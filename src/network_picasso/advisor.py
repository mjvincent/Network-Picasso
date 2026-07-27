from __future__ import annotations

from .patterns import match_patterns
from .questions import find_design_gaps


PILLARS = [
    "Hybrid and portable",
    "Resiliency",
    "Efficient operations",
    "Security and compliance",
    "Performance",
    "Financial operations and sustainability",
]


def _items(ibm_cloud: dict, key: str) -> list:
    value = ibm_cloud.get(key, [])
    return value if isinstance(value, list) else []


def _count(ibm_cloud: dict, key: str) -> int:
    return len(_items(ibm_cloud, key))


def _text(architecture: dict, requirements_text: str = "") -> str:
    parts: list[str] = [requirements_text]
    for entry in architecture.get("requirements", []):
        if isinstance(entry, dict):
            parts.append(str(entry.get("text") or ""))
    for items in architecture.get("ibm_cloud", {}).values():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                parts.extend(str(item.get(k) or "") for k in ("name", "purpose", "notes", "type"))
            else:
                parts.append(str(item))
    return " ".join(parts).lower()


def _has_text(architecture: dict, requirements_text: str, *tokens: str) -> bool:
    hay = _text(architecture, requirements_text)
    return any(token in hay for token in tokens)


def _pillar(name: str, score: int, evidence: list[str], gaps: list[str], recommendation: str) -> dict:
    if score >= 80:
        status = "Strong"
    elif score >= 50:
        status = "Needs detail"
    else:
        status = "At risk"
    return {
        "name": name,
        "score": score,
        "status": status,
        "evidence": evidence,
        "gaps": gaps,
        "recommendation": recommendation,
    }


