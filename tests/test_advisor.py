from __future__ import annotations

from network_picasso.advisor import review_architecture


def _component(name: str, notes: str = "") -> dict:
    return {"name": name, "purpose": notes, "notes": notes}


def test_review_architecture_recommends_pattern_and_pillars():
    architecture = {
        "project": {"name": "Sample"},
        "ibm_cloud": {
            "vpcs": [_component("Edge VPC"), _component("Workload VPC")],
            "regions": [_component("us-south")],
            "zones": [_component("zone-1"), _component("zone-2"), _component("zone-3")],
            "connectivity": [_component("Transit Gateway")],
            "ingress": [_component("Application Load Balancer")],
            "security": [_component("Security Groups and Key Protect")],
            "observability": [_component("Activity Tracker and Monitoring")],
            "backup_dr": [_component("Cross-region backup")],
        },
    }

    review = review_architecture(architecture)

    assert review["recommendedPattern"]["id"] == "hub-and-spoke"
    assert len(review["wellArchitected"]) == 6
    assert review["openDecisionCount"] > 0
    assert review["sellerNextActions"]
    assert review["patternFoundation"]["name"] == "VPC landing zone Standard"
    assert any(item["area"] == "Topology" for item in review["logicalDesign"])


def test_review_architecture_surfaces_security_gap_when_vpe_missing():
    architecture = {
        "project": {"name": "Regulated workload"},
        "ibm_cloud": {
            "security": [_component("Security and Compliance Center")],
            "observability": [_component("Activity Tracker")],
        },
    }

    review = review_architecture(architecture, requirements_text="Financial services, PCI, no public egress.")
    security = next(p for p in review["wellArchitected"] if p["name"] == "Security and compliance")

    assert security["score"] < 100
    assert "Define VPE/private service access coverage" in security["gaps"]


def test_review_architecture_surfaces_powervs_dr_foundation():
    architecture = {
        "project": {"name": "OmniCare"},
        "render_plan": {"pattern": "hybrid-powervs-dr", "has_powervs": True, "has_dr": True},
        "ibm_cloud": {
            "regions": [_component("us-south"), _component("us-east")],
            "vpcs": [_component("DAL VPC"), _component("WDC VPC")],
            "compute": [_component("PowerVS servers")],
            "backup_dr": [_component("WDC disaster recovery site")],
            "security": [_component("Security and Compliance Center")],
            "private_endpoints": [_component("Virtual Private Endpoints")],
        },
    }

    review = review_architecture(architecture, requirements_text="HIPAA medical imaging with PowerVS and DR site")

    assert review["recommendedPattern"]["id"] == "hybrid-powervs-dr"
    assert review["patternFoundation"]["name"] == "PowerVS with VPC landing zone + regional DR extension"
    assert "HIPAA evidence, key-management, and audit controls" in review["patternFoundation"]["requiredElements"]
