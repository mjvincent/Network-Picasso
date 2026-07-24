from __future__ import annotations

from network_picasso.questions import find_design_gaps

ALL_IBMCLOUD_KEYS = [
    "regions", "vpcs", "subnets", "connectivity", "ingress", "compute",
    "security", "private_endpoints", "dns", "observability", "backup_dr", "data",
]


def _full_architecture() -> dict:
    """
    A richly-populated architecture that satisfies every Tier-2 depth check.
    Tier 0 questions (always-asked) will still appear — that is correct behaviour.
    """
    return {
        "ibm_cloud": {
            "regions": [
                {"name": "us-south", "type": "regions", "source": "test", "notes": ""},
                {"name": "us-east",  "type": "regions", "source": "test", "notes": ""},
            ],
            "vpcs": [
                {"name": "edge-vpc",    "type": "vpcs", "source": "test", "notes": ""},
                {"name": "workload-vpc","type": "vpcs", "source": "test", "notes": ""},
            ],
            "subnets": [
                {"name": "pub-zone-1", "zone": "zone-1", "type": "subnets", "source": "test"},
                {"name": "pub-zone-2", "zone": "zone-2", "type": "subnets", "source": "test"},
                {"name": "pub-zone-3", "zone": "zone-3", "type": "subnets", "source": "test"},
            ],
            "connectivity": [
                {"name": "Direct Link 2.0", "type": "connectivity", "notes": "direct link"},
                {"name": "Transit Gateway", "type": "connectivity", "notes": "transit gateway tgw"},
            ],
            "ingress": [
                {"name": "IBM Cloud Internet Services", "type": "ingress", "notes": "cis public"},
                {"name": "Private Load Balancer",       "type": "ingress", "notes": "private internal"},
            ],
            "compute": [
                {"name": "VPC VSI bx2-2x8", "type": "compute", "notes": "vsi virtual server"},
            ],
            "security": [
                {"name": "IAM Access Groups",    "type": "security", "notes": "iam identity access"},
                {"name": "Key Protect",          "type": "security", "notes": "key protect encryption"},
                {"name": "Security Groups/NACLs","type": "security", "notes": "security group nacl acl"},
                {"name": "SCC",                  "type": "security", "notes": "scc security and compliance"},
            ],
            "private_endpoints": [
                {"name": "COS VPE",      "type": "private_endpoints", "notes": ""},
            ],
            "dns": [
                {"name": "IBM Cloud DNS Services", "type": "dns", "notes": ""},
            ],
            "observability": [
                {"name": "IBM Cloud Monitoring", "type": "observability", "notes": "monitoring metrics platform sysdig"},
                {"name": "VPC Flow Logs",        "type": "observability", "notes": "flow log"},
            ],
            "backup_dr": [
                {"name": "Backup Plan", "type": "backup_dr", "notes": "rpo rto objective"},
            ],
            "data": [
                {"name": "Cloud Object Storage", "type": "data", "notes": ""},
            ],
        }
    }


# ── Tier 0 — always asked ────────────────────────────────────────────────────

def test_tier0_pattern_question_always_asked():
    """Architecture pattern question fires even when all keys are populated."""
    gaps = find_design_gaps(_full_architecture())
    questions = [g["question"] for g in gaps]
    assert any("reference architecture pattern" in q.lower() for q in questions)


def test_tier0_region_question_always_asked():
    """Primary region question fires even when regions key is populated."""
    gaps = find_design_gaps(_full_architecture())
    questions = [g["question"] for g in gaps]
    assert any("primary deployment region" in q.lower() for q in questions)


def test_tier0_account_question_always_asked():
    """Account and resource group question fires regardless of populated keys."""
    gaps = find_design_gaps(_full_architecture())
    questions = [g["question"] for g in gaps]
    assert any("resource group" in q.lower() for q in questions)


# ── Tier 1 — absent keys ─────────────────────────────────────────────────────

def test_tier1_empty_model_has_all_gaps():
    """Empty ibm_cloud produces at least the 11 Tier-1 topology questions plus Tier-0."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    areas = {g["area"] for g in gaps}
    assert "VPC topology" in areas
    assert "Subnet design" in areas
    assert "Hybrid connectivity" in areas
    assert "Ingress and load balancing" in areas
    assert "Compute platform" in areas
    assert "Security controls" in areas
    assert "Private service access" in areas
    assert "DNS and name resolution" in areas
    assert "Observability" in areas
    assert "Backup and DR" in areas
    assert "Data services" in areas
    # At least 3 Tier-0 questions plus the 11 Tier-1 questions
    assert len(gaps) >= 14


def test_tier1_vpcs_absent():
    """VPC topology question fires when vpcs key is missing."""
    arch = {"ibm_cloud": {k: [{"name": k}] for k in ALL_IBMCLOUD_KEYS if k != "vpcs"}}
    gaps = find_design_gaps(arch)
    assert any("VPC" in g["area"] for g in gaps)
    assert any("how many vpcs" in g["question"].lower() for g in gaps)


def test_tier1_connectivity_absent():
    """Hybrid connectivity question fires when connectivity key is missing."""
    arch = {"ibm_cloud": {k: [{"name": k}] for k in ALL_IBMCLOUD_KEYS if k != "connectivity"}}
    gaps = find_design_gaps(arch)
    assert any("on-premises" in g["question"].lower() for g in gaps)


def test_tier1_guidance_is_nonempty():
    """Every Tier-1 question has meaningful guidance text (> 100 chars)."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    for g in gaps:
        assert len(g.get("guidance", "")) > 100, f"Short guidance for: {g['question'][:60]}"


# ── Tier 2 — present but shallow ─────────────────────────────────────────────

