from __future__ import annotations

from network_picasso.questions import find_design_gaps

ALL_KEYS = ["regions", "vpcs", "subnets", "connectivity", "ingress", "compute",
            "security", "private_endpoints", "dns", "observability", "backup_dr"]


def _full_architecture() -> dict:
    """Architecture with every ibm_cloud key populated — should produce no gaps."""
    ibm_cloud = {
        key: [{"name": f"{key}-item", "type": key, "purpose": "test", "source": "test", "notes": ""}]
        for key in ALL_KEYS
    }
    return {"ibm_cloud": ibm_cloud}


def test_all_gaps_when_empty():
    """Empty ibm_cloud dict returns all 11 gap questions."""
    gaps = find_design_gaps({"ibm_cloud": {}})
    assert len(gaps) == 11


def test_no_gaps_when_full():
    """Architecture with all 11 keys populated returns an empty gap list."""
    gaps = find_design_gaps(_full_architecture())
    assert gaps == []


def test_partial_gaps():
    """Architecture missing only subnets and dns returns exactly 2 questions."""
    arch = _full_architecture()
    del arch["ibm_cloud"]["subnets"]
    del arch["ibm_cloud"]["dns"]
    gaps = find_design_gaps(arch)
    areas = {g["area"] for g in gaps}
    assert len(gaps) == 2
    assert "Subnet design" in areas
    assert "DNS and name resolution" in areas


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
