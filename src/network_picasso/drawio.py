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
    "ibm-cloud--instana":                   "#1192E8",
    "tracing--node":                        "#1192E8",
    # Integration / Event-Driven — blue
    "ibm-cloud--event-streams":             "#0F62FE",
    "event--alt":                           "#0F62FE",
    "ibm-cloud--event-notifications":       "#0F62FE",
    "ibm-cloud--functions":                 "#0F62FE",
    "ibm-cloud--code-engine":               "#198038",
    # AI / watsonx — purple
    "ibm-cloud--watsonx-ai":               "#A56EFF",
    "ibm-cloud--watsonx-data":             "#A56EFF",
    "ibm-cloud--watsonx-governance":       "#A56EFF",
    "watson--machine-learning":             "#A56EFF",
    "watson--studio":                       "#A56EFF",
    "application":                          "#A56EFF",
    "application--web":                     "#A56EFF",
    # Security additions
    "ibm-cloud--app-id":                    "#FA4D56",
    "ibm-cloud--container-registry":        "#FA4D56",
    "ibm-cloud--certificate-manager":       "#FA4D56",
    "ibm-cloud--schematics":                "#FA4D56",
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
    "instana":                  "ibm-cloud--instana",
    "dynatrace":                "tracing--node",
    # Event-Driven / Integration
    "event streams":            "ibm-cloud--event-streams",
    "kafka":                    "ibm-cloud--event-streams",
    "event notifications":      "ibm-cloud--event-notifications",
    "cloud functions":          "ibm-cloud--functions",
    "functions":                "ibm-cloud--functions",
    "code engine":              "ibm-cloud--code-engine",
    # AI / watsonx
    "watsonx.ai":               "ibm-cloud--watsonx-ai",
    "watsonx.data":             "ibm-cloud--watsonx-data",
    "watsonx.governance":       "ibm-cloud--watsonx-governance",
    "watsonx":                  "ibm-cloud--watsonx-ai",
    "watson machine learning":  "watson--machine-learning",
    "watson studio":            "watson--studio",
    "watson":                   "watson--studio",
    # Security additions
    "app id":                   "ibm-cloud--app-id",
    "certificate manager":      "ibm-cloud--certificate-manager",
    "container registry":       "ibm-cloud--container-registry",
    "schematics":               "ibm-cloud--schematics",
    # Satellite
    "satellite":                "cloud-satellite",
    "satellite connector":      "cloud-satellite",
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
        parent: str = "1",
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
            f'vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        return cell_id

    def child_ibm_node(
        self,
        label: str,
        x: int,
        y: int,
        shape: str,
        parent: str,
        *,
        d: int = 48,
    ) -> str:
        """IBM Prescribed Node as a CHILD of another container cell."""
        bg_color = _stencil_color(shape)
        d2 = d // 2
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
            f'vertex="1" parent="{parent}">'
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

    def child_ibm_location(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
        shape: str,
        stroke_color: str,
        parent: str,
        *,
        stroke_width: int = 1,
        dashed: bool = False,
        icon_size: int = 24,
        fill: str = "none",
    ) -> str:
        """IBM Prescribed Location as a CHILD of another container."""
        outer_id = self._next_id()
        strip_id = self._next_id()
        icon_id  = self._next_id()
        label_id = self._next_id()

        dash_str = "dashed=1;dashPattern=8 4;" if dashed else "dashed=0;"
        outer_style = (
            "container=1;collapsible=0;expand=0;recursiveResize=0;"
            "html=1;whiteSpace=wrap;"
            f"fillColor={fill};strokeColor={stroke_color};strokeWidth={stroke_width};"
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
            f'vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{strip_id}" value="" style="{strip_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="0" y="0" width="4" height="{height}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{label_id}" value="{escape(label)}" style="{label_style}" '
            f'vertex="1" parent="{outer_id}">'
            f'<mxGeometry x="8" y="8" width="{icon_size}" height="{icon_size}" as="geometry" />'
            "</mxCell>"
        )
        return outer_id

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
# Deployment diagram — data-driven, no hardcoded topology
# ---------------------------------------------------------------------------
# The renderer reads ONLY what was extracted into ibm_cloud and the answered
# questions.  It does NOT assume any specific pattern (hub-and-spoke, single
# VPC, etc.) — those decisions come from the data.
#
# Pattern detection (from extracted data):
#   has_on_prem    → Direct Link or VPN present in connectivity
#   has_tgw        → Transit Gateway present → draw TGW node
#   vpc_count      → number of extracted VPCs → draw that many VPC containers
#   az_count       → detected from zone tags on subnets/compute, else 3 if MZR
#   has_powervs    → Power VS in compute → draw PowerVS workspace
#   has_dr         → two regions extracted → draw DR summary
#
# Layout rules (from 03-deployment-architecture.md + IBM style guide):
#   - On-prem / Enterprise block only when DL or VPN is present
#   - Connectivity column only when on-prem is present
#   - One VPC container per extracted VPC (named from data)
#   - Zones stacked inside each VPC, count derived from data (fallback: 3)
#   - Subnets inside zones, labelled from extracted subnet_tier hints
#   - Shared services (data, security, obs) on the right, always present
#   - DR box only when second region extracted
# ---------------------------------------------------------------------------

