from __future__ import annotations

import json
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any


STYLE_MEMORY_FILENAME = "style-memory.json"
GLOBAL_STYLE_MEMORY_FILENAME = "style-memory-default.json"


def _style_value(style: str, key: str) -> str | None:
    match = re.search(rf"(?:^|;){re.escape(key)}=([^;]+)", style)
    return match.group(1) if match else None


def _clean_label(value: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(unescape(text).split())


def _median(values: list[float], default: float = 0) -> float:
    return round(statistics.median(values), 1) if values else default


def extract_style_memory(drawio_xml: str, *, name: str = "Network Picasso diagram style") -> dict[str, Any]:
    """Summarize label, spacing, and layout choices from a Draw.io document.

    The result is intentionally compact and prompt-ready. It is not a visual
    renderer; it captures stable preferences that can guide future generation
    and Bob/MCP cleanup passes.
    """
    root = ET.fromstring(drawio_xml)
    diagrams = root.findall(".//diagram")
    page_names = [diagram.attrib.get("name", "").strip() for diagram in diagrams if diagram.attrib.get("name")]

    font_sizes: Counter[int] = Counter()
    label_widths: list[float] = []
    label_heights: list[float] = []
    connector_labels = 0
    edge_count = 0
    vertex_count = 0
    container_count = 0
    page_widths: list[float] = []
    page_heights: list[float] = []

    for model in root.findall(".//mxGraphModel"):
        try:
            page_widths.append(float(model.attrib.get("pageWidth", "0")))
            page_heights.append(float(model.attrib.get("pageHeight", "0")))
        except ValueError:
            pass

    for cell in root.findall(".//mxCell"):
        style = cell.attrib.get("style", "")
        value = _clean_label(cell.attrib.get("value", ""))
        font_size = _style_value(style, "fontSize")
        if font_size and font_size.isdigit():
            font_sizes[int(font_size)] += 1
        if cell.attrib.get("edge") == "1":
            edge_count += 1
            if value:
                connector_labels += 1
            continue
        if cell.attrib.get("vertex") == "1":
            vertex_count += 1
            geometry = cell.find("mxGeometry")
            if geometry is not None:
                try:
                    width = float(geometry.attrib.get("width", "0"))
                    height = float(geometry.attrib.get("height", "0"))
                except ValueError:
                    width = 0
                    height = 0
                if value:
                    label_widths.append(width)
                    label_heights.append(height)
                if "container=1" in style or (width >= 250 and height >= 120):
                    container_count += 1

    preferred_font = font_sizes.most_common(1)[0][0] if font_sizes else 11
    page_width = _median(page_widths, 1600)
    page_height = _median(page_heights, 1100)
    average_label_width = _median(label_widths, 180)
    average_label_height = _median(label_heights, 32)
    density = round(vertex_count / max(1, len(page_names) or 1), 1)

    guidance = [
        "Keep service labels inside dedicated label bands or clearly below icons; do not place text directly on connector paths.",
        "Use balanced whitespace between IBM Cloud account, region, VPC, zone, subnet, PowerVS, and shared-services containers.",
        "Prefer orthogonal connector routing with labels offset from lines and arrowheads.",
        "Preserve the five-page IBM seller flow: Executive Overview, Context, Logical Architecture, Deployment, and Assumptions & Decisions.",
        f"Use approximately {preferred_font}px for service labels and reserve larger type for page titles and section headers.",
        f"Keep common labeled objects near {int(average_label_width)}x{int(average_label_height)} px or wider when labels are long.",
    ]

    return {
        "schemaVersion": 1,
        "name": name,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": "drawio-xml",
        "summary": (
            "Saved customer-ready Draw.io preferences for label sizing, spacing, connector routing, "
            "page order, and IBM Cloud architecture hierarchy."
        ),
        "pageOrder": page_names,
        "metrics": {
            "pageCount": len(page_names),
            "medianPageWidth": page_width,
            "medianPageHeight": page_height,
            "vertexCount": vertex_count,
            "edgeCount": edge_count,
            "containerCount": container_count,
            "connectorLabelCount": connector_labels,
            "averageObjectsPerPage": density,
            "fontSizes": dict(sorted(font_sizes.items())),
            "medianLabelWidth": average_label_width,
            "medianLabelHeight": average_label_height,
        },
        "preferences": {
            "serviceLabelFontSize": preferred_font,
            "medianLabelBox": {"width": average_label_width, "height": average_label_height},
            "pageSize": {"width": page_width, "height": page_height},
            "containerHierarchy": "IBM Cloud account -> region -> VPC/workspace -> zone/subnet/service",
            "connectorRouting": "orthogonal, low crossing, labels offset from paths",
            "density": "compact" if density > 80 else "balanced",
        },
        "promptGuidance": guidance,
    }


def style_memory_path(project_path: Path) -> Path:
    return project_path / STYLE_MEMORY_FILENAME


def global_style_memory_path(repo_root: Path) -> Path:
    return repo_root / "inputs" / GLOBAL_STYLE_MEMORY_FILENAME


def save_style_memory(project_path: Path, memory: dict[str, Any]) -> Path:
    path = style_memory_path(project_path)
    path.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    return path


def load_style_memory(project_path: Path) -> dict[str, Any] | None:
    path = style_memory_path(project_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_global_style_memory(repo_root: Path, memory: dict[str, Any]) -> Path:
    path = global_style_memory_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    return path


def load_global_style_memory(repo_root: Path) -> dict[str, Any] | None:
    path = global_style_memory_path(repo_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def style_memory_prompt(memory: dict[str, Any] | None) -> str:
    if not memory:
        return ""
    guidance = memory.get("promptGuidance") or []
    lines = [str(item).strip() for item in guidance if str(item).strip()]
    if not lines:
        return ""
    return "Saved Draw.io style memory:\n" + "\n".join(f"- {line}" for line in lines)


def style_memory_markdown(memory: dict[str, Any]) -> str:
    metrics = memory.get("metrics") or {}
    preferences = memory.get("preferences") or {}
    lines = [
        f"# {memory.get('name') or 'Network Picasso Style Memory'}",
        "",
        memory.get("summary") or "Saved Draw.io style preferences.",
        "",
        "## Preferred Guidance",
    ]
    for item in memory.get("promptGuidance") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Captured Metrics",
        "",
        f"- Pages: {metrics.get('pageCount', 0)}",
        f"- Page order: {', '.join(memory.get('pageOrder') or []) or 'Not captured'}",
        f"- Service label font size: {preferences.get('serviceLabelFontSize', 'Not captured')}",
        f"- Median label box: {metrics.get('medianLabelWidth', 0)} x {metrics.get('medianLabelHeight', 0)} px",
        f"- Connector routing: {preferences.get('connectorRouting', 'Not captured')}",
        "",
        "## How Network Picasso Uses This",
        "",
        "When saved globally, future Bob/MCP remediation prompts include this guidance by default. Project-level style memory can still override it for a specific customer project.",
    ])
    return "\n".join(lines) + "\n"
