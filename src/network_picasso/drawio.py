from __future__ import annotations

from html import escape
from itertools import count
from pathlib import Path

# ---------------------------------------------------------------------------
# IBM Cloud Architecture MD Files — layout conventions loaded at import time
# ---------------------------------------------------------------------------
# These files live in "LLM Architecture MD Files/" and describe the visual
# language, layout rules, and component placement used in IBM Cloud diagrams.
# The renderer references them for layout decisions rather than duplicating
# the guidance inline.

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MD_DIR = _REPO_ROOT / "LLM Architecture MD Files"


def _load_md_guide(filename: str) -> str:
    """Return the text of an LLM Architecture MD file, or '' if missing."""
    p = _MD_DIR / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


# Pre-load at import time — these are small files used to inform conventions.
STYLE_GUIDE      = _load_md_guide("00-style-guide.md")       # visual language
CONTEXT_GUIDE    = _load_md_guide("01-context-diagram.md")   # context layout
LOGICAL_GUIDE    = _load_md_guide("02-logical-architecture.md")  # logical layout
DEPLOYMENT_GUIDE = _load_md_guide("03-deployment-architecture.md")  # deployment layout


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

# Style guide: IBM blue accents, neutral gray containers, left-to-right flow.
# Deployment guide: Account → Region → VPC → AZ columns → subnet bands.
# Logical guide: Left=users/external, Center=app/services, Right=data, Bottom=ops.

ACCOUNT_X = 60
ACCOUNT_Y = 100
ACCOUNT_W = 2100
ACCOUNT_H = 1120

REGION_MARGIN_X = 40
REGION_MARGIN_Y = 70
REGION_W = 980
REGION_H = 960
REGION_SPACING = 1060

VPC_MARGIN_X = 30
VPC_MARGIN_Y = 70
VPC_W = REGION_W - 2 * VPC_MARGIN_X          # 920
VPC_H = REGION_H - VPC_MARGIN_Y - 40         # 850

AZ_COUNT = 3
AZ_SPACING = 10
AZ_W = (VPC_W - (AZ_COUNT + 1) * AZ_SPACING) // AZ_COUNT  # ≈ 290
AZ_H = VPC_H - 70

# Deployment guide: public-facing top, private middle, management/ops below,
# data at the bottom.
BAND_LABELS  = ["Public", "Private", "Management", "Data"]
BAND_HEIGHTS = [140, 210, 140, 140]
BAND_PADDING_X = 10
BAND_PADDING_Y = 32

# ---------------------------------------------------------------------------
# IBM Cloud official color palette
# ---------------------------------------------------------------------------

COLOR = {
    # Structural chrome — IBM Blue 70 accent
    "account_fill":    "#f4f4f4",
    "account_stroke":  "#0f62fe",
    "region_fill":     "#edf5ff",
    "region_stroke":   "#0f62fe",
    "vpc_fill":        "#ffffff",
    "vpc_stroke":      "#4589ff",
    # Availability zone — cool gray
    "az_fill":         "#f4f4f4",
    "az_stroke":       "#8d8d8d",
    # Subnet bands (same palette as IBM Cloud stencil conventions)
    "Public":          "#d0e2ff",   # Blue-10
    "Private":         "#defbe6",   # Green-10
    "Management":      "#fff8e1",   # Yellow-10
    "Data":            "#ede8fe",   # Purple-10
    # External / connectivity
    "external_fill":   "#e5f6ff",
    "external_stroke": "#1192e8",
    "conn_fill":       "#d0e2ff",
    "conn_stroke":     "#0f62fe",
    # PowerVS
    "powervs_fill":    "#f6f2ff",
    "powervs_stroke":  "#7c3e97",
    # Transit Gateway — IBM dark blue
    "tgw_fill":        "#001141",
    "tgw_font":        "#ffffff",
    # Security band icon
    "security_fill":   "#fff1f1",
    "security_stroke": "#da1e28",
    # Icons — IBM stencil default colours
    "icon_fill":       "#0f62fe",
    "icon_font":       "#161616",
    "icon_stroke":     "#0f62fe",
}

# Map component category → subnet tier (deployment guide placement)
TYPE_TO_TIER: dict[str, str] = {
    "ingress":       "Public",
    "compute":       "Private",
    "security":      "Management",
    "observability": "Management",
    "data":          "Data",
}

