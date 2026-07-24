from __future__ import annotations

from html import escape
from itertools import count

# ---------------------------------------------------------------------------
# Layout constants — IBM Cloud VPC deployment topology
# ---------------------------------------------------------------------------

# Account / region / VPC chrome
ACCOUNT_X = 60
ACCOUNT_Y = 100
ACCOUNT_W = 2060
ACCOUNT_H = 1100

REGION_MARGIN_X = 40
REGION_MARGIN_Y = 60
REGION_W = 960
REGION_H = 940
REGION_SPACING = 1040   # horizontal gap between region boxes

VPC_MARGIN_X = 30
VPC_MARGIN_Y = 60
VPC_W = REGION_W - 2 * VPC_MARGIN_X          # 900
VPC_H = REGION_H - VPC_MARGIN_Y - 40         # 840

# Availability zone columns (three per VPC, side-by-side)
AZ_COUNT = 3
AZ_SPACING = 10
AZ_W = (VPC_W - (AZ_COUNT + 1) * AZ_SPACING) // AZ_COUNT  # ≈ 283
AZ_H = VPC_H - 60                            # leave room for VPC label

# Subnet bands inside each AZ (Public, Private, Management, Data — top to bottom)
BAND_LABELS = ["Public", "Private", "Management", "Data"]
BAND_HEIGHTS = [130, 200, 130, 130]          # px per band; Private is tallest
BAND_PADDING_X = 8
BAND_PADDING_Y = 30                          # space below band label before nodes

# IBM Cloud color palette (official stencil convention)
COLOR = {
    # Structural chrome
    "account_fill":   "#f7f8fa",
    "account_stroke": "#3b82d4",
    "region_fill":    "#eef4ff",
    "region_stroke":  "#3b82d4",
    "vpc_fill":       "#ffffff",
    "vpc_stroke":     "#6c8ebf",
    "az_fill":        "#f4f4f4",
    "az_stroke":      "#8d8d8d",
    # Subnet tier fills (also used for component chips)
    "Public":       "#dae8fc",
    "Private":      "#d5e8d4",
    "Management":   "#fff2cc",
    "Data":         "#e1d5e7",
    # Special zone fills
    "external_fill":    "#dae8fc",
    "external_stroke":  "#6c8ebf",
    "connectivity_fill": "#dae8fc",
    "connectivity_stroke": "#6c8ebf",
    # PowerVS
    "powervs_fill":   "#f4e6ff",
    "powervs_stroke": "#7c5cd8",
    # Transit Gateway
    "tgw_fill":   "#002d9c",
    "tgw_font":   "#ffffff",
}

# Map component type → subnet tier
TYPE_TO_TIER: dict[str, str] = {
    "ingress":       "Public",
    "compute":       "Private",
    "security":      "Management",
    "observability": "Management",
    "data":          "Data",
}


# ---------------------------------------------------------------------------
# DrawioBuilder
# ---------------------------------------------------------------------------

