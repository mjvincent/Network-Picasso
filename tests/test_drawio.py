from __future__ import annotations

from xml.etree import ElementTree

from network_picasso.drawio import render_drawio

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
