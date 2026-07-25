"""Tests for IBM Think Architecture pattern matching (patterns.py)."""
from __future__ import annotations

import pytest

from network_picasso.patterns import best_pattern, match_patterns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arch(ibm_cloud: dict, requirements: str = "") -> dict:
    """Build a minimal architecture dict for testing."""
    arch = {"ibm_cloud": ibm_cloud}
    if requirements:
        arch["requirements"] = [{"text": requirements}]
    return arch


def _component(name: str, ctype: str, notes: str = "") -> dict:
    return {"name": name, "type": ctype, "purpose": notes, "notes": notes}


def _scores(results: list[dict]) -> dict[str, float]:
    return {r["id"]: r["score"] for r in results}


# ---------------------------------------------------------------------------
# Basic sanity
# ---------------------------------------------------------------------------

def test_match_patterns_returns_all_patterns():
    """match_patterns returns one result per registered pattern."""
    results = match_patterns(_arch({}))
    # We have 15 defined patterns
    assert len(results) == 15


def test_results_sorted_by_score_descending():
    """Results are always sorted highest score first."""
    results = match_patterns(_arch({"compute": [_component("ROKS cluster", "compute")]}))
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_top_n_limits_results():
    """topN parameter returns only that many results."""
    results = match_patterns(_arch({}), top_n=3)
    assert len(results) == 3


def test_result_shape():
    """Every result has the required fields."""
    results = match_patterns(_arch({}))
    required_keys = {"id", "name", "description", "url", "score", "matched", "missing"}
    for r in results:
        assert required_keys.issubset(set(r.keys())), f"Missing keys in {r['id']}"


# ---------------------------------------------------------------------------
# Pattern-specific scoring
# ---------------------------------------------------------------------------

