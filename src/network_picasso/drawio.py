from __future__ import annotations

from html import escape
from itertools import count


class DrawioBuilder:
    def __init__(self) -> None:
        self._ids = count(2)
        self.cells: list[str] = [
            '<mxCell id="0" />',
            '<mxCell id="1" parent="0" />',
        ]

    def box(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: str = "#ffffff",
        stroke: str = "#6c8ebf",
        font_size: int = 12,
        font_style: int = 0,
        dashed: bool = False,
        align: str = "center",
        vertical_align: str = "middle",
    ) -> str:
        cell_id = f"n{next(self._ids)}"
        style = (
            "rounded=1;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};fontSize={font_size};"
            f"fontStyle={font_style};align={align};verticalAlign={vertical_align};"
        )
        if dashed:
            style += "dashed=1;"
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def edge(self, source: str, target: str, label: str = "") -> None:
        cell_id = f"e{next(self._ids)}"
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
            "jettySize=auto;html=1;fontSize=11;endArrow=block;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" edge="1" '
            f'source="{source}" target="{target}" parent="1">'
            '<mxGeometry relative="1" as="geometry" />'
            "</mxCell>"
        )

    def render(self) -> str:
        body = "\n    ".join(self.cells)
        return (
            '<mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            'pageScale="1" pageWidth="2200" pageHeight="1400" math="0" shadow="0">\n'
            "  <root>\n"
            f"    {body}\n"
            "  </root>\n"
            "</mxGraphModel>\n"
        )


def _label(item: dict, fallback: str) -> str:
    name = item.get("name") or fallback
    purpose = item.get("purpose")
    if purpose:
        return f"{name}\n{purpose}"
    return name


def render_drawio(architecture: dict, *, diagram_type: str) -> str:
    project = architecture.get("project", {})
    ibm_cloud = architecture.get("ibm_cloud", {})
    builder = DrawioBuilder()

    title = project.get("name", "IBM Cloud Architecture")
    builder.box(
        f"{title}\n{diagram_type.title()} Architecture",
        440,
        20,
        920,
        60,
        fill="#ffffff",
        stroke="#ffffff",
        font_size=22,
        font_style=1,
    )

    external = builder.box(
        "External Users / Systems",
        60,
        160,
        240,
        440,
        fill="#dae8fc",
        stroke="#6c8ebf",
        font_style=1,
        vertical_align="top",
    )
    cloud = builder.box(
        "IBM Cloud Account",
        360,
        110,
        1460,
        720,
        fill="#f7f8fa",
        stroke="#3b82d4",
        font_size=15,
        font_style=1,
        vertical_align="top",
    )

    users = builder.box("Users / Clients", 90, 220, 180, 70, fill="#ffffff")
    external_systems = builder.box("External Systems", 90, 330, 180, 70, fill="#ffffff")
    builder.edge(users, cloud, "requests")
    builder.edge(external_systems, cloud, "integration")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    region_nodes: list[str] = []
    for index, region in enumerate(regions[:2]):
        x = 400 + index * 700
        region_node = builder.box(
            _label(region, "Region"),
            x,
            160,
            640,
            520,
            fill="#eef4ff",
            stroke="#3b82d4",
            font_style=1,
            vertical_align="top",
        )
        region_nodes.append(region_node)

        vpcs = ibm_cloud.get("vpcs") or [{"name": "VPC TBD", "purpose": "Application network"}]
        vpc = vpcs[min(index, len(vpcs) - 1)]
        vpc_node = builder.box(
            _label(vpc, "VPC"),
            x + 30,
            230,
            580,
            330,
            fill="#ffffff",
            stroke="#6c8ebf",
            font_style=1,
            vertical_align="top",
        )
        builder.edge(region_node, vpc_node, "")

        ingress = ibm_cloud.get("ingress") or [{"name": "Ingress TBD"}]
        ingress_node = builder.box(_label(ingress[0], "Ingress"), x + 60, 285, 150, 70, fill="#dae8fc")
        compute = ibm_cloud.get("compute") or [{"name": "Compute TBD"}]
        compute_node = builder.box(_label(compute[0], "Compute"), x + 245, 285, 150, 70, fill="#d5e8d4")
        data = ibm_cloud.get("data") or [{"name": "Data Services TBD"}]
        data_node = builder.box(_label(data[0], "Data"), x + 430, 285, 150, 70, fill="#e1d5e7")
        builder.edge(ingress_node, compute_node, "app traffic")
        builder.edge(compute_node, data_node, "private data access")

        security = ibm_cloud.get("security") or [{"name": "IAM / Secrets / Keys TBD"}]
        security_node = builder.box(_label(security[0], "Security"), x + 60, 440, 240, 70, fill="#ffe6cc")
        observability = ibm_cloud.get("observability") or [{"name": "Monitoring / Logging TBD"}]
        obs_node = builder.box(_label(observability[0], "Observability"), x + 340, 440, 240, 70, fill="#fff2cc")
        builder.edge(security_node, compute_node, "identity and secrets")
        builder.edge(compute_node, obs_node, "logs and metrics")

    connectivity = ibm_cloud.get("connectivity") or [{"name": "Connectivity TBD"}]
    connectivity_node = builder.box(
        _label(connectivity[0], "Connectivity"),
        380,
        720,
        420,
        70,
        fill="#dae8fc",
        stroke="#6c8ebf",
    )
    for region_node in region_nodes:
        builder.edge(connectivity_node, region_node, "network path")

    return builder.render()
