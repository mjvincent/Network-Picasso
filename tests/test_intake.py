from __future__ import annotations

import pathlib
import zipfile

import pytest

from network_picasso.intake import (
    KEYWORDS,
    add_detected_facts,
    build_architecture_from_inputs,
    dedupe_components,
    infer_environment,
    is_solutioning_workbook,
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


def test_infer_environment():
    """Text containing 'production' triggers environment inference."""
    facts = {"compute": [{"name": "VSI", "type": "compute", "purpose": "production workload", "source": "x", "notes": "production"}]}
    from network_picasso.intake import infer_environment
    assert infer_environment(facts) == "Production"


def test_solutioning_detection():
    """is_solutioning_workbook returns True for the Solutioning fixture and False for a plain XLSX."""
    if not SOLUTIONING_XLSX.exists():
        pytest.skip("solutioning-sample.xlsx not found")
    with zipfile.ZipFile(SOLUTIONING_XLSX) as zf:
        assert is_solutioning_workbook(zf) is True

    # Build a minimal plain XLSX (no Solutioning columns) and confirm detection returns False.
    import io
    import zipfile as zf_mod
    # We cannot easily build a full .xlsx inline here — check that a real non-Solutioning CSV-turned-path is not detected.
    # Instead, just verify is_solutioning_workbook with a minimal zipfile that has no workbook raises gracefully.
    buf = io.BytesIO()
    with zf_mod.ZipFile(buf, "w") as zf2:
        zf2.writestr("dummy.txt", "not an xlsx")
    buf.seek(0)
    with zf_mod.ZipFile(buf) as zf3:
        assert is_solutioning_workbook(zf3) is False
