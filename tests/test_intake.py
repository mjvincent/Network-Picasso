from __future__ import annotations

import io
import pathlib
import zipfile as zf_mod

import pytest

from network_picasso.intake import (
    KEYWORDS,
    _normalise_name,
    _semantic_key,
    add_detected_facts,
    build_architecture_from_inputs,
    build_architecture_from_requirements,
    classify_file,
    dedupe_components,
    infer_environment,
    is_pricing_catalog,
    is_solutioning_workbook,
    is_unified_pricing_workbook,
    read_unified_pricing_xlsx,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SOLUTIONING_XLSX = pathlib.Path(__file__).parents[1] / "examples/sample-inputs/solutioning-sample.xlsx"


def test_csv_structured_fact(tmp_path):
    """Structured CSV (Component/Category/Region/Notes) writes to the correct ibm_cloud key."""
    csv = tmp_path / "bom.csv"
    csv.write_text("Component,Category,Region,Notes\nRed Hat OpenShift on IBM Cloud,Compute,us-south,Runtime\n")
    arch = build_architecture_from_inputs(tmp_path)
    assert len(arch["ibm_cloud"].get("compute", [])) >= 1
    names = [c["name"] for c in arch["ibm_cloud"]["compute"]]
    assert any("openshift" in n.lower() or "red hat" in n.lower() for n in names)


def test_csv_keyword_detection(tmp_path):
    """CSV with no category column but keyword text triggers keyword detection."""
    csv = tmp_path / "notes.csv"
    csv.write_text("text\nThe VPN gateway connects the on-premises network via hybrid connectivity.\n")
    arch = build_architecture_from_inputs(tmp_path)
    # "vpn" is in connectivity keywords, "hybrid" also — should have at least one connectivity fact
    assert len(arch["ibm_cloud"].get("connectivity", [])) >= 1


def test_markdown_region_extraction(tmp_path):
    """Markdown line containing an IBM region slug populates ibm_cloud.regions."""
    md = tmp_path / "notes.md"
    md.write_text("The application runs in IBM Cloud us-south.\n")
    arch = build_architecture_from_inputs(tmp_path)
    regions = [r["name"] for r in arch["ibm_cloud"].get("regions", [])]
    assert "us-south" in regions


def test_json_flat(tmp_path):
    """Flat JSON dict with keyword text populates at least one ibm_cloud key."""
    j = tmp_path / "data.json"
    j.write_text('{"description": "Deploy ROKS on VPC in us-south with IBM Cloud Databases for PostgreSQL"}')
    arch = build_architecture_from_inputs(tmp_path)
    # Should detect compute (ROKS/kubernetes), data (postgres), and possibly regions
    found_keys = set(arch["ibm_cloud"].keys()) - {"assumptions"}
    assert len(found_keys) >= 1


def test_requirements_prose_uses_canonical_component_names():
    """Narrative requirements should produce diagram-ready labels, not sentence fragments."""
    arch = build_architecture_from_requirements(
        (
            "Retail analytics platform in us-south using VSI on VPC, Cloud Object Storage "
            "archive, Activity Tracker, VPC Flow Logs, public load balancer, and no PowerVS."
        ),
        project_name="Retail Analytics",
    )

    names = {
        item["name"]
        for values in arch["ibm_cloud"].values()
        if isinstance(values, list)
        for item in values
        if isinstance(item, dict)
    }

    assert "Workload VPC" in names
    assert "VPC VSI workload tier" in names
    assert "Cloud Object Storage archive" in names
    assert "Activity Tracker" in names
    assert "VPC Flow Logs" in names
    assert "Public Load Balancer" in names
    assert not any("Retail analytics platform" in name for name in names)
    assert not any("PowerVS" in name for name in names)


def test_xlsx_basic():
    """The committed Solutioning sample XLSX parses and yields ≥ 3 components."""
    if not SOLUTIONING_XLSX.exists():
        pytest.skip("solutioning-sample.xlsx not found")
    arch = build_architecture_from_inputs(SOLUTIONING_XLSX)
    total = sum(len(v) for v in arch["ibm_cloud"].values() if isinstance(v, list))
    assert total >= 3


def test_dedupe():
    """Two identical component dicts (same type + name) are deduplicated to one."""
    component = {"name": "Direct Link", "type": "connectivity", "purpose": "", "source": "test", "notes": ""}
    result = dedupe_components([component, component])
    assert len(result) == 1


def test_dedupe_semantic_transit_gateway():
    """Near-duplicate Transit Gateway names all collapse to one component."""
    names = [
        "Transit Gateway DAL TG",
        "Transit Gateway",
        "Transit Gateway DallasTG",
        "Transit GW",
    ]
    components = [{"name": n, "type": "connectivity", "source": f"file{i}"} for i, n in enumerate(names)]
    result = dedupe_components(components)
    assert len(result) == 1, f"Expected 1, got {len(result)}: {[r['name'] for r in result]}"
    # Merged source should reference multiple files
    assert result[0]["source"].count("file") >= 2


def test_dedupe_semantic_direct_link_bandwidth_variants():
    """Direct Link variants at different bandwidths are kept as separate components
    only when they differ meaningfully; the generic 'Direct Link' collapes with them."""
    dl1 = {"name": "IBM Direct Link Dedicated", "type": "connectivity", "source": "a"}
    dl2 = {"name": "Direct Link", "type": "connectivity", "source": "b"}
    result = dedupe_components([dl1, dl2])
    # Both normalise similarly — should collapse to 1
    assert len(result) == 1


def test_dedupe_preserves_different_types():
    """Components with the same name but different types are NOT deduplicated."""
    a = {"name": "Load Balancer", "type": "ingress", "source": "x"}
    b = {"name": "Load Balancer", "type": "compute", "source": "y"}
    result = dedupe_components([a, b])
    assert len(result) == 2


def test_normalise_name_strips_profile_suffix():
    """VSI profile suffixes like bx2d-2x8 are stripped during normalisation."""
    n1 = _normalise_name("VPC VSI (bx2d-2x8)")
    n2 = _normalise_name("VPC VSI (mx2-16x128)")
    # After stripping, both should normalise to the same base
    assert n1 == n2


def test_normalise_name_abbreviation_expansion():
    """'TG' expands to 'transit gateway' for dedup purposes."""
    n_tg = _normalise_name("DAL TG")
    n_full = _normalise_name("Transit Gateway Dallas")
    assert n_tg == n_full


def test_classify_file_json(tmp_path):
    """JSON files are classified as existing_architecture."""
    f = tmp_path / "arch.json"
    f.write_text("{}")
    assert classify_file(f) == "existing_architecture"


def test_classify_file_markdown(tmp_path):
    """Markdown files are classified as solution_description."""
    f = tmp_path / "notes.md"
    f.write_text("# Notes")
    assert classify_file(f) == "solution_description"


def test_classify_file_pricing_catalog_by_filename(tmp_path):
    """Files with 'price estimat' in the name are classified as pricing_catalog."""
    f = tmp_path / "Price Estimator IBM Power Virtual Server OMNI_RFP.xlsx"
    # File does not need to exist for filename-based classification
    f.write_bytes(b"dummy")
    assert classify_file(f) == "pricing_catalog"


def test_classify_file_csv_is_bom(tmp_path):
    """Plain CSV files are classified as bom."""
    f = tmp_path / "solution.csv"
    f.write_text("Component,Category\n")
    assert classify_file(f) == "bom"


def test_is_pricing_catalog_true(tmp_path):
    """is_pricing_catalog returns True for a pricing-catalog filename."""
    f = tmp_path / "IBM Price Estimator Catalog.xlsx"
    f.write_bytes(b"dummy")
    assert is_pricing_catalog(f) is True


def test_is_pricing_catalog_false(tmp_path):
    """is_pricing_catalog returns False for a normal BOM CSV."""
    f = tmp_path / "solution-bom.csv"
    f.write_text("Component,Category\n")
    assert is_pricing_catalog(f) is False


def test_pricing_catalog_skipped_in_build(tmp_path):
    """A pricing-catalog-named file contributes 0 components to the model."""
    catalog = tmp_path / "Price Estimator IBM Cloud OMNI.xlsx"
    # Write a minimal valid XLSX (ZIP with two sheets full of random data)
    buf = io.BytesIO()
    with zf_mod.ZipFile(buf, "w") as zf:
        zf.writestr("dummy.txt", "not a real xlsx")
    catalog.write_bytes(buf.getvalue())

    arch = build_architecture_from_inputs(tmp_path)
    # No ibm_cloud keys (other than assumptions) should have components
    for key, value in arch.get("ibm_cloud", {}).items():
        if key == "assumptions":
            continue
        assert isinstance(value, list)
        assert len(value) == 0, f"Unexpected components in {key}: {value}"

    # Source entry should show skipped=True
    skipped = [s for s in arch.get("sources", []) if s.get("skipped")]
    assert len(skipped) == 1
    assert "catalog" in skipped[0].get("skip_reason", "").lower()


def test_stale_upload_clear(tmp_path):
    """_clear_upload_dir removes supported-extension files but leaves others."""
    from network_picasso.server import _clear_upload_dir
    (tmp_path / "old.csv").write_text("old data")
    (tmp_path / "old.md").write_text("old notes")
    (tmp_path / ".gitkeep").write_text("")
    (tmp_path / "subdir").mkdir()
    _clear_upload_dir(tmp_path)
    assert not (tmp_path / "old.csv").exists()
    assert not (tmp_path / "old.md").exists()
    assert (tmp_path / ".gitkeep").exists()
    assert (tmp_path / "subdir").is_dir()


def test_infer_environment():
    """Text containing 'production' triggers environment inference."""
    facts = {"compute": [{"name": "VSI", "type": "compute", "purpose": "production workload", "source": "x", "notes": "production"}]}
    from network_picasso.intake import infer_environment
    assert infer_environment(facts) == "Production"


def test_solutioning_detection():
    """is_solutioning_workbook returns True for the Solutioning fixture and False for a plain XLSX."""
    if not SOLUTIONING_XLSX.exists():
        pytest.skip("solutioning-sample.xlsx not found")
    with zf_mod.ZipFile(SOLUTIONING_XLSX) as zf:
        assert is_solutioning_workbook(zf) is True

    # Build a minimal plain XLSX (no Solutioning columns) and confirm detection returns False.
    # Verify is_solutioning_workbook with a minimal zipfile that has no workbook raises gracefully.
    buf = io.BytesIO()
    with zf_mod.ZipFile(buf, "w") as zf2:
        zf2.writestr("dummy.txt", "not an xlsx")
    buf.seek(0)
    with zf_mod.ZipFile(buf) as zf3:
        assert is_solutioning_workbook(zf3) is False


UNIFIED_PRICING_XLSX = pathlib.Path(__file__).parents[1] / "samples/Cognizant-unified-Omni-pricing-2026-6-26.xlsx"


def test_unified_pricing_detection():
    """is_unified_pricing_workbook detects the Cognizant unified pricing sample."""
    if not UNIFIED_PRICING_XLSX.exists():
        pytest.skip("Unified pricing sample not in samples/ (gitignored)")
    with zf_mod.ZipFile(UNIFIED_PRICING_XLSX) as zf:
        assert is_unified_pricing_workbook(zf) is True


def test_unified_pricing_extraction():
    """Unified pricing workbook yields VPCs, regions, compute, connectivity, and data."""
    if not UNIFIED_PRICING_XLSX.exists():
        pytest.skip("Unified pricing sample not in samples/ (gitignored)")
    arch = build_architecture_from_inputs(UNIFIED_PRICING_XLSX)
    ibm = arch["ibm_cloud"]
    # Regions: should find us-south and us-east (DAL + WDC)
    region_names = [r["name"] for r in ibm.get("regions", [])]
    assert "us-south" in region_names
    assert "us-east" in region_names
    # VPCs: DAL VPC and WDC VPC
    vpc_names = [v["name"].lower() for v in ibm.get("vpcs", [])]
    assert any("dal" in n for n in vpc_names)
    assert any("wdc" in n for n in vpc_names)
    # Connectivity: Transit Gateway and Direct Link
    conn_names = " ".join(c["name"].lower() for c in ibm.get("connectivity", []))
    assert "transit gateway" in conn_names
    assert "direct link" in conn_names
    # Compute: VSI instances
    assert len(ibm.get("compute", [])) >= 1
    # Data: Cloud Object Storage
    data_names = " ".join(d["name"].lower() for d in ibm.get("data", []))
    assert "cloud object storage" in data_names or "object storage" in data_names


def test_unified_pricing_not_detected_for_plain():
    """is_unified_pricing_workbook returns False for a non-matching zip."""
    buf = io.BytesIO()
    with zf_mod.ZipFile(buf, "w") as zf2:
        zf2.writestr("dummy.txt", "not an xlsx")
    buf.seek(0)
    with zf_mod.ZipFile(buf) as zf3:
        assert is_unified_pricing_workbook(zf3) is False