# Map component category/name tokens → IBM Cloud stencil shape name
# (shape=mxgraph.ibm_cloud.{STENCIL_SHAPE})
STENCIL_MAP: dict[str, str] = {
    # Compute
    "vsi":                      "ibm-cloud--virtual-server-vpc",
    "virtual server":           "ibm-cloud--virtual-server-vpc",
    "openshift":                "logo--openshift",
    "roks":                     "logo--openshift",
    "kubernetes":               "ibm-cloud--kubernetes-service",
    "iks":                      "ibm-cloud--kubernetes-service",
    "bare metal":               "ibm-cloud--bare-metal-servers-vpc",
    "powervs":                  "ibm--power-vs",
    "power virtual server":     "ibm--power-vs",
    "power vs":                 "ibm--power-vs",
    # Connectivity
    "transit gateway":          "ibm-cloud--transit-gateway",
    "direct link":              "ibm-cloud--direct-link-2--connect",
    "vpn":                      "ibm--vpn-for-vpc",
    # Ingress / network
    "internet services":        "ibm-cloud--internet-services",
    "cis":                      "ibm-cloud--internet-services",
    "load balancer":            "load-balancer--application",
    "load-balancer":            "load-balancer--application",
    "public load balancer":     "load-balancer--application",
    "private load balancer":    "load-balancer--vpc",
    # Data / storage
    "object storage":           "object-storage",
    "cos":                      "object-storage",
    "postgresql":               "database--postgresql",
    "mysql":                    "database--mysql",
    "mongodb":                  "database--mongodb",
    "db2":                      "ibm--db2",
    "database":                 "data--base",
    "file storage":             "block-storage",
    "block storage":            "block-storage",
    # Security
    "key protect":              "ibm-cloud--key-protect",
    "hpcs":                     "ibm-cloud--key-protect",
    "secrets manager":          "ibm-cloud--secrets-manager",
    "iam":                      "group--access",
    "scc":                      "ibm-cloud--security-compliance-center",
    # Observability
    "monitoring":               "cloud--monitoring",
    "log analysis":             "ibm-cloud--logging",
    "logging":                  "ibm-cloud--logging",
    "activity tracker":         "ibm-cloud--security-compliance-center",
    "flow log":                 "flow-logs-vpc",
    # Endpoints
    "vpe":                      "ibm-cloud--vpc-endpoints",
    "private endpoint":         "ibm-cloud--vpc-endpoints",
    # Container
    "vpc":                      "ibm-cloud--vpc",
    "subnet":                   "ibm-cloud--subnets",
    # Generic
    "user":                     "user",
    "external":                 "enterprise",
}