def _score_pillars(architecture: dict, requirements_text: str = "") -> list[dict]:
    ibm_cloud = architecture.get("ibm_cloud", {})
    has_hybrid = _count(ibm_cloud, "connectivity") > 0
    has_tgw = _has_text(architecture, requirements_text, "transit gateway")
    has_vpc = _count(ibm_cloud, "vpcs") > 0
    has_regions = _count(ibm_cloud, "regions") > 0
    has_three_zones = _count(ibm_cloud, "zones") >= 3 or _has_text(architecture, requirements_text, "zone-1", "zone 1")
    has_backup = _count(ibm_cloud, "backup_dr") > 0
    has_security = _count(ibm_cloud, "security") > 0
    has_vpe = _count(ibm_cloud, "private_endpoints") > 0
    has_obs = _count(ibm_cloud, "observability") > 0
    has_compute = _count(ibm_cloud, "compute") > 0
    has_ingress = _count(ibm_cloud, "ingress") > 0
    has_data = _count(ibm_cloud, "data") > 0
    has_cost = _has_text(architecture, requirements_text, "cost", "budget", "sizing", "estimate", "finops", "reserved")

    return [
        _pillar(
            "Hybrid and portable",
            min(100, 25 + 25 * int(has_vpc) + 20 * int(has_hybrid) + 15 * int(has_tgw) + 15 * int(has_regions)),
            [label for label, ok in [
                ("VPC boundary identified", has_vpc),
                ("Hybrid connectivity identified", has_hybrid),
                ("Transit Gateway or interconnect path identified", has_tgw),
                ("Region selected", has_regions),
            ] if ok],
            [label for label, ok in [
                ("Confirm account/resource-group structure", has_vpc),
                ("Confirm on-premises, WAN, or cross-cloud connectivity", has_hybrid),
                ("Confirm inter-VPC routing domain", has_tgw),
            ] if not ok],
            "Confirm the landing-zone topology and make every external integration explicit.",
        ),
        _pillar(
            "Resiliency",
            min(100, 20 + 25 * int(has_three_zones) + 20 * int(has_backup) + 20 * int(has_ingress) + 15 * int(has_regions)),
            [label for label, ok in [
                ("Multi-zone placement indicated", has_three_zones),
                ("Backup or DR requirement identified", has_backup),
                ("Ingress/load-balancing path identified", has_ingress),
                ("Primary region identified", has_regions),
            ] if ok],
            [label for label, ok in [
                ("Define AZ spread for workload and data tiers", has_three_zones),
                ("Define RPO/RTO and replication approach", has_backup),
                ("Define load-balancer health-check behavior", has_ingress),
            ] if not ok],
            "Default production designs to an IBM Cloud MZR with explicit RPO/RTO targets.",
        ),
        _pillar(
            "Efficient operations",
            min(100, 20 + 35 * int(has_obs) + 20 * int(_has_text(architecture, requirements_text, "terraform", "schematics", "toolchain", "ci/cd", "continuous delivery")) + 25 * int(has_security)),
            [label for label, ok in [
                ("Logging/monitoring detected", has_obs),
                ("Automation or CI/CD detected", _has_text(architecture, requirements_text, "terraform", "schematics", "toolchain", "ci/cd", "continuous delivery")),
                ("Operational security services detected", has_security),
            ] if ok],
            [label for label, ok in [
                ("Add logging, monitoring, audit, and flow logs", has_obs),
                ("Confirm IaC and deployment automation", _has_text(architecture, requirements_text, "terraform", "schematics", "toolchain", "ci/cd", "continuous delivery")),
            ] if not ok],
            "Add observability and automation as first-class architecture components, not implementation afterthoughts.",
        ),
        _pillar(
            "Security and compliance",
            min(100, 15 + 30 * int(has_security) + 25 * int(has_vpe) + 15 * int(has_obs) + 15 * int(_has_text(architecture, requirements_text, "hpcs", "key protect", "scc", "compliance", "pci", "hipaa", "sox"))),
            [label for label, ok in [
                ("Security controls detected", has_security),
                ("Private endpoint strategy detected", has_vpe),
                ("Audit/observability detected", has_obs),
                ("Compliance or key-management requirement detected", _has_text(architecture, requirements_text, "hpcs", "key protect", "scc", "compliance", "pci", "hipaa", "sox")),
            ] if ok],
            [label for label, ok in [
                ("Define IAM, secrets, keys, security groups, and NACLs", has_security),
                ("Define VPE/private service access coverage", has_vpe),
                ("Confirm compliance evidence and audit trail", has_obs),
            ] if not ok],
            "Prefer private service access, customer-managed keys, and evidence collection for regulated workloads.",
        ),
        _pillar(
            "Performance",
            min(100, 20 + 25 * int(has_compute) + 20 * int(has_ingress) + 20 * int(has_data) + 15 * int(_has_text(architecture, requirements_text, "latency", "throughput", "iops", "autoscale", "scale"))),
            [label for label, ok in [
                ("Compute layer detected", has_compute),
                ("Ingress/load-balancing detected", has_ingress),
                ("Data tier detected", has_data),
                ("Performance targets detected", _has_text(architecture, requirements_text, "latency", "throughput", "iops", "autoscale", "scale")),
            ] if ok],
            [label for label, ok in [
                ("Confirm workload sizing and scale behavior", has_compute),
                ("Confirm latency-sensitive traffic paths", has_ingress),
                ("Confirm data gravity and throughput needs", has_data),
            ] if not ok],
            "Capture traffic paths, sizing, and data locality before finalizing the logical design.",
        ),
        _pillar(
            "Financial operations and sustainability",
            min(100, 20 + 30 * int(has_cost) + 20 * int(has_compute) + 15 * int(has_backup) + 15 * int(_has_text(architecture, requirements_text, "environment", "dev", "test", "prod"))),
            [label for label, ok in [
                ("Cost or sizing source detected", has_cost),
                ("Billable compute detected", has_compute),
                ("Backup/retention detected", has_backup),
                ("Environment separation detected", _has_text(architecture, requirements_text, "environment", "dev", "test", "prod")),
            ] if ok],
            [label for label, ok in [
                ("Add sizing, environment, and budget assumptions", has_cost),
                ("Confirm retention and DR cost posture", has_backup),
            ] if not ok],
            "Track sizing assumptions and environment scope so the seller can defend cost and capacity.",
        ),
    ]


def _logical_design(architecture: dict, pattern: dict | None) -> list[dict]:
    ibm_cloud = architecture.get("ibm_cloud", {})
    pattern_id = pattern.get("id") if pattern else "custom"
    vpc_count = _count(ibm_cloud, "vpcs")
    if pattern_id in {"hybrid-powervs-dr", "healthcare-regional-dr"}:
        topology = "Primary regional VPC paired with a DR regional VPC, each connected to adjacent PowerVS workspaces and governed by shared security, observability, and private-service-access controls."
    elif pattern_id in {"hub-and-spoke", "fsc"} or vpc_count > 1:
        topology = "Edge or management VPC connected to private workload VPCs through Transit Gateway."
    elif pattern_id == "powervs":
        topology = "VPC landing zone connected to PowerVS workspace through Cloud Connection or Transit Gateway."
    elif pattern_id == "roks":
        topology = "Red Hat OpenShift workload cluster in private subnets with controlled router or load-balancer ingress."
    else:
        topology = "Single IBM Cloud VPC in a Multi-Zone Region with public, private, management, and data subnet tiers."

    return [
        {"area": "Topology", "design": topology},
        {"area": "Ingress", "design": "Use CIS/WAF and VPC load balancing when the workload is public; keep workload nodes private."},
        {"area": "Connectivity", "design": "Use Transit Gateway for VPC-to-VPC paths and Direct Link or VPN for on-premises connectivity."},
        {"area": "Security", "design": "Represent IAM, Secrets Manager, key management, security groups, NACLs, and private endpoints explicitly."},
        {"area": "Operations", "design": "Show logging, monitoring, flow logs, Activity Tracker, backup, and DR as shared operational services."},
    ]