def test_tier2_single_region_triggers_dr():
    """Single region fires DR question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["regions"] = [{"name": "us-south", "source": "test"}]
    gaps = find_design_gaps(arch)
    assert any("disaster recovery region" in g["question"].lower() for g in gaps)


def test_tier2_no_zone_spread():
    """No zone tags fires AZ placement question."""
    arch = _full_architecture()
    for item in arch["ibm_cloud"]["subnets"]:
        item.pop("zone", None)
    gaps = find_design_gaps(arch)
    assert any("zone-1" in g["question"].lower() or "availability zone" in g["question"].lower() for g in gaps)


def test_tier2_single_vpc_triggers_edge_vpc():
    """Single VPC fires Hub-and-Spoke / Edge VPC question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["vpcs"] = [{"name": "single-vpc", "source": "test"}]
    gaps = find_design_gaps(arch)
    assert any("edge vpc" in g["question"].lower() or "management vpc" in g["question"].lower() for g in gaps)


def test_tier2_no_dl_vpn_triggers_hybrid_question():
    """Connectivity present but without DL or VPN fires hybrid question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["connectivity"] = [
        {"name": "Transit Gateway", "notes": "transit gateway tgw"}
    ]
    gaps = find_design_gaps(arch)
    assert any("internet-facing" in g["question"].lower() or "on-premises" in g["question"].lower() for g in gaps)


def test_tier2_no_cis_triggers_waf_question():
    """Public LB without CIS fires WAF/DDoS question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["ingress"] = [
        {"name": "Public ALB", "notes": "public application load balancer alb"},
        {"name": "Private LB", "notes": "private internal"},
    ]
    gaps = find_design_gaps(arch)
    assert any("cis" in g["question"].lower() or "waf" in g["question"].lower() for g in gaps)


def test_tier2_no_private_ingress():
    """Public-only ingress fires private LB question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["ingress"] = [
        {"name": "IBM Cloud Internet Services", "notes": "cis public"}
    ]
    gaps = find_design_gaps(arch)
    assert any("private load balancer" in g["question"].lower() for g in gaps)


def test_tier2_roks_fires_ingress_question():
    """ROKS compute without CIS fires ingress controller question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["compute"] = [
        {"name": "ROKS cluster", "notes": "openshift roks ocp"}
    ]
    arch["ibm_cloud"]["ingress"] = [
        {"name": "Private LB", "notes": "private"},
    ]
    gaps = find_design_gaps(arch)
    assert any("roks" in g["question"].lower() or "openshift" in g["question"].lower() for g in gaps)


def test_tier2_no_iam_triggers_question():
    """Security without IAM fires IAM question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["security"] = [
        {"name": "Key Protect", "notes": "key protect encryption nacl security group acl scc compliance"}
    ]
    gaps = find_design_gaps(arch)
    assert any("iam" in g["question"].lower() or "trusted profile" in g["question"].lower() for g in gaps)


def test_tier2_no_key_mgmt_triggers_question():
    """Security without key management fires encryption question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["security"] = [
        {"name": "IAM", "notes": "iam identity access nacl security group acl scc compliance"}
    ]
    gaps = find_design_gaps(arch)
    assert any("key" in g["question"].lower() or "encrypt" in g["question"].lower() for g in gaps)


def test_tier2_no_flow_logs():
    """Observability without flow logs fires flow-log question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["observability"] = [
        {"name": "IBM Cloud Monitoring", "notes": "monitoring metrics sysdig platform"}
    ]
    gaps = find_design_gaps(arch)
    assert any("flow log" in g["question"].lower() for g in gaps)


def test_tier2_no_monitoring():
    """Observability without metrics fires platform-metrics question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["observability"] = [
        {"name": "VPC Flow Logs", "notes": "flow log"}
    ]
    gaps = find_design_gaps(arch)
    assert any("metrics" in g["question"].lower() or "monitoring" in g["question"].lower() for g in gaps)


def test_tier2_no_rpo_rto():
    """Backup/DR without RPO/RTO fires recovery objectives question."""
    arch = _full_architecture()
    arch["ibm_cloud"]["backup_dr"] = [{"name": "Daily snapshots", "notes": "snapshot backup"}]
    gaps = find_design_gaps(arch)
    assert any("rpo" in g["question"].lower() or "rto" in g["question"].lower() for g in gaps)


# ── Shape and source ─────────────────────────────────────────────────────────

def test_question_shape():
    """Every returned question has area, question, guidance, and source keys."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    for g in gaps:
        assert "area" in g
        assert "question" in g
        assert "guidance" in g
        assert "source" in g


def test_source_is_rules():
    """All questions produced by rules are tagged source: 'rules'."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    for g in gaps:
        assert g["source"] == "rules"


def test_no_duplicate_questions():
    """find_design_gaps never returns the same question text twice."""
    arch = _full_architecture()
    del arch["ibm_cloud"]["subnets"]
    gaps = find_design_gaps(arch)
    texts = [g["question"] for g in gaps]
    assert len(texts) == len(set(texts)), f"Duplicates: {[t for t in texts if texts.count(t) > 1]}"


def test_ibm_reference_coverage():
    """Questions cover the key IBM Cloud reference architecture pattern areas."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    all_text = " ".join(g["guidance"] for g in gaps).lower()
    # Each major reference pattern should be mentioned
    assert "multi-zone" in all_text or "mzr" in all_text
    assert "hub-and-spoke" in all_text or "edge vpc" in all_text
    assert "transit gateway" in all_text
    assert "direct link" in all_text
    assert "financial services" in all_text or "fsc" in all_text or "fs cloud" in all_text
    assert "openshift" in all_text or "roks" in all_text
    assert "virtual private endpoint" in all_text or "vpe" in all_text