# Layout geometry — everything is relative to these anchors
_BASE_X   = 20
_BASE_Y   = 80
_NODE_D   = 48
_NODE_GAP = 72
_SG_M     = 8     # security-group / subnet inner margin


def _az_count_from_data(ibm_cloud: dict) -> int:
    """Detect how many AZs to draw from zone tags in the extracted model."""
    seen: set[str] = set()
    for key in ("subnets", "compute", "ingress", "data"):
        for item in ibm_cloud.get(key, []):
            z = str(item.get("zone") or "").strip()
            if z:
                seen.add(z.lower())
    # Accept tags like "zone-1", "zone-2", "Zone 1", "dal10"
    known = [z for z in seen if any(c.isdigit() for c in z)]
    count = len(known)
    return max(count, 1) if count else 3  # default 3 for MZR


def _vpc_tier_items(ibm_cloud: dict, vpc_name: str) -> dict[str, list[dict]]:
    """Return items for each subnet tier relevant to a given VPC.

    Uses subnet_tier hints in the extracted model.  Falls back to category
    mapping when no explicit hint is present.
    """
    tier_map: dict[str, list[dict]] = {
        "Public": [], "Private": [], "Management": [], "Data": [],
    }
    category_to_tier = {
        "ingress": "Public",
        "compute": "Private",
        "security": "Management",
        "observability": "Management",
        "data": "Data",
    }
    for cat, default_tier in category_to_tier.items():
        for item in ibm_cloud.get(cat, []):
            tier = item.get("subnet_tier") or default_tier
            if tier in tier_map:
                tier_map[tier].append(item)
    return tier_map