def _pattern_foundation(architecture: dict, pattern: dict | None, requirements_text: str = "") -> dict:
    render_plan = architecture.get("render_plan", {})
    pattern_id = str(render_plan.get("pattern") or (pattern or {}).get("id") or "").lower()
    has_powervs = bool(render_plan.get("has_powervs")) or _has_text(architecture, requirements_text, "powervs", "power virtual")
    has_dr = bool(render_plan.get("has_dr")) or _has_text(architecture, requirements_text, "dr site", "disaster recovery")
    has_healthcare = _has_text(architecture, requirements_text, "hipaa", "hippa", "healthcare", "medical imaging")

    if has_powervs and has_dr:
        name = "PowerVS with VPC landing zone + regional DR extension"
        rationale = "Use the IBM PowerVS with VPC landing zone pattern as the base, then extend it with a primary/DR regional topology, HA private connectivity, VPEs, and compliance evidence services."
        required = [
            "VPC services connected to PowerVS workspace",
            "Primary and DR regional VPC boundaries",
            "HA Direct Link or equivalent private connectivity",
            "Security and observability foundation services",
        ]
    elif pattern_id in {"hub-and-spoke", "fsc"}:
        name = "VPC landing zone Standard"
        rationale = "Use management/edge and workload VPC separation, Transit Gateway routing, private service access, and centralized security/operations services."
        required = [
            "Management or edge VPC",
            "Private workload VPC",
            "Transit Gateway routing domain",
            "Virtual Private Endpoints for IBM Cloud services",
        ]
    elif has_powervs:
        name = "PowerVS with VPC landing zone"
        rationale = "Use the IBM PowerVS landing-zone pattern to interconnect VPC services and PowerVS workspaces with required management and security components."
        required = [
            "PowerVS workspace",
            "VPC services boundary",
            "Cloud Connection or Transit Gateway",
            "Monitoring and compliance services",
        ]
    else:
        name = (pattern or {}).get("name") or "VPC landing zone foundation"
        rationale = "Use IBM deployable architecture patterns as a starting template, then customize regions, connectivity, subnet tiers, and controls to the customer facts."
        required = [
            "Explicit VPC and subnet tier boundaries",
            "Private service access strategy",
            "Security and observability foundation",
            "Documented resiliency posture",
        ]

    if has_healthcare:
        required.append("HIPAA evidence, key-management, and audit controls")

    return {
        "name": name,
        "rationale": rationale,
        "requiredElements": required,
    }


def _selected_pattern(architecture: dict) -> dict | None:
    render_plan = architecture.get("render_plan", {})
    pattern_id = str(render_plan.get("pattern") or "").strip()
    if not pattern_id:
        return None
    pattern_name = str(render_plan.get("pattern_name") or pattern_id).strip()
    score = render_plan.get("pattern_score")
    try:
        score_value = float(score) if score is not None else 100.0
    except (TypeError, ValueError):
        score_value = 100.0
    return {
        "id": pattern_id,
        "name": pattern_name,
        "description": "Selected design foundation persisted from requirements, AI review, or architect confirmation.",
        "url": "https://www.ibm.com/think/architectures/patterns",
        "score": round(score_value, 1),
        "matched": ["✓ Selected as the current render-plan foundation"],
        "missing": [],
    }


def review_architecture(architecture: dict, requirements_text: str = "") -> dict:
    patterns = match_patterns(architecture, requirements_text=requirements_text, top_n=3)
    selected = _selected_pattern(architecture)
    recommended = selected or (patterns[0] if patterns else None)
    alternatives = [pattern for pattern in patterns if not selected or pattern.get("id") != selected.get("id")]
    pillars = _score_pillars(architecture, requirements_text)
    gaps = find_design_gaps(architecture)
    high_priority = [gap for gap in gaps[:5]]

    weakest = sorted(pillars, key=lambda p: p["score"])[:2]
    next_actions = [
        f"Confirm the recommended IBM pattern: {recommended['name']} ({recommended['score']}% match)." if recommended else "Confirm the intended IBM reference architecture pattern.",
        "Answer the highest-impact design questions before generating the deployment diagram.",
        *[f"Strengthen {pillar['name']}: {pillar['recommendation']}" for pillar in weakest],
    ]

    return {
        "recommendedPattern": recommended,
        "alternativePatterns": alternatives[:3],
        "wellArchitected": pillars,
        "openDecisionCount": len(gaps),
        "priorityQuestions": high_priority,
        "sellerNextActions": next_actions,
        "patternFoundation": _pattern_foundation(architecture, recommended, requirements_text),
        "logicalDesign": _logical_design(architecture, recommended),
    }
