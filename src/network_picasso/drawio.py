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

# ---------------------------------------------------------------------------
# IBM Cloud canonical color palette — sourced directly from Sidebar-IBMCloud.js
# ---------------------------------------------------------------------------
# IBM's prescribed node pattern:
#   bg  = colored square  (shape=rect;fillColor=<CAT_COLOR>;strokeColor=none)
#   icon = white stencil  (shape=mxgraph.ibm_cloud.X;fillColor=#ffffff;strokeColor=none)
#
# IBM's prescribed location (container) pattern:
#   outer box             (container=1;strokeColor=<CAT_COLOR>;fillColor=none;strokeWidth=1)
#   left border strip     (shape=rect;fillColor=<CAT_COLOR>;width=4)
#   icon child            (shape=mxgraph.ibm_cloud.X;fillColor=<CAT_COLOR>)
# ---------------------------------------------------------------------------

COLOR = {
    # ── IBM canonical category colors (from Sidebar-IBMCloud.js) ──────────
    "network":         "#1192E8",   # Network, Connectivity, VPC, Subnet
    "compute":         "#198038",   # VSI, Bare Metal, ROKS, Kubernetes
    "security":        "#FA4D56",   # VPN, Bastion, Auth Boundary, Sec Groups
    "data":            "#0F62FE",   # Databases, Object Storage, Data
    "ai":              "#A56EFF",   # Watson, watsonx, Applications
    "actor":           "#000000",   # User, Enterprise (actors)
    "observability":   "#1192E8",   # Monitoring, Logging, Flow Logs
    "grey":            "#878D96",   # Region, AZ, Generic group
    # ── Structural containers ──────────────────────────────────────────────
    "account_fill":    "none",
    "account_stroke":  "#1192E8",
    "account_sw":      2,
    "region_fill":     "none",
    "region_stroke":   "#878D96",
    "region_sw":       1,
    "vpc_fill":        "none",
    "vpc_stroke":      "#1192E8",
    "vpc_sw":          1,
    "az_fill":         "none",
    "az_stroke":       "#878D96",
    "az_sw":           1,
    # ── Subnet band fills (light tints, NOT the category colors) ──────────
    "Public":          "#D0E2FF",   # Blue-10
    "Private":         "#D9F7BE",   # Green-10 (approx)
    "Management":      "#FFF1F1",   # Red-10
    "Data":            "#EDE8FE",   # Purple-10
    # ── External / connectivity containers ────────────────────────────────
    "external_fill":   "none",
    "external_stroke": "#878D96",
    "conn_stroke":     "#1192E8",
    # ── PowerVS ───────────────────────────────────────────────────────────
    "powervs_fill":    "none",
    "powervs_stroke":  "#1192E8",
    # ── Icon text ─────────────────────────────────────────────────────────
    "icon_font":       "#161616",
    "icon_font_white": "#ffffff",
}

# Map component category → subnet tier (deployment guide placement)
TYPE_TO_TIER: dict[str, str] = {
    "ingress":       "Public",
    "compute":       "Private",
    "security":      "Management",
    "observability": "Management",
    "data":          "Data",
}

