from __future__ import annotations

from network_picasso.drawio import render_drawio
from network_picasso.quality import analyze_diagram_quality, apply_quality_remediations


HYBRID_ARCH = {
    "project": {"name": "OmniCare RFP", "environment": "Production"},
    "render_plan": {
        "pattern": "hybrid-powervs-dr",
        "has_dr": True,
        "has_on_prem": True,
        "has_powervs": True,
        "connectivity_label": "HA Direct Link 1 Gbps",
        "az_count": 1,
    },
    "ibm_cloud": {
        "regions": [{"name": "us-south"}, {"name": "us-east"}],
        "vpcs": [
            {"name": "DAL VPC", "region": "us-south"},
            {"name": "WDC VPC", "region": "us-east"},
        ],
        "connectivity": [{"name": "HA Direct Link 1 Gbps"}],
        "compute": [{"name": "Medical imaging processing VSIs"}, {"name": "PowerVS servers"}],
        "data": [{"name": "Cloud Object Storage"}, {"name": "NFS File Storage"}],
        "security": [{"name": "Security and Compliance Center"}, {"name": "Key Protect or HPCS"}, {"name": "Secrets Manager"}],
        "observability": [{"name": "Activity Tracker"}, {"name": "VPC Flow Logs"}],
        "private_endpoints": [{"name": "Virtual Private Endpoints for IBM Cloud services"}],
        "backup_dr": [{"name": "WDC disaster recovery site", "region": "us-east"}],
    },
}


def test_quality_analyzer_reports_ibm_pattern_checks():
    xml = render_drawio(HYBRID_ARCH, diagram_type="deployment")
    result = analyze_diagram_quality(HYBRID_ARCH, diagram_type="deployment", xml=xml)

    assert result["pattern"] == "hybrid-powervs-dr"
    assert result["ibmPatternChecks"]["name"] == "Power Virtual Server with VPC landing zone"
    assert result["score"] >= 70
    assert result["checkedCells"] > 0


def test_quality_analyzer_flags_missing_pattern_elements():
    arch = {
        "project": {"name": "Sparse VSI"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "Production VPC"}],
            "compute": [{"name": "VSI workload"}],
        },
    }
    xml = render_drawio(arch, diagram_type="deployment")
    result = analyze_diagram_quality(arch, diagram_type="deployment", xml=xml)
    messages = " ".join(finding["message"] for finding in result["findings"])

    assert "Security services" in messages
    assert "Observability services" in messages


def test_quality_analyzer_flags_tight_label_box():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile><diagram name="Test"><mxGraphModel><root>
  <mxCell id="0"/>
  <mxCell id="1" parent="0"/>
  <mxCell id="tight" value="Very long service label that will not fit" style="rounded=0;fontSize=12;" vertex="1" parent="1">
    <mxGeometry x="10" y="10" width="80" height="20" as="geometry" />
  </mxCell>
</root></mxGraphModel></diagram></mxfile>"""
    result = analyze_diagram_quality({"project": {}, "ibm_cloud": {}}, diagram_type="deployment", xml=xml)

    assert any(finding["area"] == "Label fit" for finding in result["findings"])


def test_apply_quality_remediations_adds_missing_pattern_components():
    architecture = {
        "project": {"name": "Quality fixes"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "vpcs": [{"name": "Production VPC"}],
            "compute": [{"name": "VSI workload"}],
        },
    }
    review = {
        "pattern": "vsi-vpc",
        "ibmPatternSource": "https://www.ibm.com/think/architectures/patterns",
        "ibmPatternChecks": {
            "name": "VSI on VPC landing zone - Standard",
            "checks": [
                {"name": "VPC landing zone", "present": True},
                {"name": "Private endpoints", "present": False},
                {"name": "Observability services", "present": False},
            ],
        },
        "findings": [
            {"area": "Label fit", "recommendation": "Increase the shape width."},
        ],
    }

    result = apply_quality_remediations(architecture, review)

    assert any(item["name"].startswith("Virtual Private Endpoints") for item in architecture["ibm_cloud"]["private_endpoints"])
    assert any("Activity Tracker" in item["name"] for item in architecture["ibm_cloud"]["observability"])
    assert result["applied"]
    assert result["deferred"]
    assert architecture["quality"]["lastRemediation"]["source"] == "quality-analyzer"
    traceability = architecture["decisions"]["ibmPatternTraceability"]
    assert traceability["name"] == "VSI on VPC landing zone - Standard"
    assert "VPC landing zone" in traceability["present"]
    assert "Private endpoints" in traceability["missing"]
    assert architecture["decisions"]["presentationReview"]["required"] is True


def test_quality_remediations_do_not_add_powervs_without_powervs_evidence():
    architecture = {
        "project": {"name": "UPS VCF ROVS"},
        "render_plan": {
            "pattern": "hybrid-powervs-dr",
            "topology_variant": "classic-vcf-rovs",
            "has_powervs": False,
        },
        "ibm_cloud": {
            "vpcs": [{"name": "ROVS POC VPC"}],
            "compute": [{"name": "ROVS cluster for VDI testing"}],
            "connectivity": [{"name": "DirectLink 2.0"}, {"name": "Transit Gateway"}, {"name": "Juniper vSRX"}],
        },
    }
    review = {
        "pattern": "hybrid-powervs-dr",
        "ibmPatternChecks": {
            "name": "Power Virtual Server with VPC landing zone",
            "checks": [{"name": "PowerVS workspace", "present": False}],
        },
        "findings": [],
    }

    result = apply_quality_remediations(architecture, review)
    compute_names = [item["name"] for item in architecture["ibm_cloud"]["compute"]]

    assert "PowerVS workspace" not in compute_names
    assert result["deferred"]
    assert "Skipped PowerVS" in result["deferred"][0]["change"]