class DrawioBuilder:
    def __init__(self) -> None:
        self._ids = count(2)
        self.cells: list[str] = [
            '<mxCell id="0" />',
            '<mxCell id="1" parent="0" />',
        ]

    # ------------------------------------------------------------------
    # Core primitives
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Topology helpers
    # ------------------------------------------------------------------

    def zone_column(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> str:
        """Render an availability zone boundary box with a label at the top."""
        cell_id = f"n{next(self._ids)}"
        style = (
            "swimlane;startSize=24;fillColor={fill};strokeColor={stroke};"
            "fontStyle=1;fontSize=11;align=center;"
        ).format(fill=COLOR["az_fill"], stroke=COLOR["az_stroke"])
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def subnet_band(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
        tier: str,
    ) -> str:
        """Render a subnet tier band. *tier* drives fill color."""
        fill = COLOR.get(tier, "#ffffff")
        cell_id = f"n{next(self._ids)}"
        style = (
            f"fillColor={fill};strokeColor={COLOR['az_stroke']};"
            "rounded=0;whiteSpace=wrap;html=1;"
            "fontStyle=1;fontSize=10;align=left;verticalAlign=top;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def powervs_workspace(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> str:
        """Render a PowerVS workspace boundary box (dashed, purple tint)."""
        cell_id = f"n{next(self._ids)}"
        style = (
            f"fillColor={COLOR['powervs_fill']};strokeColor={COLOR['powervs_stroke']};"
            "rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=8 4;"
            "fontStyle=1;fontSize=12;verticalAlign=top;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def transit_gateway_hub(self, label: str, x: int, y: int) -> str:
        """Render a Transit Gateway hub node (small square, IBM dark blue)."""
        cell_id = f"n{next(self._ids)}"
        style = (
            f"fillColor={COLOR['tgw_fill']};strokeColor={COLOR['tgw_fill']};"
            f"fontColor={COLOR['tgw_font']};"
            "rounded=1;whiteSpace=wrap;html=1;fontStyle=1;fontSize=11;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="160" height="50" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def vpe_gateway(self, label: str, x: int, y: int, parent_id: str) -> str:
        """Render a VPE gateway node and a dotted edge back to *parent_id*."""
        cell_id = f"n{next(self._ids)}"
        style = (
            "shape=rhombus;fillColor=#ffffff;strokeColor=#6c8ebf;"
            "whiteSpace=wrap;html=1;fontSize=9;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="80" height="50" as="geometry" />'
            "</mxCell>"
        )
        edge_id = f"e{next(self._ids)}"
        edge_style = (
            "edgeStyle=orthogonalEdgeStyle;dashed=1;endArrow=open;endFill=0;"
            "rounded=0;html=1;fontSize=9;"
        )
        self.cells.append(
            f'<mxCell id="{edge_id}" value="" style="{edge_style}" edge="1" '
            f'source="{cell_id}" target="{parent_id}" parent="1">'
            '<mxGeometry relative="1" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

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


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _label(item: dict, fallback: str) -> str:
    name = item.get("name") or fallback
    purpose = item.get("purpose")
    if purpose:
        return f"{name}\n{purpose}"
    return name


def _preferred(items: list[dict] | None, fallback: dict) -> dict:
    if not items:
        return fallback
    return sorted(
        items,
        key=lambda item: (
            0 if item.get("purpose") else 1,
            0 if item.get("region") else 1,
            len(item.get("name", "")),
        ),
    )[0]


def _has_powervs(ibm_cloud: dict) -> bool:
    """Return True if any compute component looks like a PowerVS workload."""
    for comp in ibm_cloud.get("compute", []):
        name = (comp.get("name") or "").lower()
        purpose = (comp.get("purpose") or "").lower()
        if "power" in name or "powervs" in name or "power" in purpose:
            return True
    return False


def _has_transit_gateway(ibm_cloud: dict) -> bool:
    for conn in ibm_cloud.get("connectivity", []):
        name = (conn.get("name") or "").lower()
        if "transit" in name:
            return True
    return False


# ---------------------------------------------------------------------------
# Diagram-type renderers
# ---------------------------------------------------------------------------

def _render_title(builder: DrawioBuilder, project: dict, diagram_type: str) -> None:
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


def _render_context(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    """High-level context diagram — equivalent to the original render_drawio() output."""
    _render_title(builder, project, "context")

    external = builder.box(
        "External Users / Systems",
        60,
        160,
        240,
        440,
        fill=COLOR["external_fill"],
        stroke=COLOR["external_stroke"],
        font_style=1,
        vertical_align="top",
    )
    cloud = builder.box(
        "IBM Cloud Account",
        360,
        110,
        1460,
        720,
        fill=COLOR["account_fill"],
        stroke=COLOR["account_stroke"],
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
            fill=COLOR["region_fill"],
            stroke=COLOR["region_stroke"],
            font_style=1,
            vertical_align="top",
        )
        region_nodes.append(region_node)

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC TBD", "purpose": "Application network"})
        vpc_node = builder.box(
            _label(vpc, "VPC"),
            x + 30,
            230,
            580,
            330,
            fill=COLOR["vpc_fill"],
            stroke=COLOR["vpc_stroke"],
            font_style=1,
            vertical_align="top",
        )
        builder.edge(region_node, vpc_node, "")

        ingress = _preferred(ibm_cloud.get("ingress"), {"name": "Ingress TBD"})
        ingress_node = builder.box(_label(ingress, "Ingress"), x + 60, 285, 150, 70, fill=COLOR["Public"])
        compute = _preferred(ibm_cloud.get("compute"), {"name": "Compute TBD"})
        compute_node = builder.box(_label(compute, "Compute"), x + 245, 285, 150, 70, fill=COLOR["Private"])
        data = _preferred(ibm_cloud.get("data"), {"name": "Data Services TBD"})
        data_node = builder.box(_label(data, "Data"), x + 430, 285, 150, 70, fill=COLOR["Data"])
        builder.edge(ingress_node, compute_node, "app traffic")
        builder.edge(compute_node, data_node, "private data access")

        security = _preferred(ibm_cloud.get("security"), {"name": "IAM / Secrets / Keys TBD"})
        security_node = builder.box(_label(security, "Security"), x + 60, 440, 240, 70, fill="#ffe6cc")
        observability = _preferred(ibm_cloud.get("observability"), {"name": "Monitoring / Logging TBD"})
        obs_node = builder.box(_label(observability, "Observability"), x + 340, 440, 240, 70, fill=COLOR["Management"])
        builder.edge(security_node, compute_node, "identity and secrets")
        builder.edge(compute_node, obs_node, "logs and metrics")

    connectivity = [_preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity TBD"})]
    connectivity_node = builder.box(
        _label(connectivity[0], "Connectivity"),
        380,
        720,
        420,
        70,
        fill=COLOR["connectivity_fill"],
        stroke=COLOR["connectivity_stroke"],
    )
    for rn in region_nodes:
        builder.edge(connectivity_node, rn, "network path")


def _render_logical(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    """Logical diagram — same chrome as context but adds connectivity layer detail."""
    _render_title(builder, project, "logical")

    external = builder.box(
        "External Users / Systems",
        60,
        160,
        240,
        440,
        fill=COLOR["external_fill"],
        stroke=COLOR["external_stroke"],
        font_style=1,
        vertical_align="top",
    )
    cloud = builder.box(
        "IBM Cloud Account",
        360,
        110,
        1460,
        720,
        fill=COLOR["account_fill"],
        stroke=COLOR["account_stroke"],
        font_size=15,
        font_style=1,
        vertical_align="top",
    )

    users = builder.box("Users / Clients", 90, 220, 180, 70, fill="#ffffff")
    ext_sys = builder.box("External Systems", 90, 330, 180, 70, fill="#ffffff")
    builder.edge(users, cloud, "requests")
    builder.edge(ext_sys, cloud, "integration")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    region_nodes: list[str] = []
    vpc_nodes: list[str] = []

    for index, region in enumerate(regions[:2]):
        x = 400 + index * 700
        region_node = builder.box(
            _label(region, "Region"),
            x, 160, 640, 520,
            fill=COLOR["region_fill"], stroke=COLOR["region_stroke"],
            font_style=1, vertical_align="top",
        )
        region_nodes.append(region_node)

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC TBD", "purpose": "Application network"})
        vpc_node = builder.box(
            _label(vpc, "VPC"),
            x + 30, 230, 580, 330,
            fill=COLOR["vpc_fill"], stroke=COLOR["vpc_stroke"],
            font_style=1, vertical_align="top",
        )
        vpc_nodes.append(vpc_node)

        ingress = _preferred(ibm_cloud.get("ingress"), {"name": "Ingress TBD"})
        ingress_node = builder.box(_label(ingress, "Ingress"), x + 50, 285, 160, 60, fill=COLOR["Public"])
        compute = _preferred(ibm_cloud.get("compute"), {"name": "Compute TBD"})
        compute_node = builder.box(_label(compute, "Compute"), x + 230, 285, 160, 60, fill=COLOR["Private"])
        data = _preferred(ibm_cloud.get("data"), {"name": "Data TBD"})
        data_node = builder.box(_label(data, "Data"), x + 410, 285, 160, 60, fill=COLOR["Data"])
        builder.edge(ingress_node, compute_node, "app traffic")
        builder.edge(compute_node, data_node, "data access")

        security = _preferred(ibm_cloud.get("security"), {"name": "Security TBD"})
        sec_node = builder.box(_label(security, "Security"), x + 50, 380, 240, 60, fill="#ffe6cc")
        obs = _preferred(ibm_cloud.get("observability"), {"name": "Observability TBD"})
        obs_node = builder.box(_label(obs, "Observability"), x + 310, 380, 240, 60, fill=COLOR["Management"])
        builder.edge(sec_node, compute_node, "secrets")
        builder.edge(compute_node, obs_node, "telemetry")

    # Transit Gateway hub if detected
    if _has_transit_gateway(ibm_cloud):
        tgw = builder.transit_gateway_hub("Transit Gateway", 840, 730)
        for vn in vpc_nodes:
            builder.edge(tgw, vn, "")
    else:
        conn = _preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity TBD"})
        conn_node = builder.box(
            _label(conn, "Connectivity"), 380, 720, 420, 70,
            fill=COLOR["connectivity_fill"], stroke=COLOR["connectivity_stroke"],
        )
        for rn in region_nodes:
            builder.edge(conn_node, rn, "network path")

    # PowerVS workspace if detected
    if _has_powervs(ibm_cloud):
        pw = builder.powervs_workspace("PowerVS Workspace", 1900, 200, 240, 300)
        if vpc_nodes:
            builder.edge(pw, vpc_nodes[0], "cloud connection")


def _render_deployment(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    """Full deployment diagram: IBM Cloud Account → Region → VPC → AZ columns → subnet bands."""
    _render_title(builder, project, "deployment")

    # ---- External lane (left column) ------------------------------------
    ext_lane = builder.box(
        "External / Internet",
        20, ACCOUNT_Y, 200, ACCOUNT_H,
        fill=COLOR["external_fill"], stroke=COLOR["external_stroke"],
        font_style=1, vertical_align="top",
    )
    users_node = builder.box("Users / Clients", 30, ACCOUNT_Y + 80, 180, 60, fill="#ffffff")
    ext_sys_node = builder.box("External Systems", 30, ACCOUNT_Y + 170, 180, 60, fill="#ffffff")

    # ---- IBM Cloud Account boundary ------------------------------------
    cloud = builder.box(
        "IBM Cloud Account",
        ACCOUNT_X + 220, ACCOUNT_Y, ACCOUNT_W - 240, ACCOUNT_H,
        fill=COLOR["account_fill"], stroke=COLOR["account_stroke"],
        font_size=15, font_style=1, vertical_align="top",
    )
    builder.edge(users_node, cloud, "requests")
    builder.edge(ext_sys_node, cloud, "integration")

    # ---- Collect component lists (with fallbacks) ----------------------
    regions_data = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    ingress_items = ibm_cloud.get("ingress") or [{"name": "Ingress TBD", "type": "ingress"}]
    compute_items = ibm_cloud.get("compute") or [{"name": "Compute TBD", "type": "compute"}]
    data_items = ibm_cloud.get("data") or [{"name": "Data TBD", "type": "data"}]
    security_items = ibm_cloud.get("security") or [{"name": "Security TBD", "type": "security"}]
    obs_items = ibm_cloud.get("observability") or [{"name": "Observability TBD", "type": "observability"}]
    private_endpoints = ibm_cloud.get("private_endpoints") or []

    # Map tier → items, using the first item from each category
    tier_items: dict[str, list[dict]] = {
        "Public":     ingress_items[:2],
        "Private":    compute_items[:2],
        "Management": security_items[:1] + obs_items[:1],
        "Data":       data_items[:2],
    }

    # Override with explicit subnet_tier hints
    for category_key in ("ingress", "compute", "data", "security", "observability"):
        for comp in ibm_cloud.get(category_key, []):
            if comp.get("subnet_tier"):
                tier = comp["subnet_tier"]
                if tier in tier_items:
                    if comp not in tier_items[tier]:
                        tier_items[tier].append(comp)

    account_x = ACCOUNT_X + 220
    vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC TBD", "purpose": "Application network"})

    region_nodes: list[str] = []
    vpc_nodes: list[str] = []

    for r_idx, region in enumerate(regions_data[:2]):
        rx = account_x + REGION_MARGIN_X + r_idx * REGION_SPACING
        ry = ACCOUNT_Y + REGION_MARGIN_Y

        region_node = builder.box(
            _label(region, "Region"),
            rx, ry, REGION_W, REGION_H,
            fill=COLOR["region_fill"], stroke=COLOR["region_stroke"],
            font_style=1, vertical_align="top",
        )
        region_nodes.append(region_node)

        vpc_x = rx + VPC_MARGIN_X
        vpc_y = ry + VPC_MARGIN_Y
        vpc_node = builder.box(
            _label(vpc, "VPC"),
            vpc_x, vpc_y, VPC_W, VPC_H,
            fill=COLOR["vpc_fill"], stroke=COLOR["vpc_stroke"],
            font_style=1, vertical_align="top",
        )
        vpc_nodes.append(vpc_node)

        # ---- AZ columns -------------------------------------------------
        for az_idx in range(AZ_COUNT):
            az_label = f"zone-{az_idx + 1}"
            az_x = vpc_x + AZ_SPACING + az_idx * (AZ_W + AZ_SPACING)
            az_y = vpc_y + 40   # below VPC label
            builder.zone_column(az_label, az_x, az_y, AZ_W, AZ_H)

            # ---- Subnet bands inside the AZ ---------------------------
            band_y = az_y + 28  # below zone swimlane header
            band_nodes: dict[str, str] = {}   # tier → band cell_id
            for band_label, band_h in zip(BAND_LABELS, BAND_HEIGHTS):
                band_id = builder.subnet_band(
                    band_label, az_x, band_y, AZ_W, band_h, tier=band_label
                )
                band_nodes[band_label] = band_id
                band_y += band_h

            # ---- Place components in subnet bands (zone-1 only for non-zoned) ---
            if az_idx == 0 or r_idx == 0:
                for tier, items in tier_items.items():
                    if not items:
                        continue
                    band_id = band_nodes.get(tier)
                    if not band_id:
                        continue

                    # Filter items for this specific zone when zone hint is present
                    zone_filtered = [
                        it for it in items
                        if not it.get("zone") or it.get("zone") == az_label
                    ]
                    # If none match zone-1 filter, fall through to show all in zone-1 only
                    if not zone_filtered and az_idx == 0:
                        zone_filtered = items

                    # Only render components in zone-1 (az_idx==0) unless explicitly zoned
                    explicitly_zoned = [it for it in items if it.get("zone") == az_label]
                    to_render = explicitly_zoned if az_idx > 0 else (zone_filtered or items)

                    chip_w = max(60, AZ_W - 2 * BAND_PADDING_X - 4)
                    chip_h = 32
                    # stagger band y from subnet_band header
                    band_top = _band_y_for_tier(az_y, tier)
                    for chip_idx, item in enumerate(to_render[:3]):
                        chip_x = az_x + BAND_PADDING_X
                        cy = band_top + BAND_PADDING_Y + chip_idx * (chip_h + 4)
                        chip_label = item.get("name") or tier
                        builder.box(
                            chip_label,
                            chip_x, cy, chip_w, chip_h,
                            fill=COLOR.get(tier, "#ffffff"),
                            stroke=COLOR["az_stroke"],
                            font_size=9,
                        )

            # ---- VPE gateways in Private band (zone-1 only) -----------
            if az_idx == 0 and private_endpoints:
                priv_band_id = band_nodes.get("Private")
                if priv_band_id:
                    priv_band_top = _band_y_for_tier(az_y, "Private")
                    for ep_idx, ep in enumerate(private_endpoints[:2]):
                        ep_name = ep if isinstance(ep, str) else ep.get("name", "VPE")
                        vpe_x = az_x + BAND_PADDING_X + ep_idx * 90
                        vpe_y = priv_band_top + BAND_PADDING_Y + 70
                        builder.vpe_gateway(ep_name, vpe_x, vpe_y, priv_band_id)

    # ---- Connectivity bar at the bottom --------------------------------
    conn_items = ibm_cloud.get("connectivity") or [{"name": "Connectivity TBD"}]

    if _has_transit_gateway(ibm_cloud):
        tgw_x = account_x + REGION_MARGIN_X + REGION_W // 2 - 80
        tgw_y = ACCOUNT_Y + ACCOUNT_H - 90
        tgw_node = builder.transit_gateway_hub("Transit Gateway", tgw_x, tgw_y)
        for vn in vpc_nodes:
            builder.edge(tgw_node, vn, "")
        # Also connect external
        other_conns = [c for c in conn_items if "transit" not in (c.get("name") or "").lower()]
        if other_conns:
            conn_node = builder.box(
                _label(other_conns[0], "Connectivity"),
                account_x + REGION_MARGIN_X, tgw_y, 240, 50,
                fill=COLOR["connectivity_fill"], stroke=COLOR["connectivity_stroke"],
            )
            builder.edge(conn_node, tgw_node, "")
    else:
        conn_node = builder.box(
            _label(conn_items[0], "Connectivity"),
            account_x + REGION_MARGIN_X, ACCOUNT_Y + ACCOUNT_H - 90, 420, 60,
            fill=COLOR["connectivity_fill"], stroke=COLOR["connectivity_stroke"],
        )
        for rn in region_nodes:
            builder.edge(conn_node, rn, "network path")

    # ---- PowerVS workspace (right of account boundary) ----------------
    if _has_powervs(ibm_cloud):
        pw_x = account_x + ACCOUNT_W - 240 + 20
        pw = builder.powervs_workspace(
            "PowerVS Workspace", pw_x, ACCOUNT_Y + 60, 240, 400
        )
        if vpc_nodes:
            builder.edge(pw, vpc_nodes[0], "cloud connection")


def _band_y_for_tier(az_y: int, tier: str) -> int:
    """Return the absolute y-coordinate of the top of a subnet band inside an AZ."""
    y = az_y + 28  # start below swimlane header
    for band_label, band_h in zip(BAND_LABELS, BAND_HEIGHTS):
        if band_label == tier:
            return y
        y += band_h
    return y  # fallback


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_drawio(architecture: dict, *, diagram_type: str) -> str:
    """Return Draw.io XML for *architecture* of the given *diagram_type*.

    Supported diagram_type values: "context", "logical", "deployment".
    """
    project = architecture.get("project", {})
    ibm_cloud = architecture.get("ibm_cloud", {})
    builder = DrawioBuilder()

    if diagram_type == "deployment":
        _render_deployment(builder, project, ibm_cloud)
    elif diagram_type == "logical":
        _render_logical(builder, project, ibm_cloud)
    else:
        # "context" and any unknown type → safe context diagram
        _render_context(builder, project, ibm_cloud)

    return builder.render()