# ── IBM canonical node color per stencil category ─────────────────────────
# Sourced from Sidebar-IBMCloud.js bgFillColor parameter per palette function.
STENCIL_COLOR: dict[str, str] = {
    # Compute — green
    "ibm-cloud--virtual-server-vpc":        "#198038",
    "ibm-cloud--virtual-server-classic":    "#198038",
    "ibm-cloud--bare-metal-servers-vpc":    "#198038",
    "ibm-cloud--bare-metal-server":         "#198038",
    "ibm-cloud--dedicated-host":            "#198038",
    "ibm-cloud--kubernetes-service":        "#198038",
    "logo--openshift":                      "#198038",
    "ibm-z-os--containers":                 "#198038",
    "cloud-registry":                       "#198038",
    "cloud-satellite":                      "#198038",
    "image-service":                        "#198038",
    "ibm--power-vs":                        "#198038",
    # Network / connectivity — cyan-blue
    "ibm-cloud--transit-gateway":           "#1192E8",
    "ibm-cloud--direct-link-2--connect":    "#1192E8",
    "ibm-cloud--direct-link-2--dedicated":  "#1192E8",
    "ibm-cloud--internet-services":         "#1192E8",
    "ibm-cloud--vpc-endpoints":             "#1192E8",
    "ibm-cloud--vpc":                       "#1192E8",
    "ibm-cloud--subnets":                   "#1192E8",
    "load-balancer--vpc":                   "#1192E8",
    "load-balancer--application":           "#1192E8",
    "load-balancer--network":               "#1192E8",
    "load-balancer--global":                "#1192E8",
    "load-balancer--classic":               "#1192E8",
    "floating-ip":                          "#1192E8",
    "gateway--public":                      "#1192E8",
    "dns-services":                         "#1192E8",
    "network-interface":                    "#1192E8",
    "network--public":                      "#1192E8",
    "network--enterprise":                  "#1192E8",
    "wikis":                                "#1192E8",
    "point-of-presence":                    "#878D96",
    "location":                             "#878D96",
    "data--center":                         "#878D96",
    "arrows--horizontal":                   "#1192E8",
    # Security / VPN — red
    "ibm--vpn-for-vpc":                     "#FA4D56",
    "vpn--connection":                      "#FA4D56",
    "bastion-host":                         "#FA4D56",
    "ibm-cloud--key-protect":               "#FA4D56",
    "ibm-cloud--secrets-manager":           "#FA4D56",
    "ibm-cloud--security-compliance-center":"#FA4D56",
    "group--security":                      "#FA4D56",
    "group--access":                        "#FA4D56",
    "group--resource":                      "#FA4D56",
    "group--account":                       "#FA4D56",
    "subnet-acl-rules":                     "#FA4D56",
    "password-icon":                        "#FA4D56",  # IBM stencil shape name
    # Data / storage — blue
    "object-storage":                       "#0F62FE",
    "block-storage":                        "#0F62FE",
    "data--base":                           "#0F62FE",
    "ibm--db2":                             "#0F62FE",
    "ibm--db2-warehouse":                   "#0F62FE",
    "ibm--cloudant":                        "#0F62FE",
    "ibm--mq":                              "#0F62FE",
    "database--postgresql":                 "#0F62FE",
    "database--mysql":                      "#0F62FE",
    "database--mongodb":                    "#0F62FE",
    "database--redis":                      "#0F62FE",
    "database--rabbit":                     "#0F62FE",
    "database--elastic":                    "#0F62FE",
    "database--etcd":                       "#0F62FE",
    "database--datastax":                   "#0F62FE",
    "database--enterprisedb":               "#0F62FE",
    # Observability — cyan-blue
    "cloud--monitoring":                    "#1192E8",
    "ibm-cloud--logging":                   "#1192E8",
    "flow-logs-vpc":                        "#1192E8",
    # AI / Apps — purple
    "application":                          "#A56EFF",
    "application--web":                     "#A56EFF",
    # Actors — black
    "user":                                 "#000000",
    "enterprise":                           "#000000",
    "group":                                "#000000",
}

# Map component name tokens → IBM Cloud stencil shape name.
# Keys are lowercase substrings matched against the component name.
# Order matters — more specific matches first.
STENCIL_MAP: dict[str, str] = {
    # Compute
    "power virtual server":     "ibm--power-vs",
    "powervs":                  "ibm--power-vs",
    "power vs":                 "ibm--power-vs",
    "openshift":                "logo--openshift",
    "roks":                     "logo--openshift",
    "kubernetes":               "ibm-cloud--kubernetes-service",
    "iks":                      "ibm-cloud--kubernetes-service",
    "bare metal":               "ibm-cloud--bare-metal-servers-vpc",
    "vsi":                      "ibm-cloud--virtual-server-vpc",
    "virtual server":           "ibm-cloud--virtual-server-vpc",
    "dedicated host":           "ibm-cloud--dedicated-host",
    # Connectivity
    "transit gateway":          "ibm-cloud--transit-gateway",
    "direct link dedicated":    "ibm-cloud--direct-link-2--dedicated",
    "direct link":              "ibm-cloud--direct-link-2--connect",
    "vpn gateway":              "ibm--vpn-for-vpc",
    "vpn connection":           "vpn--connection",
    "vpn":                      "ibm--vpn-for-vpc",
    "bastion":                  "bastion-host",
    "floating ip":              "floating-ip",
    "public gateway":           "gateway--public",
    # Ingress / network
    "internet services":        "ibm-cloud--internet-services",
    "cis":                      "ibm-cloud--internet-services",
    "application load balancer":"load-balancer--application",
    "private load balancer":    "load-balancer--vpc",
    "network load balancer":    "load-balancer--network",
    "global load balancer":     "load-balancer--global",
    "load balancer":            "load-balancer--application",
    "load-balancer":            "load-balancer--application",
    "dns":                      "dns-services",
    "internet":                 "wikis",
    # Data / storage
    "object storage":           "object-storage",
    "cos":                      "object-storage",
    "postgresql":               "database--postgresql",
    "mysql":                    "database--mysql",
    "mongodb":                  "database--mongodb",
    "redis":                    "database--redis",
    "db2":                      "ibm--db2",
    "cloudant":                 "ibm--cloudant",
    "mq":                       "ibm--mq",
    "database":                 "data--base",
    "file storage":             "block-storage",
    "block storage":            "block-storage",
    # Security
    "key protect":              "ibm-cloud--key-protect",
    "hpcs":                     "ibm-cloud--key-protect",
    "hyper protect":            "ibm-cloud--key-protect",
    "secrets manager":          "ibm-cloud--secrets-manager",
    "scc":                      "ibm-cloud--security-compliance-center",
    "security compliance":      "ibm-cloud--security-compliance-center",
    "iam":                      "group--access",
    "access group":             "group--access",
    "resource group":           "group--resource",
    "nacl":                     "subnet-acl-rules",
    "acl":                      "subnet-acl-rules",
    # Observability
    "monitoring":               "cloud--monitoring",
    "log analysis":             "ibm-cloud--logging",
    "logging":                  "ibm-cloud--logging",
    "activity tracker":         "ibm-cloud--logging",
    "flow log":                 "flow-logs-vpc",
    # Endpoints
    "vpe":                      "ibm-cloud--vpc-endpoints",
    "endpoint gateway":         "ibm-cloud--vpc-endpoints",
    "private endpoint":         "ibm-cloud--vpc-endpoints",
    # Actors
    "user":                     "user",
    "enterprise":               "enterprise",
}