def test_mzr_pattern_scores_high_for_three_zone_vpc():
    """A VPC with 3 AZs, LB, and compute should score highest for MZR."""
    arch = _arch({
        "vpcs": [_component("Production VPC", "vpcs")],
        "zones": [
            _component("zone-1", "zones"),
            _component("zone-2", "zones"),
            _component("zone-3", "zones"),
        ],
        "compute": [_component("VPC VSI App Server", "compute")],
        "ingress": [_component("Application Load Balancer", "ingress")],
        "security": [_component("Security Groups", "security")],
        "observability": [_component("IBM Cloud Monitoring", "observability")],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["mzr"] >= 60, f"MZR score too low: {scores['mzr']}"
    # MZR should beat basic-vpc for a 3-zone setup (basic-vpc has a negative signal for 3 zones)
    assert scores["mzr"] >= scores["basic-vpc"], (
        f"MZR ({scores['mzr']}) should be ≥ basic-vpc ({scores['basic-vpc']}) for 3-zone setup"
    )


def test_hub_and_spoke_scores_high_for_multiple_vpcs_and_tgw():
    """Multiple VPCs + Transit Gateway + edge VPC → hub-and-spoke wins."""
    arch = _arch({
        "vpcs": [
            _component("Edge VPC", "vpcs", "internet ingress"),
            _component("App VPC", "vpcs", "private workload"),
        ],
        "connectivity": [_component("Transit Gateway", "connectivity")],
        "ingress": [_component("Load Balancer", "ingress")],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["hub-and-spoke"] >= 60, f"Hub-spoke score: {scores['hub-and-spoke']}"
    assert scores["hub-and-spoke"] > scores["basic-vpc"]


def test_hybrid_pattern_scores_high_with_direct_link():
    """Direct Link + on-premises reference → hybrid scores highly."""
    arch = _arch({
        "connectivity": [
            _component("IBM Direct Link 2.0", "connectivity"),
            _component("Transit Gateway", "connectivity"),
        ],
    }, requirements="We need to connect our on-premises data centre to IBM Cloud via Direct Link.")
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["hybrid"] >= 50, f"Hybrid score: {scores['hybrid']}"
    assert scores["hybrid"] > scores["basic-vpc"]


def test_powervs_pattern_scores_high_for_power_workload():
    """PowerVS compute + SAP keyword → powervs pattern wins."""
    arch = _arch({
        "compute": [_component("IBM Power Virtual Server SAP HANA", "compute")],
        "connectivity": [_component("IBM Direct Link", "connectivity")],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["powervs"] >= 60, f"PowerVS score: {scores['powervs']}"


def test_roks_pattern_scores_high_for_openshift():
    """ROKS compute → roks pattern dominates."""
    arch = _arch({
        "compute": [_component("Red Hat OpenShift on IBM Cloud", "compute")],
        "ingress": [_component("OpenShift Router", "ingress")],
        "security": [_component("IBM Container Registry", "security")],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["roks"] >= 50, f"ROKS score: {scores['roks']}"


def test_fsc_pattern_scores_high_for_regulated_environment():
    """HPCS + SCC + regulated keywords → FSC pattern."""
    arch = _arch({
        "security": [
            _component("HPCS Hyper Protect Crypto Services", "security"),
            _component("Security and Compliance Center", "security"),
            _component("IBM Secrets Manager", "security"),
        ],
        "private_endpoints": [
            _component("VPE Cloud Object Storage", "private_endpoints"),
            _component("VPE Databases", "private_endpoints"),
        ],
        "observability": [_component("Activity Tracker", "observability")],
    }, requirements="PCI DSS compliance required. Financial services. No public egress from workload VPC.")
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["fsc"] >= 50, f"FSC score: {scores['fsc']}"


def test_ai_data_pattern_scores_high_for_watsonx():
    """watsonx keyword → ai-data pattern."""
    arch = _arch({
        "compute": [_component("watsonx.ai on ROKS", "compute")],
        "data": [_component("IBM Cloud Object Storage training data", "data")],
    }, requirements="AI and ML workloads using watsonx foundation models with GPU inference.")
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["ai-data"] >= 50, f"AI-data score: {scores['ai-data']}"


def test_event_driven_pattern_scores_high_for_kafka():
    """Event Streams (Kafka) → event-driven pattern."""
    arch = _arch({
        "data": [
            _component("IBM Event Streams Kafka", "data"),
            _component("IBM MQ", "data"),
        ],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["event-driven"] >= 60, f"Event-driven score: {scores['event-driven']}"


def test_resiliency_dr_scores_high_for_multi_region():
    """Two regions + backup_dr items → resiliency-dr pattern."""
    arch = _arch({
        "regions": [
            _component("us-south", "regions"),
            _component("us-east", "regions"),
        ],
        "backup_dr": [
            _component("Cross-region COS replication", "backup_dr"),
        ],
    }, requirements="RPO 1 hour, RTO 4 hours. Active/warm standby across us-south and us-east.")
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["resiliency-dr"] >= 50, f"DR score: {scores['resiliency-dr']}"


def test_empty_architecture_still_returns_all_patterns():
    """An empty ibm_cloud model doesn't crash and still returns all patterns."""
    results = match_patterns(_arch({}))
    assert len(results) == 15
    # All scores should be ≥ 0
    assert all(r["score"] >= 0 for r in results)


def test_best_pattern_returns_top_result():
    """best_pattern returns the highest-scoring pattern dict."""
    arch = _arch({
        "compute": [_component("Red Hat OpenShift on IBM Cloud", "compute")],
    })
    best = best_pattern(arch)
    all_results = match_patterns(arch)
    assert best["id"] == all_results[0]["id"]
    assert best["score"] == all_results[0]["score"]


def test_requirements_text_boosts_pattern_score():
    """Free-text requirements with hybrid keywords boost the hybrid pattern."""
    arch_no_req = _arch({
        "vpcs": [_component("Production VPC", "vpcs")],
    })
    arch_with_req = _arch({
        "vpcs": [_component("Production VPC", "vpcs")],
    }, requirements="Direct Link connection to on-premises data center required.")
    scores_no  = _scores(match_patterns(arch_no_req))
    scores_yes = _scores(match_patterns(arch_with_req))
    assert scores_yes["hybrid"] >= scores_no["hybrid"], (
        f"Requirements text should boost hybrid: {scores_no['hybrid']} → {scores_yes['hybrid']}"
    )


def test_three_tier_vpc_scores_for_web_app_tier_keywords():
    """Web + app + DB tier keywords → three-tier-vpc scores high."""
    arch = _arch({
        "vpcs": [_component("Production VPC", "vpcs")],
        "ingress": [_component("Application Load Balancer public subnet", "ingress")],
        "compute": [_component("App server private subnet VSI", "compute")],
        "data": [_component("PostgreSQL database data subnet", "data")],
        "subnets": [
            _component("public-subnet-1", "subnets"),
            _component("private-subnet-1", "subnets"),
            _component("data-subnet-1", "subnets"),
        ],
    })
    results = match_patterns(arch)
    scores = _scores(results)
    assert scores["three-tier-vpc"] >= 60, f"Three-tier score: {scores['three-tier-vpc']}"
