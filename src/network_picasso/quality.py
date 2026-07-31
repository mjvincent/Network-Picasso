from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any
from xml.etree import ElementTree


IBM_PATTERN_URL = "https://www.ibm.com/think/architectures/patterns"


@dataclass(frozen=True)
class Finding:
    severity: str
    area: str
    message: str
    recommendation: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "area": self.area,
            "message": self.message,
            "recommendation": self.recommendation,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class DiagramCell:
    cell_id: str
    parent: str
    value: str
    style: str
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


PATTERN_CHECKS = {
    "hybrid-powervs-dr": {
        "name": "Power Virtual Server with VPC landing zone",
        "source": IBM_PATTERN_URL,
        "required": [
            ("PowerVS workspace", ("powervs workspace", "power virtual server", "powervs servers")),
            ("Primary VPC or landing zone VPC", ("dal vpc", "primary vpc", "workload vpc", "vpc landing")),
            ("DR region or DR recovery tier", ("dr region", "us-east dr", "wdc vpc", "disaster recovery")),
            ("HA private connectivity", ("direct link", "private connectivity", "cloud connection")),
            ("Private endpoints", ("virtual private endpoint", "vpe")),
            ("Security key management", ("key protect", "hpcs", "secrets manager")),
            ("Operations evidence", ("activity tracker", "vpc flow logs", "monitoring", "logging")),
        ],
    },
    "vsi-vpc": {
        "name": "VSI on VPC landing zone - Standard",
        "source": IBM_PATTERN_URL,
        "required": [
            ("VPC landing zone", ("vpc", "landing zone")),
            ("Virtual server workload tier", ("vsi", "virtual server")),
            ("Multizone posture", ("zone 1", "zone 2", "zone 3", "multizone")),
            ("Private endpoints", ("virtual private endpoint", "vpe")),
            ("Security services", ("security and compliance", "key protect", "secrets manager")),
            ("Observability services", ("activity tracker", "flow logs", "monitoring", "logging")),
        ],
    },
    "mzr": {
        "name": "VPC landing zone - Standard",
        "source": IBM_PATTERN_URL,
        "required": [
            ("Management and workload VPC boundaries", ("management", "workload vpc", "vpc")),
            ("Multizone layout", ("zone 1", "zone 2", "zone 3", "multizone")),
            ("Transit Gateway when multiple VPCs are used", ("transit gateway",)),
            ("Virtual Private Endpoints", ("virtual private endpoint", "vpe")),
            ("Security and audit foundation", ("security and compliance", "activity tracker", "flow logs")),
        ],
    },
    "hub-and-spoke": {
        "name": "VPC landing zone - Standard",
        "source": IBM_PATTERN_URL,
        "required": [
            ("Edge VPC", ("edge vpc",)),
            ("Workload VPC", ("workload vpc",)),
            ("Transit Gateway", ("transit gateway",)),
            ("Private endpoints", ("virtual private endpoint", "vpe")),
            ("Security and observability foundation", ("security and compliance", "activity tracker", "flow logs")),
        ],
    },
    "roks": {
        "name": "Red Hat OpenShift Container Platform on VPC landing zone",
        "source": IBM_PATTERN_URL,
        "required": [
            ("ROKS or OpenShift workload cluster", ("roks", "openshift", "red hat openshift", "ocp")),
            ("VPC landing zone", ("vpc", "landing zone")),
            ("Private worker subnet tier", ("private subnet", "worker", "worker pool")),
            ("Ingress strategy", ("openshift router", "route", "ingress", "alb", "cis")),
            ("Registry and image security", ("container registry", "registry", "icr", "vulnerability")),
            ("Security and audit foundation", ("security and compliance", "key protect", "secrets manager", "activity tracker")),
            ("Observability services", ("monitoring", "logging", "flow logs", "instana")),
        ],
    },
}