def _stencil_shape(name: str) -> str:
    """Return the IBM stencil shape name for a component name string."""
    lower = name.lower()
    for token, shape in STENCIL_MAP.items():
        if token in lower:
            return shape
    return ""


def _stencil_color(shape: str) -> str:
    """Return the IBM canonical background color for a stencil shape."""
    return STENCIL_COLOR.get(shape, "#1192E8")


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

    def ibm_node(
        self,
        label: str,
        x: int,
        y: int,
        shape: str,
        *,
        d: int = 48,
    ) -> str:
        """Render an IBM Prescribed Node: colored square bg + white icon child.

        This exactly matches the IBM draw.io sidebar pattern:
          - Outer cell: shape=rect; fillColor=<category-color>; strokeColor=none
          - Inner cell: shape=mxgraph.ibm_cloud.<shape>; fillColor=#ffffff
          - Label sits below both (verticalLabelPosition=bottom)
        """
        bg_color = _stencil_color(shape)
        d2 = d // 2   # icon is half the bg size, centered
        bg_id   = self._next_id()
        icon_id = self._next_id()

        bg_style = (
            "shape=rect;"
            f"fillColor={bg_color};strokeColor=none;"
            "aspect=fixed;resizable=0;"
            "labelPosition=center;verticalLabelPosition=bottom;"
            "align=center;verticalAlign=top;"
            f"fontSize=11;fontColor={COLOR['icon_font']};"
            "html=1;"
        )
        icon_style = (
            f"shape=mxgraph.ibm_cloud.{shape};"
            "fillColor=#ffffff;strokeColor=none;"
            "dashed=0;html=1;"
            "labelPosition=center;verticalLabelPosition=bottom;"
            "verticalAlign=top;part=1;"
            "movable=0;resizable=0;rotatable=0;"
        )
        offset_x = (d - d2) // 2
        offset_y = (d - d2) // 2

        self.cells.append(
            f'<mxCell id="{bg_id}" value="{escape(label)}" style="{bg_style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{d}" height="{d}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{bg_id}">'
            f'<mxGeometry x="{offset_x}" y="{offset_y}" width="{d2}" height="{d2}" as="geometry" />'
            "</mxCell>"
        )
        return bg_id

    def ibm_actor(
        self,
        label: str,
        x: int,
        y: int,
        shape: str,
        *,
        d: int = 48,
    ) -> str:
        """Render an IBM Actor node: black circle bg + white icon child."""
        bg_color = _stencil_color(shape)
        d2 = d // 2
        bg_id   = self._next_id()
        icon_id = self._next_id()

        bg_style = (
            "shape=ellipse;"
            f"fillColor={bg_color};strokeColor=none;"
            "aspect=fixed;resizable=0;"
            "labelPosition=center;verticalLabelPosition=bottom;"
            "align=center;verticalAlign=top;"
            f"fontSize=11;fontColor={COLOR['icon_font']};"
            "html=1;"
        )
        icon_style = (
            f"shape=mxgraph.ibm_cloud.{shape};"
            "fillColor=#ffffff;strokeColor=none;"
            "dashed=0;html=1;part=1;"
            "movable=0;resizable=0;rotatable=0;"
        )
        offset_x = (d - d2) // 2
        offset_y = (d - d2) // 2

        self.cells.append(
            f'<mxCell id="{bg_id}" value="{escape(label)}" style="{bg_style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{d}" height="{d}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{bg_id}">'
            f'<mxGeometry x="{offset_x}" y="{offset_y}" width="{d2}" height="{d2}" as="geometry" />'
            "</mxCell>"
        )
        return bg_id

    def ibm_location(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
        shape: str,
        stroke_color: str,
        *,
        stroke_width: int = 1,
        dashed: bool = False,
        icon_size: int = 24,
    ) -> str:
        """Render an IBM Prescribed Location (container with left border strip + icon).

        Matches the IBM sidebar addIBMCloudPrescribedLocation pattern:
          - Outer container: fillColor=none; strokeColor=<color>; strokeWidth=<sw>
          - Left strip child: shape=rect; fillColor=<color>; width=4
          - Icon child: shape=mxgraph.ibm_cloud.<shape>; fillColor=<color>
          - Label as part of the icon child row
        """
        outer_id = self._next_id()
        strip_id = self._next_id()
        icon_id  = self._next_id()
        label_id = self._next_id()

        dash_str = "dashed=1;dashPattern=8 4;" if dashed else "dashed=0;"
        outer_style = (
            "container=1;collapsible=0;expand=0;recursiveResize=0;"
            "html=1;whiteSpace=wrap;"
            f"fillColor=none;strokeColor={stroke_color};strokeWidth={stroke_width};"
            + dash_str
        )
        strip_style = (
            "shape=rect;"
            f"fillColor={stroke_color};strokeColor=none;"
            "aspect=fixed;part=1;movable=0;resizable=0;rotatable=0;"
        )
        icon_style = (
            f"shape=mxgraph.ibm_cloud.{shape};"
            f"fillColor={stroke_color};strokeColor=none;"
            "dashed=0;html=1;part=1;movable=0;resizable=0;rotatable=0;"
        )
        label_style = (
            "shape=rect;fillColor=none;strokeColor=none;"
            "labelPosition=right;verticalLabelPosition=middle;"
            "align=left;verticalAlign=middle;"
            "fontSize=13;fontStyle=1;part=1;movable=0;resizable=0;rotatable=0;"
            "spacingLeft=5;"
        )

        self.cells.append(
            f'<mxCell id="{outer_id}" value="" style="{outer_style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        # Left border strip (4px wide, full height)
        self.cells.append(
            f'<mxCell id="{strip_id}" value="" style="{strip_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="0" y="0" width="4" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        # Icon positioned top-left after the strip
        self.cells.append(
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        )
        # Label to the right of the icon
        self.cells.append(
            f'<mxCell id="{label_id}" value="{escape(label)}" style="{label_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        )
        return outer_id

    def container(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: str = "none",
        stroke: str = "#8d8d8d",
        stroke_width: int = 1,
        font_size: int = 13,
        font_style: int = 1,
        dashed: bool = False,
        vertical_align: str = "top",
    ) -> str:
        """Plain container boundary box — no IBM icon strip (for subnet bands, misc)."""
        cell_id = self._next_id()
        dash_str = "dashed=1;dashPattern=8 4;" if dashed else ""
        style = (
            "container=1;collapsible=0;expand=0;recursiveResize=0;"
            "rounded=0;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth={stroke_width};"
            f"fontSize={font_size};fontStyle={font_style};"
            f"verticalAlign={vertical_align};align=left;"
            + dash_str
        )
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
        stroke: str = "#1192E8",
        font_size: int = 11,
        font_style: int = 0,
        dashed: bool = False,
        align: str = "center",
        vertical_align: str = "middle",
    ) -> str:
        """Generic rounded rectangle (title bar, fallback nodes)."""
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
            "strokeColor=#1192E8;"
        )
        if dashed:
            style += "dashed=1;endArrow=open;endFill=0;strokeColor=#878D96;"
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
        """Availability zone boundary — IBM Zone pattern (dashed gray, data--center icon)."""
        # IBM Zone = dashed container with data--center icon, grey stroke
        return self.ibm_location(
            label, x, y, w, h,
            shape="data--center",
            stroke_color=COLOR["az_stroke"],
            stroke_width=1,
            dashed=True,
            icon_size=24,
        )

    def subnet_band(self, label: str, x: int, y: int, w: int, h: int, tier: str) -> str:
        """Colored subnet tier band — IBM Subnet pattern with tinted fill."""
        fill = COLOR.get(tier, "#ffffff")
        cell_id = self._next_id()
        style = (
            "container=1;collapsible=0;expand=0;recursiveResize=0;"
            f"fillColor={fill};strokeColor={COLOR['az_stroke']};strokeWidth=1;"
            "rounded=0;whiteSpace=wrap;html=1;"
            "fontStyle=1;fontSize=11;align=left;verticalAlign=top;"
        )
        self.cells.append(
            f'<mxCell id="{cell_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def transit_gateway(self, label: str, x: int, y: int) -> str:
        """IBM Transit Gateway — prescribed node (cyan-blue square + white icon)."""
        return self.ibm_node(label, x, y, "ibm-cloud--transit-gateway", d=48)

    def powervs_workspace(self, label: str, x: int, y: int, w: int, h: int) -> str:
        """PowerVS workspace boundary — IBM Location pattern, green border."""
        return self.ibm_location(
            label, x, y, w, h,
            shape="ibm--power-vs",
            stroke_color=COLOR["compute"],
            stroke_width=1,
            dashed=True,
            icon_size=24,
        )

    def vpe_gateway(self, label: str, x: int, y: int, parent_id: str) -> str:
        """VPE gateway node + dotted edge to its parent service."""
        node_id = self.ibm_node(label, x, y, "ibm-cloud--vpc-endpoints", d=40)
        self.edge(node_id, parent_id, dashed=True)
        return node_id

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
    """Render a component using the IBM Prescribed Node pattern.

    Uses ibm_node (colored square + white icon) when a stencil shape is found,
    falls back to a generic box otherwise.
    """
    name = item.get("name") or fallback_name
    shape = _stencil_shape(name)

    if shape:
        # IBM prescribed node: use the stencil's canonical color, not the tier tint
        return builder.ibm_node(name, x, y, shape, d=48)
    else:
        fill = COLOR.get(tier, "#ffffff") if tier else "#ffffff"
        return builder.box(name, x, y, w, h, fill=fill, font_size=10)


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

    # ── External lane (left) — IBM Location: grey border, network--public icon ──
    builder.ibm_location(
        "External / Internet", 20, ACCOUNT_Y, 220, 460,
        shape="network--public", stroke_color=COLOR["grey"],
    )
    users_node    = builder.ibm_actor("Users / Clients",   50, ACCOUNT_Y + 80,  "user",       d=48)
    ext_sys_node  = builder.ibm_actor("External Systems",  50, ACCOUNT_Y + 190, "enterprise", d=48)

    # ── IBM Cloud Account boundary — IBM Location: cyan border, ibm-cloud icon ──
    cloud = builder.ibm_location(
        "IBM Cloud Account", 280, ACCOUNT_Y, 1720, 740,
        shape="ibm-cloud", stroke_color=COLOR["network"],
        stroke_width=2,
    )
    builder.edge(users_node, cloud, "HTTPS requests")
    builder.edge(ext_sys_node, cloud, "API integration")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    region_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 820
        # IBM Location: grey border, location icon
        rn = builder.ibm_location(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 760, 540,
            shape="location", stroke_color=COLOR["grey"],
        )
        region_nodes.append(rn)

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC", "purpose": "Application network"})
        # IBM Location: cyan border, ibm-cloud--vpc icon
        builder.ibm_location(
            _label(vpc, "VPC"), rx + 30, ACCOUNT_Y + 130, 700, 370,
            shape="ibm-cloud--vpc", stroke_color=COLOR["network"],
        )

        # Ingress → Compute → Data (left-to-right, style guide)
        ingress  = _preferred(ibm_cloud.get("ingress"),  {"name": "Ingress"})
        compute  = _preferred(ibm_cloud.get("compute"),  {"name": "Compute"})
        data_svc = _preferred(ibm_cloud.get("data"),     {"name": "Data Services"})

        ingress_node  = _service_node(builder, ingress,  "Ingress",       rx + 50,  ACCOUNT_Y + 200)
        compute_node  = _service_node(builder, compute,  "Compute",       rx + 280, ACCOUNT_Y + 200)
        data_node     = _service_node(builder, data_svc, "Data",          rx + 510, ACCOUNT_Y + 200)

        builder.edge(ingress_node, compute_node, "app traffic")
        builder.edge(compute_node, data_node, "data access")

        # Security + Observability (bottom of VPC)
        security = _preferred(ibm_cloud.get("security"),    {"name": "IAM / Secrets / Keys"})
        obs      = _preferred(ibm_cloud.get("observability"),{"name": "Monitoring / Logging"})

        sec_node = _service_node(builder, security, "Security",    rx + 50,  ACCOUNT_Y + 330)
        obs_node = _service_node(builder, obs,      "Observability",rx + 280, ACCOUNT_Y + 330)

        builder.edge(sec_node, compute_node, "identity & secrets")
        builder.edge(compute_node, obs_node, "telemetry")

    # ── Connectivity bar (bottom) ────────────────────────────────────────
    conn       = _preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity"})
    conn_shape = _stencil_shape(conn.get("name") or "direct link")
    conn_node  = builder.ibm_node(
        conn.get("name") or "Connectivity", 300, ACCOUNT_Y + 640,
        conn_shape or "ibm-cloud--direct-link-2--connect",
    )
    for rn in region_nodes:
        builder.edge(conn_node, rn, "")

    # ── Security boundary (bottom-right, shown as a node) ────────────────
    if ibm_cloud.get("security"):
        sec = _preferred(ibm_cloud.get("security"), {"name": "Security & Compliance"})
        _service_node(builder, sec, "Security & Compliance", 600, ACCOUNT_Y + 640)


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

    # ── Left: external — IBM Location: grey, network--public ─────────────
    builder.ibm_location(
        "External / Internet", 20, ACCOUNT_Y, 220, 560,
        shape="network--public", stroke_color=COLOR["grey"],
    )
    users_node   = builder.ibm_actor("Users / Clients",  50, ACCOUNT_Y + 80,  "user",       d=48)
    ext_sys_node = builder.ibm_actor("External Systems", 50, ACCOUNT_Y + 190, "enterprise", d=48)

    # ── Center: IBM Cloud Account — IBM Location: cyan, ibm-cloud ────────
    cloud = builder.ibm_location(
        "IBM Cloud Account", 280, ACCOUNT_Y, 1280, 740,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )
    builder.edge(users_node, cloud, "HTTPS")
    builder.edge(ext_sys_node, cloud, "API")

    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    vpc_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 600
        builder.ibm_location(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 560, 540,
            shape="location", stroke_color=COLOR["grey"],
        )

        vpc = _preferred(ibm_cloud.get("vpcs"), {"name": "VPC"})
        vpc_node = builder.ibm_location(
            _label(vpc, "VPC"), rx + 20, ACCOUNT_Y + 120, 520, 380,
            shape="ibm-cloud--vpc", stroke_color=COLOR["network"],
        )
        vpc_nodes.append(vpc_node)

        ingress  = _preferred(ibm_cloud.get("ingress"),  {"name": "Ingress"})
        compute  = _preferred(ibm_cloud.get("compute"),  {"name": "Compute"})
        security = _preferred(ibm_cloud.get("security"), {"name": "Security"})
        obs      = _preferred(ibm_cloud.get("observability"), {"name": "Observability"})

        in_node   = _service_node(builder, ingress,  "Ingress",       rx + 30,  ACCOUNT_Y + 180)
        comp_node = _service_node(builder, compute,  "Compute",       rx + 180, ACCOUNT_Y + 180)
        sec_node  = _service_node(builder, security, "Security",      rx + 30,  ACCOUNT_Y + 310)
        obs_node  = _service_node(builder, obs,      "Observability", rx + 180, ACCOUNT_Y + 310)

        builder.edge(in_node,   comp_node, "app traffic")
        builder.edge(sec_node,  comp_node, "auth & secrets")
        builder.edge(comp_node, obs_node,  "telemetry")

    # ── Right: data stores ───────────────────────────────────────────────
    builder.ibm_location(
        "Data & Storage", 1600, ACCOUNT_Y + 60, 320, 500,
        shape="data--base", stroke_color=COLOR["data"],
    )
    data_items = ibm_cloud.get("data") or [{"name": "Data Services"}]
    for di, ditem in enumerate(data_items[:4]):
        dn = _service_node(builder, ditem, "Data", 1620, ACCOUNT_Y + 130 + di * 90)
        if vpc_nodes:
            builder.edge(vpc_nodes[0], dn, "private data access")

    # ── Transit Gateway (if present) ─────────────────────────────────────
    if _has_transit_gateway(ibm_cloud):
        tgw = builder.transit_gateway("Transit Gateway", 840, ACCOUNT_Y + 760)
        for vn in vpc_nodes:
            builder.edge(tgw, vn, "")
    else:
        conn      = _preferred(ibm_cloud.get("connectivity"), {"name": "Connectivity"})
        conn_node = _service_node(builder, conn, "Connectivity", 320, ACCOUNT_Y + 760)
        for rn_id in vpc_nodes:
            builder.edge(conn_node, rn_id, "network")

    # ── PowerVS (if present) ─────────────────────────────────────────────
    if _has_powervs(ibm_cloud):
        pw = builder.powervs_workspace("PowerVS Workspace", 1980, ACCOUNT_Y + 100, 260, 340)
        if vpc_nodes:
            builder.edge(pw, vpc_nodes[0], "cloud connection")

    # ── Bottom: backup/DR ────────────────────────────────────────────────
    backup = ibm_cloud.get("backup_dr")
    if backup:
        bitem = _preferred(backup, {"name": "Backup / DR"})
        builder.ibm_node(
            bitem.get("name") or "Backup / DR",
            320, ACCOUNT_Y + 840,
            "ibm-cloud--continuous-delivery",
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

    # ── External lane (left) — IBM Location: grey, network--public ───────
    builder.ibm_location(
        "External / Internet", 20, ACCOUNT_Y, 200, ACCOUNT_H,
        shape="network--public", stroke_color=COLOR["grey"],
    )
    users_node   = builder.ibm_actor("Users / Clients",  30, ACCOUNT_Y + 80,  "user",       d=48)
    ext_sys_node = builder.ibm_actor("External Systems", 30, ACCOUNT_Y + 200, "enterprise", d=48)

    # ── IBM Cloud Account boundary — IBM Location: cyan, ibm-cloud ───────
    cloud = builder.ibm_location(
        "IBM Cloud Account",
        ACCOUNT_X + 220, ACCOUNT_Y, ACCOUNT_W - 220, ACCOUNT_H,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
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

        region_node = builder.ibm_location(
            _label(region, "Region"), rx, ry, REGION_W, REGION_H,
            shape="location", stroke_color=COLOR["grey"],
        )
        region_nodes.append(region_node)

        vpc_x = rx + VPC_MARGIN_X
        vpc_y = ry + VPC_MARGIN_Y
        vpc_node = builder.ibm_location(
            _label(vpc, "VPC"), vpc_x, vpc_y, VPC_W, VPC_H,
            shape="ibm-cloud--vpc", stroke_color=COLOR["network"],
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
                        if shape:
                            nid = builder.ibm_node(name, cx, cy, shape, d=40)
                        else:
                            nid = builder.box(
                                name, cx, cy, chip_w, chip_h,
                                fill=COLOR.get(tier, "#ffffff"), font_size=9,
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
            dl_node = builder.ibm_node(
                dl.get("name") or "Direct Link",
                account_left + REGION_MARGIN_X, tgw_y,
                dl_shape or "ibm-cloud--direct-link-2--connect",
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


def render_ibm_node_snippet(
    name: str,
    shape: str,
    *,
    x: int = 100,
    y: int = 100,
    d: int = 48,
    parent_id: str = "1",
) -> str:
    """Return standalone Draw.io XML for a single IBM Prescribed Node.

    The returned XML wraps the two-cell node (colored square bg + white icon
    child) in a minimal ``<mxGraphModel>`` so it can be imported into an open
    Draw.io document via the ``import-diagram`` MCP tool in ``add`` mode.

    Parameters
    ----------
    name:
        Human-readable label shown beneath the icon.
    shape:
        IBM Cloud stencil name (e.g. ``"ibm-cloud--virtual-server-vpc"``).
        Use ``_stencil_shape(name)`` if you have a component name string.
    x, y:
        Top-left position of the node in the target diagram.
    d:
        Node size in pixels (default 48).
    parent_id:
        Draw.io parent cell ID (``"1"`` = root layer; pass a band/AZ cell ID
        to nest the node inside a container).
    """
    builder = DrawioBuilder()
    # Override the auto-generated IDs to respect parent_id when it is not "1".
    # The builder always uses parent="1" in ibm_node(); we patch the output.
    bg_color = _stencil_color(shape)
    d2 = d // 2
    bg_id   = "np2"
    icon_id = "np3"
    offset  = (d - d2) // 2

    from xml.sax.saxutils import escape as _esc
    bg_style = (
        "shape=rect;"
        f"fillColor={bg_color};strokeColor=none;"
        "aspect=fixed;resizable=0;"
        "labelPosition=center;verticalLabelPosition=bottom;"
        "align=center;verticalAlign=top;"
        f"fontSize=11;fontColor={COLOR['icon_font']};"
        "html=1;"
    )
    icon_style = (
        f"shape=mxgraph.ibm_cloud.{shape};"
        "fillColor=#ffffff;strokeColor=none;"
        "dashed=0;html=1;"
        "labelPosition=center;verticalLabelPosition=bottom;"
        "verticalAlign=top;part=1;"
        "movable=0;resizable=0;rotatable=0;"
    )
    cells = [
        '<mxCell id="0" />',
        '<mxCell id="1" parent="0" />',
        (
            f'<mxCell id="{bg_id}" value="{_esc(name)}" style="{bg_style}" '
            f'vertex="1" parent="{parent_id}">'
            f'<mxGeometry x="{x}" y="{y}" width="{d}" height="{d}" as="geometry" />'
            "</mxCell>"
        ),
        (
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{bg_id}">'
            f'<mxGeometry x="{offset}" y="{offset}" width="{d2}" height="{d2}" as="geometry" />'
            "</mxCell>"
        ),
    ]
    cells_xml = "\n    ".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxGraphModel>\n'
        '  <root>\n'
        f'    {cells_xml}\n'
        '  </root>\n'
        '</mxGraphModel>'
    )


def render_ibm_location_snippet(
    name: str,
    shape: str,
    stroke_color: str,
    *,
    x: int = 100,
    y: int = 100,
    w: int = 300,
    h: int = 200,
    parent_id: str = "1",
) -> str:
    """Return standalone Draw.io XML for a single IBM Prescribed Location container.

    Produces the four-cell container pattern (outer frame + left border strip +
    icon + label) wrapped in a minimal ``<mxGraphModel>`` for ``import-diagram``
    ``add`` mode.

    Parameters
    ----------
    name:
        Label for the container.
    shape:
        IBM Cloud stencil name (e.g. ``"ibm-cloud--vpc"``, ``"location"``,
        ``"data--center"``).
    stroke_color:
        IBM brand color for the border and icon (e.g. ``"#1192E8"``).
    x, y:
        Top-left position in the target diagram.
    w, h:
        Width and height of the container.
    parent_id:
        Draw.io parent cell ID (``"1"`` = root layer).
    """
    from xml.sax.saxutils import escape as _esc
    icon_size = 24
    outer_id  = "nl2"
    strip_id  = "nl3"
    icon_id   = "nl4"
    label_id  = "nl5"

    outer_style = (
        "container=1;collapsible=0;expand=0;recursiveResize=0;"
        "html=1;whiteSpace=wrap;"
        f"fillColor=none;strokeColor={stroke_color};strokeWidth=1;dashed=0;"
    )
    strip_style = (
        "shape=rect;"
        f"fillColor={stroke_color};strokeColor=none;"
        "aspect=fixed;part=1;movable=0;resizable=0;rotatable=0;"
    )
    icon_style = (
        f"shape=mxgraph.ibm_cloud.{shape};"
        f"fillColor={stroke_color};strokeColor=none;"
        "dashed=0;html=1;part=1;movable=0;resizable=0;rotatable=0;"
    )
    label_style = (
        "shape=rect;fillColor=none;strokeColor=none;"
        "labelPosition=right;verticalLabelPosition=middle;"
        "align=left;verticalAlign=middle;"
        "fontSize=13;fontStyle=1;part=1;movable=0;resizable=0;rotatable=0;"
        "spacingLeft=5;"
    )
    cells = [
        '<mxCell id="0" />',
        '<mxCell id="1" parent="0" />',
        (
            f'<mxCell id="{outer_id}" value="" style="{outer_style}" '
            f'vertex="1" parent="{parent_id}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
            "</mxCell>"
        ),
        (
            f'<mxCell id="{strip_id}" value="" style="{strip_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="0" y="0" width="4" height="{h}" as="geometry" />'
            "</mxCell>"
        ),
        (
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        ),
        (
            f'<mxCell id="{label_id}" value="{_esc(name)}" style="{label_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        ),
    ]
    cells_xml = "\n    ".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxGraphModel>\n'
        '  <root>\n'
        f'    {cells_xml}\n'
        '  </root>\n'
        '</mxGraphModel>'
    )


def render_all_diagrams(architecture: dict) -> dict[str, str]:
    """Return all three diagram types as a dict keyed by type name.

    Returns::

        {
            "context":    "<mxGraphModel>...</mxGraphModel>",
            "logical":    "<mxGraphModel>...</mxGraphModel>",
            "deployment": "<mxGraphModel>...</mxGraphModel>",
        }

    Suitable for multi-page imports via the MCP ``import-diagram`` tool.
    """
    return {
        "context":    render_drawio(architecture, diagram_type="context"),
        "logical":    render_drawio(architecture, diagram_type="logical"),
        "deployment": render_drawio(architecture, diagram_type="deployment"),
    }


def render_multipage_drawio(architecture: dict) -> str:
    """Return a single multi-page Draw.io XML document with all three diagram types.

    Each diagram type becomes a named page (``<diagram>`` element).  The result
    can be saved as a ``.drawio`` file and opened in Draw.io desktop or
    diagrams.net without the MCP server.
    """
    page_names = {
        "context":    "Context",
        "logical":    "Logical Architecture",
        "deployment": "Deployment",
    }
    diagrams_xml: list[str] = []
    for dtype, page_name in page_names.items():
        inner_xml = render_drawio(architecture, diagram_type=dtype)
        # Strip the outer <?xml ...?><mxGraphModel> wrapper — we need just the
        # <root>...</root> content to embed as a named page.
        import re as _re
        root_match = _re.search(r"<root>(.*?)</root>", inner_xml, _re.DOTALL)
        root_content = root_match.group(1) if root_match else inner_xml
        # Escape for CDATA embedding
        diagrams_xml.append(
            f'  <diagram name="{page_name}">'
            f"<mxGraphModel><root>{root_content}</root></mxGraphModel>"
            f"</diagram>"
        )
    pages = "\n".join(diagrams_xml)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<mxfile>\n"
        f"{pages}\n"
        "</mxfile>"
    )