def _render_deployment(builder: DrawioBuilder, project: dict, ibm_cloud: dict) -> None:  # noqa: PLR0912, PLR0915
    """Render a deployment diagram driven entirely by the extracted architecture model.

    No topology is assumed.  Every structural element (on-prem block, VPC count,
    AZ count, node types) is derived from the ibm_cloud dict.
    """
    _render_title(builder, project, "deployment")

    regions_data   = ibm_cloud.get("regions")          or [{"name": "Region TBD"}]
    conn_items     = ibm_cloud.get("connectivity")      or []
    vpcs_data      = ibm_cloud.get("vpcs")              or [{"name": "VPC", "purpose": ""}]
    data_items     = ibm_cloud.get("data")              or []
    security_items = ibm_cloud.get("security")          or []
    obs_items      = ibm_cloud.get("observability")     or []
    private_eps    = ibm_cloud.get("private_endpoints") or []

    # ── Pattern detection — from extracted data, no assumptions ──────────
    has_on_prem = any(
        kw in (c.get("name") or "").lower()
        for c in conn_items
        for kw in ("direct link", "vpn", "direct-link")
    )
    has_tgw     = _has_transit_gateway(ibm_cloud)
    has_powervs = _has_powervs(ibm_cloud)
    has_dr      = len(regions_data) > 1
    az_count    = _az_count_from_data(ibm_cloud)
    vpc_count   = len(vpcs_data)

    # ── Layout anchors — shift right if on-prem block is present ─────────
    ent_w    = 260
    conn_w   = 200
    gap      = 20

    cursor_x = _BASE_X

    # ── On-Premises block (only when Direct Link or VPN extracted) ───────
    on_prem_node: str | None = None
    users_node:   str | None = None

    if has_on_prem:
        ent_h = 360
        builder.ibm_location(
            "Enterprise / On-Premises", cursor_x, _BASE_Y, ent_w, ent_h,
            shape="network--enterprise", stroke_color=COLOR["grey"],
        )
        users_node  = builder.ibm_actor("Users",      cursor_x + 20, _BASE_Y + 60,  "user",       d=40)
        on_prem_node = builder.ibm_actor("Enterprise", cursor_x + 20, _BASE_Y + 160, "enterprise", d=40)

        # Only draw connectivity equipment that was actually extracted
        eq_y = _BASE_Y + 260
        vpn_items = [c for c in conn_items if "vpn" in (c.get("name") or "").lower()]
        if vpn_items:
            builder.ibm_node(vpn_items[0].get("name") or "VPN", cursor_x + 20, eq_y, "ibm--vpn-for-vpc", d=36)
            eq_y += 52

        cursor_x += ent_w + gap

        # Connectivity column — items from extracted connectivity
        non_tgw = [c for c in conn_items if "transit" not in (c.get("name") or "").lower()]
        if non_tgw:
            conn_container = builder.ibm_location(
                "Connectivity", cursor_x, _BASE_Y, conn_w, ent_h,
                shape="arrows--horizontal", stroke_color=COLOR["network"],
            )
            if on_prem_node:
                builder.edge(on_prem_node, conn_container, "")
            if users_node:
                builder.edge(users_node, conn_container, "HTTPS/API")

            cy = _BASE_Y + 60
            conn_anchor: str | None = None
            for citem in non_tgw[:3]:
                cshape = _stencil_shape(citem.get("name") or "")
                cid = builder.ibm_node(
                    citem.get("name") or "Connectivity",
                    cursor_x + 20, cy,
                    cshape or "ibm-cloud--direct-link-2--connect", d=36,
                )
                if conn_anchor is None:
                    conn_anchor = cid
                cy += 72
            cursor_x += conn_w + gap
    else:
        # Internet-only: just show users on the left
        users_node = builder.ibm_actor("Users / Clients", cursor_x + 10, _BASE_Y + 60, "user", d=40)
        cursor_x += 80 + gap

    # ── IBM Cloud Account ─────────────────────────────────────────────────
    # Width: fit all VPCs side-by-side inside, plus shared services on right
    per_vpc_w   = max(480, 1200 // max(vpc_count, 1))
    ibm_inner_w = vpc_count * per_vpc_w + (vpc_count + 1) * gap
    svc_panel_w = 280
    ibm_w       = ibm_inner_w + svc_panel_w + gap * 2
    ibm_h       = 80 + max(az_count * 280 + 120, 600)

    ibm_account = builder.ibm_location(
        "IBM Cloud Account", cursor_x, _BASE_Y, ibm_w, ibm_h,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )
    if users_node and not has_on_prem:
        builder.edge(users_node, ibm_account, "HTTPS/API")

    # ── Region ───────────────────────────────────────────────────────────
    reg_margin = 20
    region_id = builder.child_ibm_location(
        _label(regions_data[0], "Region"),
        reg_margin, 60,
        ibm_inner_w - reg_margin, ibm_h - 80,
        "location", COLOR["grey"], ibm_account,
    )

    # ── Transit Gateway (only if extracted) ──────────────────────────────
    tgw_id: str | None = None
    if has_tgw:
        tgw_id = builder.child_ibm_node(
            "Transit Gateway", reg_margin + 10, 20,
            "ibm-cloud--transit-gateway", region_id, d=40,
        )

    # ── VPCs — one per extracted VPC, side by side ───────────────────────
    vpc_ids: list[str] = []
    vpc_x_offset = gap

    for v_idx, vpc in enumerate(vpcs_data):
        vpc_label = vpc.get("name") or f"VPC {v_idx + 1}"
        if vpc.get("purpose"):
            vpc_label += f"\n{vpc['purpose']}"

        vpc_w = per_vpc_w - gap
        vpc_h = ibm_h - 80 - 60 - 20   # fill inside region

        vpc_id = builder.child_ibm_location(
            vpc_label, vpc_x_offset, 60, vpc_w, vpc_h,
            "ibm-cloud--vpc", COLOR["network"], region_id,
        )
        vpc_ids.append(vpc_id)
        if tgw_id:
            builder.edge(tgw_id, vpc_id, "")

        # ── Determine tier items for this VPC ───────────────────────────
        # Use all items if single VPC, otherwise try to match by vpc hint
        if vpc_count == 1:
            tier_items = _vpc_tier_items(ibm_cloud, vpc_label)
        else:
            # Filter items that reference this VPC by name
            filtered: dict[str, list] = {"Public": [], "Private": [], "Management": [], "Data": []}
            cat_tier = {"ingress": "Public", "compute": "Private",
                        "security": "Management", "observability": "Management", "data": "Data"}
            for cat, dtier in cat_tier.items():
                for item in ibm_cloud.get(cat, []):
                    item_vpc = str(item.get("vpc") or item.get("notes") or "").lower()
                    if vpc_label.lower() in item_vpc or vpc_count == 1:
                        tier = item.get("subnet_tier") or dtier
                        if tier in filtered:
                            filtered[tier].append(item)
            # Fall back: distribute evenly if no vpc tags
            if not any(filtered.values()):
                tier_items = _vpc_tier_items(ibm_cloud, vpc_label)
                # Split items across VPCs roughly
                for tier, items in tier_items.items():
                    chunk = len(items) // vpc_count
                    start = v_idx * chunk
                    filtered[tier] = items[start:start + max(chunk, 1)]
            tier_items = filtered

        # ── Availability Zones inside this VPC ──────────────────────────
        zone_h_each = (vpc_h - 60 - az_count * _SG_M) // max(az_count, 1)
        z_y = 60

        for z in range(1, az_count + 1):
            z_label = f"Zone {z}"
            z_w = vpc_w - 2 * _SG_M

            zone_id = builder.child_ibm_location(
                z_label, _SG_M, z_y, z_w, zone_h_each,
                "data--center", COLOR["grey"], vpc_id, dashed=True, icon_size=20,
            )

            # Tiers with items → draw subnet bands inside this zone
            node_x = _SG_M + 4
            TIER_COLORS = {
                "Public": COLOR["Public"], "Private": COLOR["Private"],
                "Management": COLOR["Management"], "Data": COLOR["Data"],
            }
            band_h      = (zone_h_each - 40) // max(len([t for t, its in tier_items.items() if its]), 1)
            band_h      = max(band_h, 60)
            band_y_cur  = 36

            for tier, items in tier_items.items():
                if not items:
                    continue
                # Derive subnet label from first item's subnet_tier or tier name
                first = items[0]
                subnet_name = (
                    first.get("name") if "subnet" in str(first.get("name") or "").lower()
                    else f"{vpc_label.split()[0].lower()}-{tier.lower()}-subnet-{z}"
                )
                sub_id = builder.container(
                    subnet_name,
                    _SG_M, band_y_cur, z_w - 2 * _SG_M, band_h,
                    fill=TIER_COLORS.get(tier, "#f4f4f4"),
                    stroke=COLOR["az_stroke"], font_size=9,
                    parent=zone_id,
                )
                # Place service nodes inside subnet (zone 1 only for clarity)
                if z == 1:
                    nx = _SG_M + 4
                    for item in items[:3]:
                        shape = _stencil_shape(item.get("name") or "")
                        if shape:
                            builder.child_ibm_node(
                                item.get("name") or tier,
                                nx, 8, shape, sub_id, d=36,
                            )
                        nx += _NODE_GAP

                band_y_cur += band_h + _SG_M

            z_y += zone_h_each + _SG_M

        vpc_x_offset += per_vpc_w

    # ── Shared Services panel (right side of IBM Cloud) ───────────────────
    svc_x = ibm_inner_w + gap
    svc_y_start = _BASE_Y + 70

    svc_items: list[tuple[list[dict], str, str]] = [
        (data_items,     "data--base",           "Data"),
        (security_items, "ibm-cloud--key-protect","Security"),
        (obs_items,      "cloud--monitoring",     "Observability"),
    ]
    if private_eps:
        svc_items.append((private_eps[:3], "ibm-cloud--vpc-endpoints", "VPE"))

    svc_node_count = sum(len(lst) for lst, _, _ in svc_items)
    svc_h_total    = svc_node_count * 64 + 80
    svc_container  = builder.child_ibm_location(
        "Shared Services",
        svc_x, 60, svc_panel_w, max(svc_h_total, ibm_h - 100),
        "cloud-services", COLOR["data"], ibm_account,
    )

    svc_node_y = 60
    for item_list, default_shape, group_label in svc_items:
        for sitem in item_list[:4]:
            name = sitem.get("name") or sitem if isinstance(sitem, str) else group_label
            shape = _stencil_shape(name) or default_shape
            builder.child_ibm_node(
                str(name), 16, svc_node_y, shape, svc_container, d=40,
            )
            svc_node_y += 64

    # ── Edge from last VPC to shared services ────────────────────────────
    if vpc_ids:
        builder.edge(vpc_ids[-1], svc_container, "private access via VPE", dashed=True)

    # ── DR region summary (only when second region extracted) ────────────
    if has_dr:
        dr_region = regions_data[1]
        dr_y = _BASE_Y + ibm_h + gap
        dr_id = builder.ibm_location(
            _label(dr_region, "DR Region"),
            cursor_x, dr_y, 520, 110,
            shape="location", stroke_color=COLOR["grey"],
        )
        # COS replication node (only if COS was extracted)
        cos_items = [d for d in data_items if "object" in (d.get("name") or "").lower()
                     or "cos" in (d.get("name") or "").lower()]
        if cos_items:
            builder.ibm_node("COS Cross-Region Replication",
                             cursor_x + 20, dr_y + 30, "object-storage", d=40)
        builder.edge(ibm_account, dr_id, "active/passive DR", dashed=True)

    # ── PowerVS workspace (only when PowerVS compute extracted) ──────────
    if has_powervs:
        pw_x = cursor_x + ibm_w + gap
        pw = builder.powervs_workspace(
            "PowerVS Workspace", pw_x, _BASE_Y, 280, 200,
        )
        if vpc_ids:
            builder.edge(vpc_ids[0], pw, "Cloud Connection", dashed=True)


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