def _stencil_shape(name: str) -> str:
    """Return the IBM stencil shape name for a component name string."""
    lower = name.lower()
    for token, shape in STENCIL_MAP.items():
        if token in lower:
            return shape
    return ""


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

    def _next_id(self) -> str:
        return f"n{next(self._ids)}"

    def ibm_service(
        self,
        value: str,
        x: int,
        y: int,
        width: int = 48,
        height: int = 48,
        *,
        shape: str = "",
        fill: str = "",
        stroke: str = "",
        font_size: int = 10,
    ) -> str:
        """Render an IBM stencil icon cell.

        Uses shape=mxgraph.ibm_cloud.{shape} when a shape is provided,
        falling back to a rounded rectangle with IBM color conventions.
        """
        cell_id = self._next_id()
        if shape:
            style = (
                f"shape=mxgraph.ibm_cloud.{shape};"
                f"fillColor={fill or COLOR['icon_fill']};"
                f"strokeColor={stroke or COLOR['icon_stroke']};"
                f"fontColor={COLOR['icon_font']};"
                f"fontSize={font_size};align=center;html=1;"
                "sketch=0;aspect=fixed;"
            )
        else:
            style = (
                "rounded=1;whiteSpace=wrap;html=1;"
                f"fillColor={fill or '#ffffff'};"
                f"strokeColor={stroke or COLOR['icon_stroke']};"
                f"fontColor={COLOR['icon_font']};"
                f"fontSize={font_size};align=center;verticalAlign=middle;"
            )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def container(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: str = "#f4f4f4",
        stroke: str = "#8d8d8d",
        font_size: int = 12,
        font_style: int = 1,
        dashed: bool = False,
        vertical_align: str = "top",
        shape: str = "",
    ) -> str:
        """Render a container / boundary box (region, VPC, AZ, etc.)."""
        cell_id = self._next_id()
        if shape:
            style = (
                f"shape=mxgraph.ibm_cloud.{shape};"
                f"fillColor={fill};strokeColor={stroke};"
                f"fontSize={font_size};fontStyle={font_style};"
                f"verticalAlign={vertical_align};align=left;html=1;whiteSpace=wrap;"
                "swimlane=0;sketch=0;"
            )
        else:
            style = (
                "rounded=0;whiteSpace=wrap;html=1;"
                f"fillColor={fill};strokeColor={stroke};"
                f"fontSize={font_size};fontStyle={font_style};"
                f"verticalAlign={vertical_align};align=left;"
            )
        if dashed:
            style += "dashed=1;dashPattern=8 4;"
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def box(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: str = "#ffffff",
        stroke: str = "#4589ff",
        font_size: int = 11,
        font_style: int = 0,
        dashed: bool = False,
        align: str = "center",
        vertical_align: str = "middle",
    ) -> str:
        """Generic rounded rectangle (used for fallback nodes)."""
        cell_id = self._next_id()
        style = (
            "rounded=1;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};"
            f"fontSize={font_size};fontStyle={font_style};"
            f"align={align};verticalAlign={vertical_align};"
        )
        if dashed:
            style += "dashed=1;"
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(value)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def edge(self, source: str, target: str, label: str = "", *, dashed: bool = False) -> None:
        """Labeled orthogonal edge between two nodes."""
        cell_id = f"e{next(self._ids)}"
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
            "jettySize=auto;html=1;fontSize=10;endArrow=block;endFill=1;"
            "strokeColor=#4589ff;"
        )
        if dashed:
            style += "dashed=1;endArrow=open;endFill=0;"
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" edge="1" '
            f'source="{source}" target="{target}" parent="1">'
            '<mxGeometry relative="1" as="geometry" />'
            "</mxCell>"
        )

    # ------------------------------------------------------------------
    # IBM-specific topology helpers
    # ------------------------------------------------------------------

    def zone_column(self, label: str, x: int, y: int, w: int, h: int) -> str:
        """Availability zone boundary — gray swimlane."""
        cell_id = self._next_id()
        style = (
            "swimlane;startSize=26;"
            f"fillColor={COLOR['az_fill']};strokeColor={COLOR['az_stroke']};"
            "fontStyle=1;fontSize=11;align=center;horizontal=1;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def subnet_band(self, label: str, x: int, y: int, w: int, h: int, tier: str) -> str:
        """Colored subnet tier band inside an AZ."""
        fill = COLOR.get(tier, "#ffffff")
        cell_id = self._next_id()
        style = (
            f"fillColor={fill};strokeColor={COLOR['az_stroke']};"
            "rounded=0;whiteSpace=wrap;html=1;"
            "fontStyle=1;fontSize=10;align=left;verticalAlign=top;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def transit_gateway(self, label: str, x: int, y: int) -> str:
        """IBM Transit Gateway node using the IBM stencil shape."""
        cell_id = self._next_id()
        style = (
            "shape=mxgraph.ibm_cloud.ibm-cloud--transit-gateway;"
            f"fillColor={COLOR['tgw_fill']};strokeColor={COLOR['tgw_fill']};"
            f"fontColor={COLOR['tgw_font']};"
            "fontSize=11;fontStyle=1;align=center;html=1;sketch=0;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="180" height="60" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def powervs_workspace(self, label: str, x: int, y: int, w: int, h: int) -> str:
        """PowerVS workspace boundary — purple dashed."""
        cell_id = self._next_id()
        style = (
            "shape=mxgraph.ibm_cloud.ibm--power-vs;"
            f"fillColor={COLOR['powervs_fill']};strokeColor={COLOR['powervs_stroke']};"
            "fontSize=12;fontStyle=1;verticalAlign=top;align=left;html=1;"
            "dashed=1;dashPattern=8 4;whiteSpace=wrap;sketch=0;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def vpe_gateway(self, label: str, x: int, y: int, parent_id: str) -> str:
        """VPE gateway icon + dotted edge to its parent service."""
        cell_id = self._next_id()
        style = (
            "shape=mxgraph.ibm_cloud.ibm-cloud--vpc-endpoints;"
            f"fillColor={COLOR['Private']};strokeColor={COLOR['vpc_stroke']};"
            "fontSize=9;align=center;html=1;sketch=0;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="80" height="50" as="geometry" />'
            "</mxCell>"
        )
        self.edge(cell_id, parent_id, dashed=True)
        return cell_id

    def render(self) -> str:
        body = "\n    ".join(self.cells)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile>\n'
            '  <diagram name="IBM Cloud Architecture">\n'
            '    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            'pageScale="1" pageWidth="2400" pageHeight="1600" math="0" shadow="0">\n'
            "      <root>\n"
            f"        {body}\n"
            "      </root>\n"
            "    </mxGraphModel>\n"
            "  </diagram>\n"
            "</mxfile>\n"
        )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _label(item: dict, fallback: str) -> str:
    name = item.get("name") or fallback
    purpose = item.get("purpose")
    if purpose and purpose != name:
        return f"{name}\n{purpose}"
    return name


def _preferred(items: list[dict] | None, fallback: dict) -> dict:
    """Return the most informative item from a list (has purpose > has region > longer name)."""
    if not items:
        return fallback
    return sorted(
        items,
        key=lambda it: (
            0 if it.get("purpose") else 1,
            0 if it.get("region") else 1,
            -len(it.get("name", "")),
        ),
    )[0]


def _has_powervs(ibm_cloud: dict) -> bool:
    for comp in ibm_cloud.get("compute", []):
        name = (comp.get("name") or "").lower()
        if "power" in name or "powervs" in name:
            return True
    return False


def _has_transit_gateway(ibm_cloud: dict) -> bool:
    for conn in ibm_cloud.get("connectivity", []):
        if "transit" in (conn.get("name") or "").lower():
            return True
    return False


def _service_node(
    builder: DrawioBuilder,
    item: dict,
    fallback_name: str,
    x: int,
    y: int,
    w: int = 160,
    h: int = 52,
    *,
    tier: str = "",
) -> str:
    """Render a component as an IBM stencil icon + label box.

    Uses the IBM stencil shape when one can be matched, falls back to a
    colored rounded rectangle if not.
    """
    name = item.get("name") or fallback_name
    shape = _stencil_shape(name)
    fill = COLOR.get(tier, "#ffffff") if tier else "#ffffff"

    # Render icon (left-aligned) + text label
    if shape:
        icon_id = builder.ibm_service(
            name, x, y, w, h,
            shape=shape, fill=fill,
            font_size=10,
        )
        return icon_id
    else:
        return builder.box(
            name, x, y, w, h,
            fill=fill, stroke=COLOR["icon_stroke"],
            font_size=10,
        )


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

def _render_title(builder: DrawioBuilder, project: dict, diagram_type: str) -> None:
    title = project.get("name", "IBM Cloud Architecture")
    env = project.get("environment", "")
    label = f"{title}  —  {diagram_type.title()} Architecture"
    if env and env != "TBD":
        label += f"  [{env}]"
    builder.box(
        label,
        ACCOUNT_X, 20, 1920, 65,
        fill="#ffffff", stroke="#ffffff",
        font_size=20, font_style=1, align="left",
    )


# ---------------------------------------------------------------------------
# Context diagram
# ---------------------------------------------------------------------------
# Layout from 01-context-diagram.md:
#   Users / client apps on the left.
#   External systems outside the IBM Cloud boundary.
#   IBM Cloud boundary in the center.
#   Major IBM Cloud services grouped by function.
#   High-level data or request flows.
#   Security boundary and identity/authentication.
#   Optional operations/monitoring block at the bottom.

def _render_context(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    _render_title(builder, project, "context")

    # ── External lane (left) ─────────────────────────────────────────────
    ext_lane = builder.container(
        "External Users & Systems", 20, ACCOUNT_Y, 220, 460,
        fill=COLOR["external_fill"], stroke=COLOR["external_stroke"],
        font_size=12,
    )
    users_node = builder.ibm_service(
        "Users / Clients", 50, ACCOUNT_Y + 80, 160, 60,
        shape="user", fill=COLOR["external_fill"],
    )
    ext_sys_node = builder.ibm_service(
        "External Systems", 50, ACCOUNT_Y + 180, 160, 60,
        shape="enterprise", fill=COLOR["external_fill"],
    )

    # ── IBM Cloud Account boundary ───────────────────────────────────────
    cloud = builder.container(
        "IBM Cloud Account", 280, ACCOUNT_Y, 1720, 740,
        fill=COLOR["account_fill"], stroke=COLOR["account_stroke"],
        font_size=14,
    )
    builder.edge(users_node, cloud, "HTTPS requests")
    builder.edge(ext_sys_node, cloud, "API integration")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    region_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 820
        rn = builder.container(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 760, 540,
            fill=COLOR["region_fill"], stroke=COLOR["region_stroke"],
            font_size=13,
        )
        region_nodes.append(rn)

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC", "purpose": "Application network"})
        vpc_node = builder.container(
            _label(vpc, "VPC"), rx + 30, ACCOUNT_Y + 130, 700, 370,
            fill=COLOR["vpc_fill"], stroke=COLOR["vpc_stroke"],
            font_size=12,
        )

        # Ingress → Compute → Data (left-to-right, style guide)
        ingress = _preferred(ibm_cloud.get("ingress"), {"name": "Ingress"})
        ingress_node = _service_node(builder, ingress, "Ingress", rx + 50, ACCOUNT_Y + 195, 180, 60, tier="Public")

        compute = _preferred(ibm_cloud.get("compute"), {"name": "Compute"})
        compute_node = _service_node(builder, compute, "Compute", rx + 265, ACCOUNT_Y + 195, 180, 60, tier="Private")

        data = _preferred(ibm_cloud.get("data"), {"name": "Data Services"})
        data_node = _service_node(builder, data, "Data", rx + 480, ACCOUNT_Y + 195, 180, 60, tier="Data")

        builder.edge(ingress_node, compute_node, "app traffic")
        builder.edge(compute_node, data_node, "data access")

        # Security + Observability (bottom of VPC, style guide)
        security = _preferred(ibm_cloud.get("security"), {"name": "IAM / Secrets / Keys"})
        sec_node = _service_node(builder, security, "Security", rx + 50, ACCOUNT_Y + 310, 200, 60, tier="Management")

        obs = _preferred(ibm_cloud.get("observability"), {"name": "Monitoring / Logging"})
        obs_node = _service_node(builder, obs, "Observability", rx + 280, ACCOUNT_Y + 310, 200, 60, tier="Management")

        builder.edge(sec_node, compute_node, "identity & secrets")
        builder.edge(compute_node, obs_node, "telemetry")

    # ── Connectivity bar (bottom, style guide) ───────────────────────────
    conn = _preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity"})
    conn_name = conn.get("name") or "Connectivity"
    conn_shape = _stencil_shape(conn_name)
    conn_node = builder.ibm_service(
        conn_name, 300, ACCOUNT_Y + 640, 260, 60,
        shape=conn_shape, fill=COLOR["conn_fill"], stroke=COLOR["conn_stroke"],
    )
    for rn in region_nodes:
        builder.edge(conn_node, rn, "")

    # ── Security boundary (bottom-right) ─────────────────────────────────
    if ibm_cloud.get("security"):
        builder.container(
            "Security & Compliance", 600, ACCOUNT_Y + 640, 400, 60,
            fill=COLOR["security_fill"], stroke=COLOR["security_stroke"],
            font_size=11,
        )


# ---------------------------------------------------------------------------
# Logical diagram
# ---------------------------------------------------------------------------
# Layout from 02-logical-architecture.md:
#   Left: users, apps, external systems
#   Center: IBM Cloud application/services layer
#   Right: data stores, AI services, external integrations
#   Bottom: logging, monitoring, backup, CI/CD, security controls
#   Labeled arrows for key flows.

def _render_logical(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    _render_title(builder, project, "logical")

    # ── Left: external ───────────────────────────────────────────────────
    ext_lane = builder.container(
        "External Users & Systems", 20, ACCOUNT_Y, 220, 560,
        fill=COLOR["external_fill"], stroke=COLOR["external_stroke"],
    )
    users_node = builder.ibm_service(
        "Users / Clients", 50, ACCOUNT_Y + 80, 160, 60, shape="user",
        fill=COLOR["external_fill"],
    )
    ext_sys_node = builder.ibm_service(
        "External Systems", 50, ACCOUNT_Y + 190, 160, 60, shape="enterprise",
        fill=COLOR["external_fill"],
    )

    # ── Center: IBM Cloud ────────────────────────────────────────────────
    cloud = builder.container(
        "IBM Cloud Account", 280, ACCOUNT_Y, 1280, 740,
        fill=COLOR["account_fill"], stroke=COLOR["account_stroke"],
        font_size=14,
    )
    builder.edge(users_node, cloud, "HTTPS")
    builder.edge(ext_sys_node, cloud, "API")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    vpc_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 600
        rn = builder.container(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 560, 540,
            fill=COLOR["region_fill"], stroke=COLOR["region_stroke"],
        )

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC"})
        vpc_node = builder.container(
            _label(vpc, "VPC"), rx + 20, ACCOUNT_Y + 120, 520, 380,
            fill=COLOR["vpc_fill"], stroke=COLOR["vpc_stroke"],
        )
        vpc_nodes.append(vpc_node)

        # Ingress layer
        ingress = _preferred(ibm_cloud.get("ingress"), {"name": "Ingress"})
        in_node = _service_node(builder, ingress, "Ingress", rx + 30, ACCOUNT_Y + 180, 160, 55, tier="Public")

        # Compute layer
        compute = _preferred(ibm_cloud.get("compute"), {"name": "Compute"})
        comp_node = _service_node(builder, compute, "Compute", rx + 200, ACCOUNT_Y + 180, 160, 55, tier="Private")

        builder.edge(in_node, comp_node, "app traffic")

        # Security + IAM
        security = _preferred(ibm_cloud.get("security"), {"name": "Security"})
        sec_node = _service_node(builder, security, "Security", rx + 30, ACCOUNT_Y + 310, 160, 55, tier="Management")
        builder.edge(sec_node, comp_node, "auth & secrets")

        # Observability
        obs = _preferred(ibm_cloud.get("observability"), {"name": "Observability"})
        obs_node = _service_node(builder, obs, "Observability", rx + 200, ACCOUNT_Y + 310, 160, 55, tier="Management")
        builder.edge(comp_node, obs_node, "telemetry")

    # ── Right: data stores (02-logical-architecture.md: right side) ──────
    data_lane = builder.container(
        "Data & Storage", 1600, ACCOUNT_Y + 60, 320, 500,
        fill=COLOR["Data"], stroke=COLOR["az_stroke"],
    )
    data_items = ibm_cloud.get("data") or [{"name": "Data Services"}]
    for di, ditem in enumerate(data_items[:4]):
        dn = _service_node(
            builder, ditem, "Data", 1620, ACCOUNT_Y + 130 + di * 90, 280, 55, tier="Data",
        )
        if vpc_nodes:
            builder.edge(vpc_nodes[0], dn, "private data access")

    # ── Transit Gateway (if present) ─────────────────────────────────────
    if _has_transit_gateway(ibm_cloud):
        tgw = builder.transit_gateway("Transit Gateway", 840, ACCOUNT_Y + 760)
        for vn in vpc_nodes:
            builder.edge(tgw, vn, "")
    else:
        conn = _preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity"})
        conn_node = _service_node(
            builder, conn, "Connectivity", 320, ACCOUNT_Y + 760, 300, 55,
        )
        for rn_id in vpc_nodes:
            builder.edge(conn_node, rn_id, "network")

    # ── PowerVS (if present) ─────────────────────────────────────────────
    if _has_powervs(ibm_cloud):
        pw = builder.powervs_workspace("PowerVS Workspace", 1980, ACCOUNT_Y + 100, 260, 340)
        if vpc_nodes:
            builder.edge(pw, vpc_nodes[0], "cloud connection")

    # ── Bottom: backup/DR (02-logical-architecture.md: bottom layer) ─────
    backup = ibm_cloud.get("backup_dr")
    if backup:
        bitem = _preferred(backup, {"name": "Backup / DR"})
        builder.ibm_service(
            bitem.get("name") or "Backup / DR",
            320, ACCOUNT_Y + 840, 280, 55,
            shape="ibm-cloud--continuous-delivery",
            fill="#f4f4f4",
        )


# ---------------------------------------------------------------------------
# Deployment diagram
# ---------------------------------------------------------------------------
# Layout from 03-deployment-architecture.md:
#   Account → Region → VPC → AZ columns → subnet bands
#   Public-facing components near the top.
#   Private services inside private subnet/container boundaries.
#   Operations components along the bottom.
#   Label every important network/data flow.

def _render_deployment(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:
    _render_title(builder, project, "deployment")

    # ── External lane (left) ─────────────────────────────────────────────
    builder.container(
        "External / Internet", 20, ACCOUNT_Y, 200, ACCOUNT_H,
        fill=COLOR["external_fill"], stroke=COLOR["external_stroke"],
    )
    users_node = builder.ibm_service(
        "Users / Clients", 30, ACCOUNT_Y + 80, 180, 60, shape="user",
        fill=COLOR["external_fill"],
    )
    ext_sys_node = builder.ibm_service(
        "External Systems", 30, ACCOUNT_Y + 200, 180, 60, shape="enterprise",
        fill=COLOR["external_fill"],
    )

    # ── IBM Cloud Account boundary ───────────────────────────────────────
    cloud = builder.container(
        "IBM Cloud Account",
        ACCOUNT_X + 220, ACCOUNT_Y, ACCOUNT_W - 220, ACCOUNT_H,
        fill=COLOR["account_fill"], stroke=COLOR["account_stroke"],
        font_size=14,
    )
    builder.edge(users_node, cloud, "HTTPS")
    builder.edge(ext_sys_node, cloud, "API integration")

    regions_data = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    ingress_items  = ibm_cloud.get("ingress")         or [{"name": "Ingress TBD",   "type": "ingress"}]
    compute_items  = ibm_cloud.get("compute")         or [{"name": "Compute TBD",   "type": "compute"}]
    data_items     = ibm_cloud.get("data")            or [{"name": "Data TBD",      "type": "data"}]
    security_items = ibm_cloud.get("security")        or [{"name": "Security TBD",  "type": "security"}]
    obs_items      = ibm_cloud.get("observability")   or [{"name": "Observability TBD", "type": "observability"}]
    private_eps    = ibm_cloud.get("private_endpoints") or []

    # Tier → items mapping (deployment guide: public top, private middle, ops/data bottom)
    tier_items: dict[str, list[dict]] = {
        "Public":     ingress_items[:2],
        "Private":    compute_items[:2],
        "Management": security_items[:1] + obs_items[:1],
        "Data":       data_items[:2],
    }

    # Override with explicit subnet_tier hints from extracted model
    for cat in ("ingress", "compute", "data", "security", "observability"):
        for comp in ibm_cloud.get(cat, []):
            tier = comp.get("subnet_tier")
            if tier and tier in tier_items and comp not in tier_items[tier]:
                tier_items[tier].append(comp)

    account_left = ACCOUNT_X + 220
    vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC"})

    region_nodes: list[str] = []
    vpc_nodes: list[str] = []
    first_comp_node: str | None = None

    for r_idx, region in enumerate(regions_data[:2]):
        rx = account_left + REGION_MARGIN_X + r_idx * REGION_SPACING
        ry = ACCOUNT_Y + REGION_MARGIN_Y

        region_node = builder.container(
            _label(region, "Region"), rx, ry, REGION_W, REGION_H,
            fill=COLOR["region_fill"], stroke=COLOR["region_stroke"],
            font_size=13,
        )
        region_nodes.append(region_node)

        vpc_x = rx + VPC_MARGIN_X
        vpc_y = ry + VPC_MARGIN_Y
        vpc_node = builder.container(
            _label(vpc, "VPC"), vpc_x, vpc_y, VPC_W, VPC_H,
            fill=COLOR["vpc_fill"], stroke=COLOR["vpc_stroke"],
            font_size=12,
        )
        vpc_nodes.append(vpc_node)

        # ── AZ columns ─────────────────────────────────────────────────
        for az_idx in range(AZ_COUNT):
            az_label = f"zone-{az_idx + 1}"
            az_x = vpc_x + AZ_SPACING + az_idx * (AZ_W + AZ_SPACING)
            az_y = vpc_y + 50
            builder.zone_column(az_label, az_x, az_y, AZ_W, AZ_H)

            # ── Subnet bands ─────────────────────────────────────────
            band_y = az_y + 30
            band_nodes: dict[str, str] = {}
            for band_label, band_h in zip(BAND_LABELS, BAND_HEIGHTS):
                bid = builder.subnet_band(band_label, az_x, band_y, AZ_W, band_h, tier=band_label)
                band_nodes[band_label] = bid
                band_y += band_h

            # ── Service nodes inside bands ────────────────────────────
            # Deployment guide: only zone-1 shows all; other zones mirror
            # what is explicitly zone-tagged.
            if az_idx == 0 or r_idx == 0:
                for tier, items in tier_items.items():
                    if not items:
                        continue
                    band_top = _band_y_for_tier(az_y, tier)
                    explicitly_zoned = [it for it in items if it.get("zone") == az_label]
                    to_render = explicitly_zoned if az_idx > 0 else (items[:2])

                    chip_w = AZ_W - 2 * BAND_PADDING_X - 4
                    chip_h = 38
                    for ci, item in enumerate(to_render[:2]):
                        cx = az_x + BAND_PADDING_X
                        cy = band_top + BAND_PADDING_Y + ci * (chip_h + 4)
                        name = item.get("name") or tier
                        shape = _stencil_shape(name)
                        nid = builder.ibm_service(
                            name, cx, cy, chip_w, chip_h,
                            shape=shape,
                            fill=COLOR.get(tier, "#ffffff"),
                            font_size=9,
                        )
                        # Track first compute node for connectivity edges
                        if tier == "Private" and first_comp_node is None:
                            first_comp_node = nid

            # ── VPE gateways in Private band (zone-1 only) ─────────
            if az_idx == 0 and private_eps:
                priv_top = _band_y_for_tier(az_y, "Private")
                for ep_idx, ep in enumerate(private_eps[:2]):
                    ep_name = ep if isinstance(ep, str) else ep.get("name", "VPE")
                    vpe_x = az_x + BAND_PADDING_X + ep_idx * 90
                    vpe_y = priv_top + BAND_PADDING_Y + 90
                    priv_band = band_nodes.get("Private")
                    if priv_band:
                        builder.vpe_gateway(ep_name, vpe_x, vpe_y, priv_band)

    # ── Connectivity bar (bottom, deployment guide: operations at the bottom) ──
    conn_items = ibm_cloud.get("connectivity") or [{"name": "Connectivity TBD"}]

    if _has_transit_gateway(ibm_cloud):
        tgw_x = account_left + REGION_MARGIN_X + REGION_W // 2 - 90
        tgw_y = ACCOUNT_Y + ACCOUNT_H - 100
        tgw_node = builder.transit_gateway("Transit Gateway", tgw_x, tgw_y)
        for vn in vpc_nodes:
            builder.edge(tgw_node, vn, "")
        # Direct Link / VPN alongside TGW
        other = [c for c in conn_items if "transit" not in (c.get("name") or "").lower()]
        if other:
            dl = other[0]
            dl_shape = _stencil_shape(dl.get("name") or "")
            dl_node = builder.ibm_service(
                dl.get("name") or "Direct Link",
                account_left + REGION_MARGIN_X, tgw_y, 220, 55,
                shape=dl_shape, fill=COLOR["conn_fill"], stroke=COLOR["conn_stroke"],
            )
            builder.edge(dl_node, tgw_node, "")
    else:
        conn = _preferred(conn_items, {"name": "Connectivity TBD"})
        cn = _service_node(
            builder, conn, "Connectivity",
            account_left + REGION_MARGIN_X, ACCOUNT_Y + ACCOUNT_H - 100, 280, 55,
        )
        for rn in region_nodes:
            builder.edge(cn, rn, "network path")

    # ── PowerVS workspace ──────────────────────────────────────────────
    if _has_powervs(ibm_cloud):
        pw_x = account_left + ACCOUNT_W - 200
        pw = builder.powervs_workspace("PowerVS Workspace", pw_x, ACCOUNT_Y + 80, 260, 400)
        if vpc_nodes:
            builder.edge(pw, vpc_nodes[0], "cloud connection")


def _band_y_for_tier(az_y: int, tier: str) -> int:
    y = az_y + 30
    for band_label, band_h in zip(BAND_LABELS, BAND_HEIGHTS):
        if band_label == tier:
            return y
        y += band_h
    return y


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_drawio(architecture: dict, *, diagram_type: str) -> str:
    """Return Draw.io XML for *architecture* using IBM Cloud stencil shapes.

    Layout conventions are derived from the LLM Architecture MD Files:
      - 00-style-guide.md     → IBM visual language, color palette
      - 01-context-diagram.md → context diagram layout
      - 02-logical-architecture.md → logical diagram layout
      - 03-deployment-architecture.md → deployment diagram layout

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
        _render_context(builder, project, ibm_cloud)

    return builder.render()
