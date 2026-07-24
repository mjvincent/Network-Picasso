from __future__ import annotations

from network_picasso.questions import find_design_gaps

ALL_KEYS = ["regions", "vpcs", "subnets", "connectivity", "ingress", "compute",
            "security", "private_endpoints", "dns", "observability", "backup_dr"]


def _full_architecture() -> dict:
    """
    Architecture with all ibm_cloud keys populated and rich enough to satisfy
    every Tier-2 depth check — should produce zero gap questions.
    """
    return {
        "ibm_cloud": {
            # Two regions so single-region DR check does not fire
            "regions": [
                {"name": "us-south", "type": "regions", "purpose": "primary", "source": "test", "notes": ""},
                {"name": "us-east", "type": "regions", "purpose": "dr", "source": "test", "notes": ""},
            ],
            # Two VPCs so single-VPC check does not fire
            "vpcs": [
                {"name": "workload-vpc", "type": "vpcs", "purpose": "workload", "source": "test", "notes": ""},
                {"name": "management-vpc", "type": "vpcs", "purpose": "management", "source": "test", "notes": ""},
            ],
            # Subnets across all three zones
            "subnets": [
                {"name": "sub-zone-1", "zone": "zone-1", "type": "subnets", "source": "test", "notes": ""},
                {"name": "sub-zone-2", "zone": "zone-2", "type": "subnets", "source": "test", "notes": ""},
                {"name": "sub-zone-3", "zone": "zone-3", "type": "subnets", "source": "test", "notes": ""},
            ],
            # Direct Link + Transit Gateway so hybrid and TGW checks do not fire
            "connectivity": [
                {"name": "Direct Link 2.0", "type": "connectivity", "purpose": "hybrid", "source": "test", "notes": "direct link"},
                {"name": "Transit Gateway", "type": "connectivity", "purpose": "inter-vpc", "source": "test", "notes": "transit gateway"},
            ],
            # Public + private ingress so private-only check does not fire
            "ingress": [
                {"name": "IBM Cloud Internet Services", "type": "ingress", "purpose": "public edge", "source": "test", "notes": "public cis"},
                {"name": "Private Load Balancer", "type": "ingress", "purpose": "internal", "source": "test", "notes": "private"},
            ],
            # Non-ROKS compute so OpenShift Router check does not fire
            "compute": [
                {"name": "VPC VSI", "type": "compute", "purpose": "app tier", "source": "test", "notes": "vsi"},
            ],
            # IAM + security groups + NACLs so all security checks satisfied
            "security": [
                {"name": "IAM Policies", "type": "security", "purpose": "identity", "source": "test", "notes": "iam identity access"},
                {"name": "Security Groups", "type": "security", "purpose": "sg", "source": "test", "notes": "security group nacl acl"},
            ],
            "private_endpoints": [
                {"name": "VPE Gateway", "type": "private_endpoints", "source": "test", "notes": ""},
            ],
            "dns": [
                {"name": "IBM Cloud DNS Services", "type": "dns", "source": "test", "notes": ""},
            ],
            # Monitoring + flow logs so both observability checks satisfied
            "observability": [
                {"name": "IBM Cloud Monitoring", "type": "observability", "source": "test", "notes": "monitoring metrics"},
                {"name": "VPC Flow Logs", "type": "observability", "source": "test", "notes": "flow log"},
            ],
            # RPO/RTO + replication so both DR checks satisfied
            "backup_dr": [
                {"name": "Backup Plan", "type": "backup_dr", "purpose": "rpo rto target objective", "source": "test",
                 "notes": "cross-region replication sync"},
            ],
        }
    }