def analyze_diagram_quality(
    architecture: dict,
    *,
    diagram_type: str,
    xml: str,
) -> dict[str, Any]:
    """Return deterministic Draw.io quality and IBM pattern-alignment findings."""
    cells = _extract_cells(xml)
    text_blob = _search_blob(architecture, xml)
    pattern_id = _pattern_id(architecture, text_blob)

    findings: list[Finding] = []
    findings.extend(_check_label_fit(cells))
    findings.extend(_check_cell_overlap(cells))
    findings.extend(_check_ibm_pattern_alignment(pattern_id, text_blob))
    findings.extend(_check_diagram_specifics(diagram_type, text_blob, cells))

    score = _score(findings)
    return {
        "score": score,
        "status": _status(score),
        "diagramType": diagram_type,
        "pattern": pattern_id,
        "ibmPatternSource": IBM_PATTERN_URL,
        "checkedCells": len(cells),
        "summary": _summary(score, findings),
        "findings": [finding.as_dict() for finding in findings],
        "ibmPatternChecks": _pattern_check_result(pattern_id, text_blob),
    }


def apply_quality_remediations(architecture: dict, review: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic, model-safe remediations from a quality review.

    The function updates architecture metadata and adds missing IBM pattern
    foundation components. Visual layout findings are returned as deferred
    actions because those require Draw.io page edits rather than model changes.
    """
    applied: list[dict[str, str]] = []
    deferred: list[dict[str, str]] = []
    ibm_cloud = architecture.setdefault("ibm_cloud", {})
    render_plan = architecture.setdefault("render_plan", {})
    decisions = architecture.setdefault("decisions", {})

    pattern = str(review.get("pattern") or "").strip()
    if pattern and pattern != "unclassified":
        render_plan.setdefault("pattern", pattern)
        render_plan.setdefault("pattern_source", "quality-analyzer")
        pattern_checks = review.get("ibmPatternChecks") or {}
        decisions["ibmPatternTraceability"] = {
            "id": pattern,
            "name": str(pattern_checks.get("name") or pattern),
            "source": str(review.get("ibmPatternSource") or IBM_PATTERN_URL),
            "status": "review-required",
            "present": [
                check.get("name")
                for check in pattern_checks.get("checks", [])
                if isinstance(check, dict) and check.get("present")
            ],
            "missing": [
                check.get("name")
                for check in pattern_checks.get("checks", [])
                if isinstance(check, dict) and not check.get("present")
            ],
            "sellerAction": "Confirm analyzer-added foundation services with the customer before final design approval.",
        }
        applied.append({
            "area": "IBM pattern foundation",
            "change": f"Recorded IBM pattern foundation '{pattern}' in the render plan.",
        })

    for check in (review.get("ibmPatternChecks") or {}).get("checks", []):
        if check.get("present"):
            continue
        component = _component_for_pattern_check(str(check.get("name") or ""))
        if component and component["category"] == "compute" and component["item"]["name"] == "PowerVS workspace":
            if not _has_explicit_powervs_evidence(architecture):
                deferred.append({
                    "area": "IBM pattern alignment",
                    "change": "Skipped PowerVS recommendation because the customer requirements do not mention PowerVS or Power Virtual Server.",
                })
                continue
        if not component:
            deferred.append({
                "area": "IBM pattern alignment",
                "change": f"Review missing element manually: {check.get('name')}",
            })
            continue
        if _ensure_component(ibm_cloud, component["category"], component["item"]):
            applied.append({
                "area": "IBM pattern alignment",
                "change": f"Added {component['item']['name']} to {component['category']} as a quality-analyzer recommendation.",
            })

    for finding in review.get("findings", []):
        area = str(finding.get("area") or "")
        if area in {"Label fit", "Overlap risk", "Diagram density"}:
            deferred.append({
                "area": area,
                "change": str(finding.get("recommendation") or "Use Bob/MCP to make presentation-safe layout edits."),
            })

    if deferred:
        render_plan["presentation_review_required"] = True
        decisions["presentationReview"] = {
            "required": True,
            "source": "quality-analyzer",
            "items": deferred,
            "sellerAction": "Open the diagram in the MCP editor, use the copied Bob prompt, then re-run quality analysis.",
        }
    if applied or deferred:
        architecture.setdefault("quality", {})["lastRemediation"] = {
            "applied": applied,
            "deferred": deferred,
            "source": "quality-analyzer",
        }
    return {"applied": applied, "deferred": deferred, "architecture": architecture}


def _has_explicit_powervs_evidence(architecture: dict[str, Any]) -> bool:
    evidence_parts: list[str] = []
    ibm_cloud = architecture.get("ibm_cloud", {})
    if isinstance(ibm_cloud, dict):
        for items in ibm_cloud.values():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    evidence_parts.extend(str(item.get(key) or "") for key in ("name", "purpose", "notes"))
    for req in architecture.get("requirements", []) or []:
        if isinstance(req, dict):
            evidence_parts.append(str(req.get("text") or ""))
        else:
            evidence_parts.append(str(req))
    context = " ".join(evidence_parts).lower()
    return "powervs" in context or "power virtual" in context or "power virtual server" in context


def _extract_cells(xml: str) -> list[DiagramCell]:
    root = ElementTree.fromstring(xml)
    cells: list[DiagramCell] = []
    for cell in root.iter("mxCell"):
        if cell.attrib.get("vertex") != "1":
            continue
        geo = cell.find("mxGeometry")
        if geo is None:
            continue
        width = _float_attr(geo, "width")
        height = _float_attr(geo, "height")
        if width <= 0 or height <= 0:
            continue
        cells.append(
            DiagramCell(
                cell_id=cell.attrib.get("id", ""),
                parent=cell.attrib.get("parent", ""),
                value=_clean_value(cell.attrib.get("value", "")),
                style=cell.attrib.get("style", ""),
                x=_float_attr(geo, "x"),
                y=_float_attr(geo, "y"),
                width=width,
                height=height,
            )
        )
    return cells


def _check_label_fit(cells: list[DiagramCell]) -> list[Finding]:
    findings: list[Finding] = []
    for cell in cells:
        if not cell.value or _is_icon_only(cell) or cell.width < 42:
            continue
        lines = _label_lines(cell.value)
        if not lines:
            continue
        font_size = _font_size(cell.style)
        longest = max(len(line) for line in lines)
        estimated_width = longest * font_size * 0.58
        estimated_height = len(lines) * (font_size + 3) + 4
        if estimated_width > cell.width - 10 or estimated_height > cell.height + 2:
            findings.append(
                Finding(
                    "warning",
                    "Label fit",
                    f"Label may overflow its shape: '{_short(cell.value)}'.",
                    "Increase the shape width, shorten the label, or move secondary detail into a separate annotation.",
                    (f"cell={cell.cell_id}", f"size={cell.width:.0f}x{cell.height:.0f}"),
                )
            )
    return findings[:12]


def _check_cell_overlap(cells: list[DiagramCell]) -> list[Finding]:
    candidates = [
        cell for cell in cells
        if cell.value and cell.area >= 1200 and not _is_container(cell) and not _is_icon_only(cell)
    ]
    findings: list[Finding] = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1:]:
            if first.parent != second.parent:
                continue
            overlap = _overlap_area(first, second)
            if overlap <= 0:
                continue
            ratio = overlap / max(1.0, min(first.area, second.area))
            if ratio >= 0.18:
                findings.append(
                    Finding(
                        "warning",
                        "Overlap risk",
                        f"Two labeled objects appear too close or overlapping: '{_short(first.value)}' and '{_short(second.value)}'.",
                        "Separate these cells or route connectors outside the labeled area before presenting the diagram.",
                        (f"cells={first.cell_id},{second.cell_id}", f"overlap={ratio:.0%}"),
                    )
                )
    return findings[:8]


def _check_ibm_pattern_alignment(pattern_id: str, text_blob: str) -> list[Finding]:
    result = _pattern_check_result(pattern_id, text_blob)
    findings: list[Finding] = []
    if not result["checks"]:
        findings.append(
            Finding(
                "info",
                "IBM pattern alignment",
                "No explicit IBM pattern was detected for this diagram.",
                "Run the Architecture Advisor and confirm the IBM Think pattern before using this with a customer.",
                (IBM_PATTERN_URL,),
            )
        )
        return findings

    for check in result["checks"]:
        if check["present"]:
            continue
        findings.append(
            Finding(
                "warning",
                "IBM pattern alignment",
                f"Missing or unclear IBM pattern element: {check['name']}.",
                f"Add or label this element to better align with {result['name']}.",
                (result["source"],),
            )
        )
    return findings


def _check_diagram_specifics(diagram_type: str, text_blob: str, cells: list[DiagramCell]) -> list[Finding]:
    findings: list[Finding] = []
    if diagram_type == "deployment":
        if "shared services" not in text_blob and "compliance foundation" not in text_blob:
            findings.append(
                Finding(
                    "warning",
                    "Deployment completeness",
                    "Deployment diagram does not clearly show a shared services or compliance foundation.",
                    "Add a shared-services foundation for security, observability, private endpoints, and data services.",
                )
            )
        if "direct link" in text_blob and "enterprise" not in text_blob:
            findings.append(
                Finding(
                    "info",
                    "Hybrid context",
                    "Private connectivity is present, but the enterprise-side source is not clearly labeled.",
                    "Label the enterprise/on-premises source and the business traffic flow that uses Direct Link.",
                )
            )
    if diagram_type in {"logical", "deployment"}:
        labeled = [cell for cell in cells if cell.value and not _is_icon_only(cell)]
        if len(labeled) > 75:
            findings.append(
                Finding(
                    "info",
                    "Diagram density",
                    "The diagram has a high number of labeled objects.",
                    "Consider using the Context or Executive page for seller conversations and reserve this view for implementation detail.",
                    (f"labeledCells={len(labeled)}",),
                )
            )
    return findings


def _pattern_check_result(pattern_id: str, text_blob: str) -> dict[str, Any]:
    spec = PATTERN_CHECKS.get(pattern_id)
    if not spec:
        return {"id": pattern_id, "name": "Unclassified IBM pattern", "source": IBM_PATTERN_URL, "checks": []}
    checks = []
    for name, tokens in spec["required"]:
        checks.append({
            "name": name,
            "present": any(token in text_blob for token in tokens),
            "tokens": list(tokens),
        })
    return {"id": pattern_id, "name": spec["name"], "source": spec["source"], "checks": checks}


def _component_for_pattern_check(name: str) -> dict[str, Any] | None:
    lower = name.lower()
    if "powervs" in lower or "power virtual server" in lower:
        return _component("compute", "PowerVS workspace", "IBM Power Virtual Server workspace for dependent workloads.")
    if "edge vpc" in lower:
        return _component("vpcs", "Edge VPC", "Ingress, egress, and hybrid connectivity boundary.")
    if "workload vpc" in lower:
        return _component("vpcs", "Workload VPC", "Private application and data tiers.")
    if "vpc" in lower or "landing zone" in lower:
        return _component("vpcs", "VPC landing zone", "IBM Cloud VPC landing zone foundation.")
    if "dr" in lower or "recovery" in lower or "disaster" in lower:
        return _component("backup_dr", "DR recovery tier", "Disaster recovery target and runbook evidence.")
    if "direct link" in lower or "private connectivity" in lower or "connectivity" in lower:
        return _component("connectivity", "Direct Link 2.0", "Private hybrid connectivity between enterprise sites and IBM Cloud.")
    if "transit gateway" in lower:
        return _component("connectivity", "Transit Gateway", "Hub connectivity between VPCs and attached networks.")
    if "private endpoint" in lower or "vpe" in lower:
        return _component("private_endpoints", "Virtual Private Endpoints for IBM Cloud services", "Private service access without public internet traversal.")
    if "security" in lower or "key" in lower or "audit" in lower:
        return _component("security", "Security and Compliance Center", "Compliance posture, evidence collection, and security governance.")
    if "observability" in lower or "operations" in lower or "flow logs" in lower:
        return _component("observability", "Activity Tracker and VPC Flow Logs", "Audit events, network flow evidence, monitoring, and logging.")
    if "multizone" in lower or "zone" in lower:
        return _component("zones", "Zone 1 / Zone 2 / Zone 3", "Multizone placement target for resilient workloads.")
    return None


def _component(category: str, name: str, purpose: str) -> dict[str, Any]:
    return {
        "category": category,
        "item": {
            "name": name,
            "type": category,
            "purpose": purpose,
            "source": "quality-analyzer",
            "notes": "Added by Apply analyzer fixes; confirm with the customer before final design approval.",
        },
    }


def _ensure_component(ibm_cloud: dict, category: str, item: dict[str, Any]) -> bool:
    items = ibm_cloud.setdefault(category, [])
    if not isinstance(items, list):
        ibm_cloud[category] = items = []
    new_name = str(item.get("name") or "").lower()
    for existing in items:
        if isinstance(existing, dict) and str(existing.get("name") or "").lower() == new_name:
            return False
        if isinstance(existing, str) and existing.lower() == new_name:
            return False
    items.append(item)
    return True


def _pattern_id(architecture: dict, text_blob: str) -> str:
    plan = architecture.get("render_plan") if isinstance(architecture, dict) else {}
    if isinstance(plan, dict) and plan.get("pattern"):
        return str(plan.get("pattern"))
    if "powervs" in text_blob and ("dr region" in text_blob or "disaster recovery" in text_blob):
        return "hybrid-powervs-dr"
    if "edge vpc" in text_blob and "workload vpc" in text_blob:
        return "hub-and-spoke"
    if "vsi" in text_blob or "virtual server" in text_blob:
        return "vsi-vpc"
    return "mzr" if "vpc" in text_blob else "unclassified"


def _search_blob(architecture: dict, xml: str) -> str:
    return f"{architecture} {unescape(xml)}".lower()


def _score(findings: list[Finding]) -> int:
    penalty = 0
    for finding in findings:
        if finding.severity == "error":
            penalty += 18
        elif finding.severity == "warning":
            penalty += 6
        else:
            penalty += 2
    return max(0, 100 - penalty)


def _status(score: int) -> str:
    if score >= 85:
        return "Professional"
    if score >= 70:
        return "Needs polish"
    return "Needs attention"


def _summary(score: int, findings: list[Finding]) -> str:
    if not findings:
        return "No material diagram quality or IBM pattern-alignment issues found."
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    infos = sum(1 for finding in findings if finding.severity == "info")
    return f"Score {score}; {warnings} warning(s), {infos} informational note(s)."


def _clean_value(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _label_lines(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\\n|\n| {2,}", value) if part.strip()]


def _float_attr(element: ElementTree.Element, name: str) -> float:
    try:
        return float(element.attrib.get(name, "0") or 0)
    except ValueError:
        return 0.0


def _font_size(style: str) -> int:
    match = re.search(r"fontSize=(\d+)", style)
    return int(match.group(1)) if match else 11


def _is_container(cell: DiagramCell) -> bool:
    return "container=1" in cell.style or cell.width >= 250 and cell.height >= 120


def _is_icon_only(cell: DiagramCell) -> bool:
    return (
        "shape=mxgraph.ibm_cloud" in cell.style
        or "shape=rect" in cell.style and "strokeColor=none" in cell.style and cell.width <= 56
    )


def _overlap_area(first: DiagramCell, second: DiagramCell) -> float:
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.x + first.width, second.x + second.width)
    bottom = min(first.y + first.height, second.y + second.height)
    if right <= left or bottom <= top:
        return 0.0
    return (right - left) * (bottom - top)


def _short(value: str, limit: int = 64) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}..."
