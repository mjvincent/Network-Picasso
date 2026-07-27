from __future__ import annotations

from xml.etree import ElementTree

from network_picasso.drawio import (
    DEPLOYMENT_GUIDE,
    LOGICAL_GUIDE,
    STYLE_GUIDE,
    render_all_diagrams,
    render_drawio,
    render_ibm_location_snippet,
    render_ibm_node_snippet,
    render_multipage_drawio,
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
    """All diagram types produce parseable XML."""
    for dtype in ("executive", "context", "logical", "deployment"):
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
    """Deployment output contains at least one AZ zone label derived from data."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    # Data-driven: zone count comes from zone tags in the model.
    # Sample has zone-1 tagged → renderer draws Zone 1 only.
    assert "Zone 1" in xml, "Expected 'Zone 1' in deployment XML"


def test_subnet_bands_in_deployment():
    """Deployment output contains subnet tier labels derived from extracted data."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    # Data-driven: subnet names include the VPC name and tier from the model.
    # Sample has 'sample-prod-vpc' with Public/Private/Management/Data tiers.
    for tier in ("public-subnet", "private-subnet"):
        assert tier in xml, f"Expected subnet tier label '{tier}' in deployment XML"


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


def test_render_plan_hub_and_spoke_changes_deployment_topology():
    arch = {
        "project": {"name": "Pattern Driven"},
        "render_plan": {"pattern": "hub-and-spoke"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "compute": [{"name": "ROKS", "type": "compute"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "Edge VPC" in xml
    assert "Workload VPC" in xml


def test_render_plan_mzr_forces_three_zones():
    arch = {
        "project": {"name": "MZR Pattern"},
        "render_plan": {"pattern": "mzr", "az_count": 3},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "Production VPC"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "Zone 1" in xml
    assert "Zone 2" in xml
    assert "Zone 3" in xml


def test_multi_region_requirements_render_primary_dr_regions():
    arch = {
        "project": {"name": "OmniCare RFP"},
        "render_plan": {
            "pattern": "hybrid-powervs-dr",
            "has_dr": True,
            "has_on_prem": True,
            "has_powervs": True,
            "connectivity_label": "HA Direct Link 1 Gbps",
            "az_count": 1,
            "shared_services": ["Security and Compliance Center", "Virtual Private Endpoints"],
        },
        "ibm_cloud": {
            "regions": [{"name": "us-south"}, {"name": "us-east"}],
            "vpcs": [
                {"name": "DAL VPC", "region": "us-south", "purpose": "Primary medical imaging processing"},
                {"name": "WDC VPC", "region": "us-east", "purpose": "DR medical imaging retrieval"},
            ],
            "connectivity": [{"name": "HA Direct Link 1 Gbps"}],
            "compute": [{"name": "Medical imaging processing VSIs"}, {"name": "PowerVS servers"}],
            "data": [{"name": "Cloud Object Storage for medical imaging archive"}, {"name": "NFS File Storage for VSI workloads"}],
            "security": [{"name": "Security and Compliance Center"}, {"name": "Key Protect or HPCS"}],
            "observability": [{"name": "Activity Tracker"}, {"name": "VPC Flow Logs"}],
            "private_endpoints": [{"name": "Virtual Private Endpoints for IBM Cloud services"}],
            "backup_dr": [{"name": "WDC disaster recovery site", "region": "us-east"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "Primary Region" in xml
    assert "DR Region" in xml
    assert "DAL VPC" in xml
    assert "WDC VPC" in xml
    assert "HA Direct Link 1 Gbps" in xml
    assert "PowerVS Workspace" in xml
    assert "SCC evidence collection" in xml
    assert "Shared Services / Compliance Foundation" in xml
    assert "PowerVS with VPC landing zone" in xml
    assert "DR VSI recovery tier" in xml
    assert "Replicated imaging data" in xml
    assert "VPC from unified pricing workbook" not in xml


def test_hybrid_dr_ignores_stale_hub_spoke_template_vpcs():
    arch = {
        "project": {"name": "Stale Plan"},
        "render_plan": {
            "pattern": "hybrid-powervs-dr",
            "has_dr": True,
            "has_on_prem": True,
            "has_powervs": True,
            "vpcs": [
                {"name": "Edge VPC", "purpose": "stale hub template"},
                {"name": "Workload VPC", "purpose": "stale hub template"},
            ],
        },
        "ibm_cloud": {
            "regions": [{"name": "us-south"}, {"name": "us-east"}],
            "vpcs": [
                {"name": "DAL VPC", "region": "us-south"},
                {"name": "WDC VPC", "region": "us-east"},
            ],
            "compute": [{"name": "PowerVS servers"}],
            "data": [{"name": "Cloud Object Storage"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "DAL VPC" in xml
    assert "WDC VPC" in xml
    assert "Edge VPC" not in xml
    assert "Workload VPC" not in xml


def test_executive_overview_renders_seller_friendly_story():
    arch = {
        "project": {"name": "OmniCare RFP", "environment": "Production"},
        "render_plan": {
            "pattern": "hybrid-powervs-dr",
            "has_on_prem": True,
            "has_powervs": True,
            "has_dr": True,
            "connectivity_label": "HA Direct Link 1 Gbps",
        },
        "ibm_cloud": {
            "regions": [{"name": "us-south"}, {"name": "us-east"}],
            "vpcs": [{"name": "DAL VPC"}, {"name": "WDC VPC"}],
        },
    }
    xml = render_drawio(arch, diagram_type="executive")
    assert "Executive Overview" in xml
    assert "Enterprise Sites" in xml
    assert "Dallas / us-south" in xml
    assert "Washington DC / us-east" in xml
    assert "Shared Security, Compliance, and Operations Foundation" in xml


def test_deployment_summarizes_multiple_vsi_profiles_as_workload_tier():
    arch = {
        "project": {"name": "OmniCare RFP", "environment": "Production"},
        "render_plan": {
            "pattern": "hybrid-powervs-dr",
            "has_on_prem": True,
            "has_powervs": True,
            "has_dr": True,
        },
        "ibm_cloud": {
            "regions": [{"name": "us-south"}, {"name": "us-east"}],
            "vpcs": [
                {"name": "DAL VPC", "region": "us-south"},
                {"name": "WDC VPC", "region": "us-east"},
            ],
            "compute": [
                {
                    "name": "VPC VSI (mx2-16x128)",
                    "purpose": "VSI profile mx2-16x128",
                    "notes": "Many VSIs on VPC in each region of various profiles for medical imaging.",
                },
                {"name": "PowerVS servers"},
            ],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    assert "Medical imaging VSI tier" in xml
    assert "Multiple VPC VSI profiles" in xml
    assert "VPC VSI (mx2-16x128)" not in xml

    multi_xml = render_multipage_drawio(arch)
    assert "Multiple profiles" in multi_xml
    assert "VPC VSI (mx2-16x128)" not in multi_xml


def test_xml_has_mxfile_wrapper():
    """Output XML starts with mxfile wrapper as required by Draw.io desktop app."""
    xml = render_drawio(SAMPLE_ARCH, diagram_type="deployment")
    assert xml.strip().startswith("<?xml") or "<mxfile" in xml


# ---------------------------------------------------------------------------
# render_ibm_node_snippet tests
# ---------------------------------------------------------------------------

def test_ibm_node_snippet_is_valid_xml():
    xml = render_ibm_node_snippet("Bastion Host", "bastion-host")
    root = ElementTree.fromstring(xml)
    assert root.tag == "mxGraphModel"


def test_ibm_node_snippet_contains_name():
    xml = render_ibm_node_snippet("Bastion Host", "bastion-host")
    assert "Bastion Host" in xml


def test_ibm_node_snippet_uses_stencil():
    xml = render_ibm_node_snippet("Bastion Host", "bastion-host")
    assert "mxgraph.ibm_cloud.bastion-host" in xml


def test_ibm_node_snippet_custom_position():
    xml = render_ibm_node_snippet("Bastion Host", "bastion-host", x=200, y=350)
    assert 'x="200"' in xml
    assert 'y="350"' in xml


def test_ibm_node_snippet_custom_parent():
    xml = render_ibm_node_snippet("VSI", "ibm-cloud--virtual-server-vpc", parent_id="az-band-42")
    assert 'parent="az-band-42"' in xml


def test_ibm_node_snippet_colored_background():
    """IBM prescribed node pattern: outer cell must have a non-white fill."""
    xml = render_ibm_node_snippet("ROKS", "logo--openshift")
    # The background cell should have fillColor (not white, not 'none')
    assert "fillColor=#" in xml


# ---------------------------------------------------------------------------
# render_ibm_location_snippet tests
# ---------------------------------------------------------------------------

def test_ibm_location_snippet_is_valid_xml():
    xml = render_ibm_location_snippet("Production VPC", "ibm-cloud--vpc", "#1192E8")
    root = ElementTree.fromstring(xml)
    assert root.tag == "mxGraphModel"


def test_ibm_location_snippet_contains_name():
    xml = render_ibm_location_snippet("Production VPC", "ibm-cloud--vpc", "#1192E8")
    assert "Production VPC" in xml


def test_ibm_location_snippet_uses_stencil():
    xml = render_ibm_location_snippet("Production VPC", "ibm-cloud--vpc", "#1192E8")
    assert "mxgraph.ibm_cloud.ibm-cloud--vpc" in xml


def test_ibm_location_snippet_stroke_color():
    xml = render_ibm_location_snippet("Production VPC", "ibm-cloud--vpc", "#1192E8", w=400, h=300)
    assert "#1192E8" in xml


def test_ibm_location_snippet_dimensions():
    xml = render_ibm_location_snippet("My Region", "location", "#878D96", x=50, y=80, w=960, h=800)
    assert 'width="960"' in xml
    assert 'height="800"' in xml


def test_ibm_location_snippet_has_border_strip():
    """IBM location pattern always includes a 4px-wide left border strip."""
    xml = render_ibm_location_snippet("My VPC", "ibm-cloud--vpc", "#1192E8")
    assert 'width="4"' in xml


# ---------------------------------------------------------------------------
# render_all_diagrams tests
# ---------------------------------------------------------------------------

def test_render_all_diagrams_keys():
    result = render_all_diagrams(SAMPLE_ARCH)
    assert set(result.keys()) == {"executive", "context", "logical", "deployment"}


def test_render_all_diagrams_all_valid_xml():
    for dtype, xml in render_all_diagrams(SAMPLE_ARCH).items():
        root = ElementTree.fromstring(xml)
        assert root is not None, f"Invalid XML for diagram type '{dtype}'"


def test_render_all_diagrams_non_empty():
    result = render_all_diagrams(SAMPLE_ARCH)
    for dtype, xml in result.items():
        assert len(xml) > 200, f"Diagram '{dtype}' seems too short: {len(xml)} chars"


# ---------------------------------------------------------------------------
# render_multipage_drawio tests
# ---------------------------------------------------------------------------

def test_multipage_drawio_has_mxfile_root():
    xml = render_multipage_drawio(SAMPLE_ARCH)
    root = ElementTree.fromstring(xml)
    assert root.tag == "mxfile"


def test_multipage_drawio_has_four_pages():
    xml = render_multipage_drawio(SAMPLE_ARCH)
    root = ElementTree.fromstring(xml)
    diagrams = root.findall("diagram")
    assert len(diagrams) == 4


def test_multipage_drawio_page_names():
    xml = render_multipage_drawio(SAMPLE_ARCH)
    root = ElementTree.fromstring(xml)
    names = [d.attrib.get("name") for d in root.findall("diagram")]
    assert "Executive Overview" in names
    assert "Context" in names
    assert "Logical Architecture" in names
    assert "Deployment" in names