def test_all_gaps_when_empty():
    """Empty ibm_cloud dict returns exactly the 11 Tier-1 absence questions."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    assert len(gaps) == 11


def test_no_gaps_when_full():
    """A richly-populated architecture returns zero gap questions."""
    gaps = find_design_gaps(_full_architecture())
    assert gaps == [], [g["question"] for g in gaps]


def test_partial_gaps_absence():
    """Architecture missing only subnets and dns returns exactly those 2 Tier-1 questions."""
    arch = _full_architecture()
    del arch["ibm_cloud"]["subnets"]
    del arch["ibm_cloud"]["dns"]
    gaps = find_design_gaps(arch)
    areas = {g["area"] for g in gaps}
    # Only absence questions should fire (subnets absent, dns absent)
    assert "Subnet design" in areas
    assert "DNS and name resolution" in areas
    # No Tier-2 zone-spread question because subnets key is gone (Tier-1 fires instead)
    tier1_texts = [g["question"] for g in gaps if g["question"].startswith("Which")]
    assert any("subnet" in t.lower() for t in tier1_texts)


def test_single_region_triggers_dr_question():
    """Architecture with a single region fires the DR sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["regions"] = [
        {"name": "us-south", "type": "regions", "purpose": "primary", "source": "test", "notes": ""}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("disaster recovery" in q.lower() for q in questions)


def test_no_zone_spread_triggers_question():
    """Components with no zone tags fire the AZ placement sub-question."""
    arch = _full_architecture()
    # Remove zone tags from all subnets
    for item in arch["ibm_cloud"]["subnets"]:
        item.pop("zone", None)
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("zone" in q.lower() for q in questions)


def test_single_vpc_triggers_management_question():
    """Architecture with only one VPC fires the management VPC sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["vpcs"] = [
        {"name": "workload-vpc", "type": "vpcs", "purpose": "workload", "source": "test", "notes": ""}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("management" in q.lower() or "shared" in q.lower() for q in questions)


def test_no_private_ingress_triggers_question():
    """Public-only ingress fires the private load balancer sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["ingress"] = [
        {"name": "IBM Cloud Internet Services", "type": "ingress", "source": "test", "notes": "public cis"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("private" in q.lower() for q in questions)


def test_security_missing_iam_triggers_question():
    """Security present but without IAM fires the IAM sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["security"] = [
        {"name": "Key Protect", "type": "security", "source": "test", "notes": "key management nacl security group acl"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("iam" in q.lower() or "identity" in q.lower() for q in questions)


def test_observability_missing_flow_logs():
    """Observability present but without flow logs fires the flow-log sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["observability"] = [
        {"name": "IBM Cloud Monitoring", "type": "observability", "source": "test", "notes": "monitoring metrics platform"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("flow log" in q.lower() for q in questions)


def test_observability_missing_monitoring():
    """Observability present but without metrics fires the platform-metrics sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["observability"] = [
        {"name": "VPC Flow Logs", "type": "observability", "source": "test", "notes": "flow log"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("metric" in q.lower() or "monitoring" in q.lower() for q in questions)


def test_dr_missing_rpo_rto():
    """Backup/DR present but without RPO/RTO fires the recovery-objectives sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["backup_dr"] = [
        {"name": "Backup", "type": "backup_dr", "source": "test", "notes": "cross-region replication sync"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("rpo" in q.lower() or "rto" in q.lower() for q in questions)


def test_dr_missing_replication():
    """Backup/DR present but without replication fires the cross-region backup sub-question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["backup_dr"] = [
        {"name": "Backup Plan", "type": "backup_dr", "source": "test", "notes": "rpo rto target objective"}
    ]
    gaps = find_design_gaps(arch)
    questions = [g["question"] for g in gaps]
    assert any("replication" in q.lower() or "regional failure" in q.lower() for q in questions)


def test_question_shape():
    """Every returned question has area, question, guidance, and source keys."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    for gap in gaps:
        assert "area" in gap
        assert "question" in gap
        assert "guidance" in gap
        assert "source" in gap


def test_source_is_rules():
    """All rule-based questions are tagged source: 'rules'."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    for gap in gaps:
        assert gap["source"] == "rules"


def test_no_duplicate_questions():
    """find_design_gaps never returns the same question text twice."""
    arch = _full_architecture()
    # Remove a few keys to trigger both tiers simultaneously
    del arch["ibm_cloud"]["subnets"]
    gaps = find_design_gaps(arch)
    texts = [g["question"] for g in gaps]
    assert len(texts) == len(set(texts))
