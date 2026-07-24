from __future__ import annotations

from xml.etree import ElementTree

from network_picasso.drawio import (
    DEPLOYMENT_GUIDE,
    LOGICAL_GUIDE,
    STYLE_GUIDE,
    render_drawio,
    _stencil_shape,
)

SAMPLE_ARCH = {
    "project": {"name": "Test Healthcare", "environment": "Production"},
    "ibm_cloud": {
        "regions": [{"name": "us-south", "type": "regions", "purpose": "primary", "source": "test", "notes": ""}],
        "vpcs": [{"name": "prod-vpc", "type": "vpcs", "purpose": "Application VPC", "source": "test", "notes": ""}],
        "compute": [{"name": "ROKS", "type": "compute", "purpose": "App runtime", "source": "test", "notes": "", "zone": "zone-1", "subnet_tier": "Private"}],
        "data": [{"name": "PostgreSQL", "type": "data", "purpose": "Primary DB", "source": "test", "notes": "", "zone": "zone-1", "subnet_tier": "Data"}],
        "security": [{"name": "Secrets Manager", "type": "security", "purpose": "Secrets", "source": "test", "notes": ""}],
        "observability": [{"name": "Activity Tracker", "type": "observability", "purpose": "Audit", "source": "test", "notes": ""}],
        "ingress": [{"name": "Public Load Balancer", "type": "ingress", "purpose": "Ingress", "source": "test", "notes": ""}],
        "connectivity": [{"name": "Direct Link", "type": "connectivity", "purpose": "Hybrid", "source": "test", "notes": ""}],
    },
}


def test_render_returns_string():
    result = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert isinstance(result, str)
    assert len(result) > 100


def test_valid_xml():
    """All three diagram types produce parseable XML."""
    for dtype in ("context", "logical", "deployment"):
        xml = render_drawio(SAMPLE_ARCH, diagram_type=dtype)
        # Should not raise
        ElementTree.fromstring(xml)


def test_unique_cell_ids():
    """All mxCell id values in deployment output are unique."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    root = ElementTree.fromstring(xml)
    ids = [cell.attrib["id"] for cell in root.iter() if "id" in cell.attrib]
    assert len(ids) == len(set(ids)), f"Duplicate cell IDs found: {len(ids) - len(set(ids))} duplicates"


def test_title_in_output():
    """The project name appears somewhere in the XML."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert "Test Healthcare" in xml


def test_region_box_present():
    """A region from the model creates a cell containing the region name."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert "us-south" in xml


def test_empty_model_fallback():
    """render_drawio with an empty ibm_cloud dict does not raise."""
    xml = render_drawio({"project": {}, "ibm_cloud": {}}, diagram_type="deployment")
    ElementTree.fromstring(xml)  # Must parse without error


def test_zone_labels_in_deployment():
    """Deployment output contains AZ column labels."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    for zone in ("zone-1", "zone-2", "zone-3"):
        assert zone in xml, f"Expected '{zone}' in deployment XML"


def test_subnet_bands_in_deployment():
    """Deployment output contains all four subnet tier band labels."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    for tier in ("Public", "Private", "Management", "Data"):
        assert tier in xml, f"Expected subnet tier '{tier}' in deployment XML"


def test_ibm_stencil_shapes_present():
    """Deployment output uses IBM stencil shapes for known service types."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert "mxgraph.ibm_cloud" in xml, "Expected IBM stencil shape references in deployment XML"


def test_stencil_shape_lookup():
    """_stencil_shape maps known service names to IBM stencil identifiers."""
    assert _stencil_shape("Public Load Balancer") == "load-balancer--application"
    assert _stencil_shape("Transit Gateway") == "ibm-cloud--transit-gateway"
    assert _stencil_shape("Direct Link Connect 1 Gbps") == "ibm-cloud--direct-link-2--connect"
    assert _stencil_shape("Cloud Object Storage") == "object-storage"
    assert _stencil_shape("Secrets Manager") == "ibm-cloud--secrets-manager"
    assert _stencil_shape("Red Hat OpenShift on IBM Cloud") == "logo--openshift"
    assert _stencil_shape("VPC VSI (bx2d-2x8)") == "ibm-cloud--virtual-server-vpc"
    assert _stencil_shape("IBM Cloud Monitoring") == "cloud--monitoring"
    assert _stencil_shape("unknown random service") == ""  # no match → empty string


def test_md_files_loaded():
    """LLM Architecture MD Files are loaded at import time (non-empty when present)."""
    # If the files exist they must contain meaningful content.
    # If missing (e.g. test environment without LLM dir), empty string is acceptable.
    for guide, name in [
        (STYLE_GUIDE, "00-style-guide.md"),
        (LOGICAL_GUIDE, "02-logical-architecture.md"),
        (DEPLOYMENT_GUIDE, "03-deployment-architecture.md"),
    ]:
        if guide:  # only check if file was found
            assert len(guide) > 10, f"{name} was loaded but appears empty"


def test_transit_gateway_stencil():
    """Transit Gateway renders with IBM stencil shape when detected."""
    arch = {
        "project": {"name": "TGW Test"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "vpc1"}],
            "connectivity": [{"name": "Transit Gateway", "type": "connectivity"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "ibm-cloud--transit-gateway" in xml


def test_xml_has_mxfile_wrapper():
    """Output XML starts with mxfile wrapper as required by Draw.io desktop app."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert xml.strip().startswith("<?xml") or "<mxfile" in xml
