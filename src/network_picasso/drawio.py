from __future__ import annotations

from dataclasses import dataclass
from html import escape
from itertools import count
from pathlib import Path
import re

from .patterns import best_pattern, match_patterns

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

@dataclass(frozen=True)
class RendererStyle:
    service_font_size: int = 11
    container_label_font_size: int = 13
    connector_font_size: int = 10
    label_box_width: int = 180
    label_box_height: int = 32
    page_width: int = 2400
    page_height: int = 1600
    node_gap: int = 72
    density: str = "balanced"


def _safe_int(value: object, default: int, *, minimum: int, maximum: int) -> int:
    try:
        result = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, result))


def _renderer_style_from_memory(style_memory: dict | None) -> RendererStyle:
    if not isinstance(style_memory, dict):
        return RendererStyle()
    preferences = style_memory.get("preferences") if isinstance(style_memory.get("preferences"), dict) else {}
    page_size = preferences.get("pageSize") if isinstance(preferences.get("pageSize"), dict) else {}
    label_box = preferences.get("medianLabelBox") if isinstance(preferences.get("medianLabelBox"), dict) else {}
    service_font = _safe_int(preferences.get("serviceLabelFontSize"), 11, minimum=9, maximum=14)
    label_width = _safe_int(label_box.get("width"), 180, minimum=120, maximum=340)
    label_height = _safe_int(label_box.get("height"), 32, minimum=24, maximum=72)
    page_width = _safe_int(page_size.get("width"), 2400, minimum=1600, maximum=3200)
    page_height = _safe_int(page_size.get("height"), 1600, minimum=1000, maximum=2200)
    density = str(preferences.get("density") or "balanced")
    return RendererStyle(
        service_font_size=service_font,
        container_label_font_size=max(service_font + 2, 12),
        connector_font_size=max(service_font - 1, 9),
        label_box_width=label_width,
        label_box_height=label_height,
        page_width=page_width,
        page_height=page_height,
        node_gap=64 if density == "compact" else 78,
        density=density,
    )


class DrawioBuilder:
    def __init__(self, style: RendererStyle | None = None) -> None:
        self.style = style or RendererStyle()
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
            f"fontSize={self.style.service_font_size};fontColor={COLOR['icon_font']};"
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
            f"fontSize={self.style.service_font_size};fontColor={COLOR['icon_font']};"
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
            "labelPosition=center;verticalLabelPosition=middle;"
            "align=left;verticalAlign=middle;"
            f"fontSize={self.style.container_label_font_size};fontStyle=1;part=1;movable=0;resizable=0;rotatable=0;"
            "spacingLeft=3;"
        )
        label_x = 8 + icon_size + 8
        label_w = max(width - label_x - 8, 80)

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
            f'<mxGeometry x="{label_x}" y="8" width="{label_w}" height="{icon_size}" as="geometry" />'
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
        font_size: int | None = None,
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
            f"fontSize={font_size or self.style.container_label_font_size};fontStyle={font_style};"
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
            f"fontSize={self.style.service_font_size};fontColor={COLOR['icon_font']};"
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

    def child_service_tile(
        self,
        label: str,
        x: int,
        y: int,
        width: int,
        parent: str,
        shape: str,
        *,
        d: int = 20,
    ) -> str:
        """Compact IBM node row for dense subnet bands."""
        label = _clean_diagram_label(label)
        bg_color = _stencil_color(shape)
        bg_id = self._next_id()
        icon_id = self._next_id()
        label_id = self._next_id()
        icon_d = max(d // 2, 10)
        icon_offset = (d - icon_d) // 2
        label_x = x + d + 6
        label_w = max(min(width - d - 8, self.style.label_box_width), 60)

        bg_style = (
            "shape=rect;"
            f"fillColor={bg_color};strokeColor=none;"
            "aspect=fixed;resizable=0;html=1;"
        )
        icon_style = (
            f"shape=mxgraph.ibm_cloud.{shape};"
            "fillColor=#ffffff;strokeColor=none;"
            "dashed=0;html=1;part=1;"
            "movable=0;resizable=0;rotatable=0;"
        )
        text_style = (
            "shape=rect;fillColor=none;strokeColor=none;"
            "whiteSpace=wrap;html=1;align=left;verticalAlign=middle;"
            f"fontSize={self.style.service_font_size};fontStyle=0;spacingLeft=2;overflow=hidden;"
        )
        self.cells.append(
            f'<mxCell id="{bg_id}" value="" style="{bg_style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{d}" height="{d}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{icon_id}" value="" style="{icon_style}" vertex="1" parent="{bg_id}">'
            f'<mxGeometry x="{icon_offset}" y="{icon_offset}" width="{icon_d}" height="{icon_d}" as="geometry" />'
            "</mxCell>"
        )
        self.cells.append(
            f'<mxCell id="{label_id}" value="{escape(label)}" style="{text_style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{label_x}" y="{y - 2}" width="{label_w}" height="{max(d + 8, self.style.label_box_height)}" as="geometry" />'
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
            "labelPosition=center;verticalLabelPosition=middle;"
            "align=left;verticalAlign=middle;"
            f"fontSize={self.style.container_label_font_size};fontStyle=1;part=1;movable=0;resizable=0;rotatable=0;"
            "spacingLeft=3;"
        )
        label_x = 8 + icon_size + 8
        label_w = max(width - label_x - 8, 80)

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
            f'<mxGeometry x="{label_x}" y="8" width="{label_w}" height="{icon_size}" as="geometry" />'
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
        font_size: int | None = None,
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
            f"fontSize={font_size or self.style.service_font_size};fontStyle={font_style};"
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
            f"jettySize=auto;html=1;fontSize={self.style.connector_font_size};endArrow=block;endFill=1;"
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
            f"fontStyle=1;fontSize={self.style.service_font_size};align=left;verticalAlign=top;"
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

    def render(self, *, diagram_name: str = "IBM Cloud Architecture") -> str:
        body = "\n    ".join(self.cells)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile>\n'
            f'  <diagram name="{escape(diagram_name)}">\n'
            '    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            f'pageScale="1" pageWidth="{self.style.page_width}" pageHeight="{self.style.page_height}" math="0" shadow="0">\n'
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
    name = _clean_diagram_label(item.get("name") or fallback)
    purpose = item.get("purpose")
    if purpose and purpose != name and _is_diagram_purpose(purpose):
        return f"{name}\n{_clean_diagram_label(str(purpose))}"
    return name


def _is_vpc_vsi_item(item: dict) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("name", "purpose", "notes")).lower()
    if "dr vsi recovery" in text:
        return False
    return (
        ("vsi" in text or "virtual server" in text)
        and "powervs" not in text
        and "power virtual" not in text
    )


def _is_powervs_item(item: dict) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("name", "purpose", "notes")).lower()
    return "powervs" in text or "power virtual" in text


def _compact_private_compute_items(items: list[dict]) -> list[dict]:
    """Summarize VSI profile extracts as a workload tier instead of one machine."""
    vsi_items = [item for item in items if _is_vpc_vsi_item(item)]
    if not vsi_items:
        return [item for item in items if not _is_powervs_item(item)]

    text = " ".join(
        str(item.get(key) or "")
        for item in vsi_items
        for key in ("name", "purpose", "notes")
    ).lower()
    if "medical imaging" in text:
        name = "Medical imaging VSI tier"
    else:
        name = "VPC VSI workload tier"

    summary = {
        "name": f"{name}\nMultiple VPC VSI profiles",
        "purpose": "Multiple VPC VSI profiles",
        "type": "compute",
    }
    return [summary] + [item for item in items if not _is_vpc_vsi_item(item) and not _is_powervs_item(item)]


def _clean_diagram_label(label: str) -> str:
    text = str(label).replace("Hippa", "HIPAA").replace("hippa", "HIPAA")
    text = text.replace("Hipaa", "HIPAA")
    lowered = text.strip().lower()
    if lowered.startswith("vpc vsi (") or lowered.startswith("vpc virtual server instance ("):
        return "VPC VSI workload tier\nMultiple profiles"
    if text.strip().lower() == "hipaa compliance":
        return "HIPAA compliance controls"
    return text


def _is_diagram_purpose(purpose: str) -> bool:
    lowered = str(purpose).lower()
    provenance_markers = (
        "from unified pricing workbook",
        "from '",
        "from workbook",
        "sheet ",
    )
    return not any(marker in lowered for marker in provenance_markers)


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
    name = _clean_diagram_label(item.get("name") or fallback_name)
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

def _render_context(builder: DrawioBuilder, project: dict, ibm_cloud: dict, render_plan: dict | None = None) -> None:
    render_plan = render_plan or {}
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
    planned_vpcs = _vpcs_from_render_plan(render_plan, ibm_cloud)
    region_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 820
        # IBM Location: grey border, location icon
        rn = builder.ibm_location(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 760, 540,
            shape="location", stroke_color=COLOR["grey"],
        )
        region_nodes.append(rn)

        vpc = planned_vpcs[min(idx, len(planned_vpcs) - 1)] if planned_vpcs else _preferred(ibm_cloud.get("vpcs"), {"name": "VPC", "purpose": "Application network"})
        # IBM Location: cyan border, ibm-cloud--vpc icon
        vpc_container = builder.ibm_location(
            _label(vpc, "VPC"), rx + 30, ACCOUNT_Y + 130, 700, 370,
            shape="ibm-cloud--vpc", stroke_color=COLOR["network"],
        )
        if idx == 0 and len(planned_vpcs) > 1:
            for vpc_index, planned_vpc in enumerate(planned_vpcs[:4]):
                builder.child_service_tile(
                    _clean_diagram_label(str(planned_vpc.get("name") or f"VPC {vpc_index + 1}")),
                    28 + (vpc_index % 2) * 320,
                    278 + (vpc_index // 2) * 42,
                    280,
                    vpc_container,
                    "ibm-cloud--vpc",
                    d=20,
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

def _render_logical(builder: DrawioBuilder, project: dict, ibm_cloud: dict, render_plan: dict | None = None) -> None:
    render_plan = render_plan or {}
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
    planned_vpcs = _vpcs_from_render_plan(render_plan, ibm_cloud)
    vpc_nodes: list[str] = []

    for idx, region in enumerate(regions[:2]):
        rx = 320 + idx * 600
        builder.ibm_location(
            _label(region, "Region"), rx, ACCOUNT_Y + 60, 560, 540,
            shape="location", stroke_color=COLOR["grey"],
        )

        vpc = planned_vpcs[min(idx, len(planned_vpcs) - 1)] if planned_vpcs else _preferred(ibm_cloud.get("vpcs"), {"name": "VPC"})
        vpc_node = builder.ibm_location(
            _label(vpc, "VPC"), rx + 20, ACCOUNT_Y + 120, 520, 380,
            shape="ibm-cloud--vpc", stroke_color=COLOR["network"],
        )
        vpc_nodes.append(vpc_node)
        if idx == 0 and len(planned_vpcs) > 1:
            for vpc_index, planned_vpc in enumerate(planned_vpcs[:4]):
                builder.child_service_tile(
                    _clean_diagram_label(str(planned_vpc.get("name") or f"VPC {vpc_index + 1}")),
                    24 + (vpc_index % 2) * 225,
                    270 + (vpc_index // 2) * 42,
                    200,
                    vpc_node,
                    "ibm-cloud--vpc",
                    d=20,
                )

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
    for item in ibm_cloud.get("zones", []):
        z = str(item.get("name") or item.get("zone") or "").strip()
        if z:
            seen.add(z.lower())
    # Accept tags like "zone-1", "zone-2", "Zone 1", "dal10"
    known = [z for z in seen if any(c.isdigit() for c in z)]
    count = len(known)
    return max(count, 1) if count else 3  # default 3 for MZR


def _plan_bool(render_plan: dict, key: str, fallback: bool) -> bool:
    value = render_plan.get(key)
    return fallback if value is None else bool(value)


def _vpcs_from_render_plan(render_plan: dict, ibm_cloud: dict) -> list[dict]:
    """Return VPCs to draw, using IBM pattern templates when explicitly chosen."""
    existing = ibm_cloud.get("vpcs") or []
    pattern = str(render_plan.get("pattern") or "").lower()
    if pattern in {"hybrid-powervs-dr", "healthcare-regional-dr", "resiliency-dr"} and existing:
        return existing

    plan_vpcs = render_plan.get("vpcs")
    if isinstance(plan_vpcs, list) and plan_vpcs:
        result: list[dict] = []
        for item in plan_vpcs:
            if isinstance(item, dict):
                result.append({
                    "name": str(item.get("name") or "VPC"),
                    "purpose": str(item.get("purpose") or ""),
                    "region": str(item.get("region") or ""),
                    "tiers": item.get("tiers") if isinstance(item.get("tiers"), list) else [],
                })
            else:
                result.append({"name": str(item), "purpose": "", "tiers": []})
        return result

    if pattern in {"hub-and-spoke", "fsc", "financial-services", "financial-services-cloud"} and len(existing) < 2:
        return [
            {"name": "Edge VPC", "purpose": "Internet ingress, egress, and hybrid connectivity", "tiers": ["Public", "Management"]},
            {"name": "Workload VPC", "purpose": "Private application and data tiers", "tiers": ["Private", "Data"]},
        ]
    if pattern in {"mzr", "three-tier-vpc", "basic-vpc"} and existing:
        return existing
    return existing or [{"name": "VPC", "purpose": ""}]


def _should_render_classic_vcf_rovs(render_plan: dict, ibm_cloud: dict) -> bool:
    """True when the deployment should use the Classic/vSRX handoff layout."""
    topology_variant = str(render_plan.get("topology_variant") or "").lower()
    if topology_variant == "classic-vcf-rovs":
        return True
    pattern = str(render_plan.get("pattern") or "").lower()
    if pattern != "hybrid-classic-vpc":
        return False
    return True


def _tiers_for_vpc(vpc: dict, tier_items: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Ensure template tiers appear even when no extracted item exists yet."""
    tiers = vpc.get("tiers")
    if not isinstance(tiers, list):
        return tier_items
    planned = {str(t).title() for t in tiers}
    result = {key: list(value) for key, value in tier_items.items()}
    for tier in ("Public", "Private", "Management", "Data"):
        if tier in planned and not result.get(tier):
            result[tier] = [{
                "name": f"{tier.lower()} subnet",
                "type": "subnets",
                "subnet_tier": tier,
                "purpose": f"{tier} tier placeholder from selected IBM pattern",
                "notes": "template",
            }]
    return result


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


def _region_name(region: dict) -> str:
    return str(region.get("name") or "").strip()


def _region_label(region: dict, idx: int) -> str:
    name = _region_name(region) or f"Region {idx + 1}"
    lower = f"{name} {region.get('purpose', '')} {region.get('notes', '')}".lower()
    if idx == 0 or "primary" in lower or "dal" in lower or "dallas" in lower:
        role = "Primary Region"
    elif idx == 1 or "dr" in lower or "disaster" in lower or "wdc" in lower or "washington" in lower:
        role = "DR Region"
    else:
        role = "Regional Site"
    return f"{name}\n{role}"


def _vpc_matches_region(vpc: dict, region: dict) -> bool:
    region_name = _region_name(region).lower()
    if region_name and str(vpc.get("region") or "").lower() == region_name:
        return True
    haystack = " ".join(
        str(vpc.get(key) or "").lower()
        for key in ("name", "purpose", "notes", "source")
    )
    aliases = {
        "us-south": ("dal", "dallas"),
        "us-east": ("wdc", "washington"),
    }.get(region_name, ())
    return any(alias in haystack for alias in aliases)


def _items_for_region(items: list[dict], region: dict) -> list[dict]:
    region_name = _region_name(region).lower()
    if not region_name:
        return items
    aliases = {
        "us-south": ("dal", "dallas", "primary"),
        "us-east": ("wdc", "washington", "dr", "disaster"),
    }.get(region_name, ())
    matched: list[dict] = []
    shared: list[dict] = []
    for item in items:
        item_region = str(item.get("region") or "").lower()
        text = " ".join(
            str(item.get(key) or "").lower()
            for key in ("name", "purpose", "notes", "source")
        )
        if item_region == region_name or any(alias in text for alias in aliases):
            matched.append(item)
        elif not item_region:
            shared.append(item)
    return matched or shared


def _regional_tier_items(ibm_cloud: dict, region: dict, *, include_unscoped: bool = True) -> dict[str, list[dict]]:
    tier_map: dict[str, list[dict]] = {
        "Public": [], "Private": [], "Management": [], "Data": [],
    }
    category_to_tier = {
        "ingress": "Public",
        "compute": "Private",
        "data": "Data",
    }
    for cat, default_tier in category_to_tier.items():
        source_items = _items_for_region(ibm_cloud.get(cat, []), region) if include_unscoped else [
            item for item in ibm_cloud.get(cat, [])
            if str(item.get("region") or "").lower() == _region_name(region).lower()
        ]
        for item in source_items:
            tier = item.get("subnet_tier") or default_tier
            if tier in tier_map:
                tier_map[tier].append(item)
    return tier_map


def _fallback_dr_tier_items(ibm_cloud: dict, region: dict) -> dict[str, list[dict]]:
    tier_items = _regional_tier_items(ibm_cloud, region, include_unscoped=False)
    if not tier_items["Private"]:
        tier_items["Private"] = [{
            "name": "DR VSI recovery tier",
            "type": "compute",
            "purpose": "Standby compute capacity for disaster recovery workloads",
        }]
    if not tier_items["Data"]:
        tier_items["Data"] = [{
            "name": "Replicated workload data",
            "type": "data",
            "purpose": "Recovery copy for application and storage data",
        }]
    return tier_items


def _prioritized_foundation_items(items: list[dict], preferred_names: list[str], *, limit: int = 4) -> list[dict]:
    by_name: dict[str, dict] = {}
    for item in items:
        name = _clean_diagram_label(str(item.get("name") or "").strip())
        if not name:
            continue
        lowered = name.lower()
        if any(noise in lowered for noise in ("security is multi", "cloud security is multi")):
            continue
        by_name.setdefault(lowered, {"name": name})

    selected: list[dict] = []
    selected_keys: set[str] = set()
    for preferred in preferred_names:
        key = preferred.lower()
        for name_key, item in by_name.items():
            if key in name_key and name_key not in selected_keys:
                selected.append(item)
                selected_keys.add(name_key)
                break
        if len(selected) >= limit:
            return selected

    for name_key, item in by_name.items():
        if name_key not in selected_keys:
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _component_label(item: dict | str, fallback: str = "Component") -> str:
    if isinstance(item, dict):
        name = str(item.get("name") or item.get("type") or fallback).strip()
        purpose = str(item.get("purpose") or "").strip()
        if purpose and _is_diagram_purpose(purpose):
            return f"{_clean_diagram_label(name)}\n{_clean_diagram_label(purpose)}"
        return _clean_diagram_label(name)
    return _clean_diagram_label(str(item or fallback))


def _category_items(ibm_cloud: dict, category: str, limit: int = 4) -> list[dict]:
    items = ibm_cloud.get(category, [])
    if not isinstance(items, list):
        return []
    result: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("type") or "").strip()
            if name:
                result.append(item)
        elif str(item).strip():
            result.append({"name": str(item).strip(), "type": category})
        if len(result) >= limit:
            break
    return result


def _first_component(ibm_cloud: dict, category: str, fallback: str) -> dict:
    items = _category_items(ibm_cloud, category, 1)
    return items[0] if items else {"name": fallback, "type": category}


def _cidr_suffix(ibm_cloud: dict, name: str) -> str:
    cidr = _find_cidr_for_name(ibm_cloud, name)
    return f"\n{cidr}" if cidr else ""


def _render_vpc_zones(
    builder: DrawioBuilder,
    vpc_id: str,
    vpc_label: str,
    vpc_w: int,
    vpc_h: int,
    tier_items: dict[str, list[dict]],
    az_count: int,
) -> None:
    tier_order = ("Public", "Private", "Data", "Management")
    tier_items = {tier: tier_items.get(tier, []) for tier in tier_order}
    zone_h_each = (vpc_h - 60 - az_count * _SG_M) // max(az_count, 1)
    zone_h_each = max(zone_h_each, 170)
    z_y = 60
    for z in range(1, az_count + 1):
        z_w = vpc_w - 2 * _SG_M
        zone_id = builder.child_ibm_location(
            f"Zone {z}", _SG_M, z_y, z_w, zone_h_each,
            "data--center", COLOR["grey"], vpc_id, dashed=True, icon_size=20,
        )
        visible_tiers = [(tier, items) for tier, items in tier_items.items() if items]
        band_h = (zone_h_each - 44) // max(len(visible_tiers), 1)
        band_h = max(min(band_h, 92), 58)
        band_y_cur = 36
        for tier, items in visible_tiers:
            display_items = _compact_private_compute_items(items) if tier == "Private" else items
            first = items[0]
            subnet_name = (
                first.get("name") if "subnet" in str(first.get("name") or "").lower()
                else f"{vpc_label.split()[0].lower()}-{tier.lower()}-subnet-{z}"
            )
            sub_id = builder.container(
                subnet_name,
                _SG_M, band_y_cur, z_w - 2 * _SG_M, band_h,
                fill=COLOR.get(tier, "#f4f4f4"),
                stroke=COLOR["az_stroke"], font_size=9,
                parent=zone_id,
            )
            if z == 1:
                tile_w = max((z_w - 2 * _SG_M - 18) // 2, 150)
                for idx, item in enumerate(display_items[:3]):
                    shape = _stencil_shape(item.get("name") or "") or {
                        "Public": "load-balancer--vpc",
                        "Private": "ibm-cloud--virtual-server-vpc",
                        "Data": "object-storage",
                        "Management": "cloud--monitoring",
                    }.get(tier, "cloud-services")
                    if shape:
                        tx = _SG_M + 4 + (idx % 2) * (tile_w + 10)
                        ty = 12 + (idx // 2) * 32
                        builder.child_service_tile(
                            item.get("name") or tier,
                            tx, ty, tile_w, sub_id, shape, d=22,
                        )
                hidden_count = max(len(display_items) - 3, 0)
                if hidden_count:
                    builder.container(
                        f"+{hidden_count} more",
                        z_w - 92, 12, 72, 24,
                        fill="#ffffff", stroke=COLOR["az_stroke"], font_size=9,
                        font_style=0, parent=sub_id,
                    )
            band_y_cur += band_h + _SG_M
        z_y += zone_h_each + _SG_M


def _find_cidr_for_name(ibm_cloud: dict, name_token: str) -> str:
    token = name_token.lower().strip()
    if not token:
        return ""
    for category in ("vpcs", "subnets"):
        for item in ibm_cloud.get(category, []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").lower().strip()
            cidr = str(item.get("cidr") or "")
            if name == token and cidr:
                return cidr
    for category in ("vpcs", "subnets"):
        for item in ibm_cloud.get(category, []):
            if not isinstance(item, dict):
                continue
            haystack = " ".join(str(item.get(key) or "") for key in ("name", "purpose")).lower()
            cidr = str(item.get("cidr") or "")
            if token in haystack and cidr:
                return cidr
            match = re.search(r'\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b', haystack)
            if token in haystack and match:
                return match.group(0)
    for category in ("vpcs", "subnets"):
        for item in ibm_cloud.get(category, []):
            if not isinstance(item, dict):
                continue
            haystack = " ".join(str(item.get(key) or "") for key in ("name", "purpose", "notes")).lower()
            cidr = str(item.get("cidr") or "")
            if token in haystack and cidr:
                return cidr
            match = re.search(r'\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b', haystack)
            if token in haystack and match:
                return match.group(0)
    return ""


def _label_with_cidr(label: str, cidr: str) -> str:
    label = _clean_diagram_label(label)
    cidr = str(cidr or "").strip()
    if cidr and cidr not in label:
        return f"{label}\n{cidr}"
    return label


def _customer_name_from_model(project: dict, ibm_cloud: dict) -> str:
    for key in ("customer", "client", "account", "company"):
        value = str(project.get(key) or "").strip()
        if value:
            return value
    haystacks: list[str] = []
    for category in ("vpcs", "subnets", "connectivity", "compute", "regions"):
        for item in ibm_cloud.get(category, []):
            if isinstance(item, dict):
                haystacks.append(" ".join(str(item.get(key) or "") for key in ("notes", "purpose")))
    text = "\n".join(haystacks)
    possessive = re.search(r"\b([A-Z][A-Z0-9&.-]{1,})'s\b", text)
    if possessive:
        return possessive.group(1)
    return ""


def _render_classic_vcf_rovs_deployment(builder: DrawioBuilder, project: dict, ibm_cloud: dict, render_plan: dict) -> None:
    """Render Classic/vSRX to VPC Transit Gateway topologies from the model."""
    _render_title(builder, project, "deployment")

    left = _BASE_X
    top = _BASE_Y
    gap = 28
    planned_vpcs = _vpcs_from_render_plan(render_plan, ibm_cloud)
    existing_networks = [vpc for vpc in planned_vpcs if "classic" in str(vpc.get("purpose", "")).lower() or "vcf" in str(vpc.get("name", "")).lower()]
    vpc_targets = [vpc for vpc in planned_vpcs if vpc not in existing_networks] or planned_vpcs[-1:]
    connectivity_items = _category_items(ibm_cloud, "connectivity", 4)
    direct_link = next((item for item in connectivity_items if "direct" in str(item.get("name", "")).lower()), _first_component(ibm_cloud, "connectivity", str(render_plan.get("connectivity_label") or "Private connectivity")))
    router = next((item for item in connectivity_items if any(token in str(item.get("name", "")).lower() for token in ("vsrx", "router", "firewall"))), {"name": "Classic routing / firewall"})
    tgw_item = next((item for item in connectivity_items if "transit" in str(item.get("name", "")).lower()), {"name": "Transit Gateway"})
    compute = _first_component(ibm_cloud, "compute", "Workload cluster")
    customer_name = _customer_name_from_model(project, ibm_cloud)
    customer_prefix = f"{customer_name} " if customer_name else ""

    enterprise = builder.ibm_location(
        f"{customer_prefix}Enterprise / On-Premises", left, top, 250, 360,
        shape="network--enterprise", stroke_color=COLOR["grey"],
    )
    users = builder.ibm_actor(f"{customer_prefix}users" if customer_name else "Users", left + 24, top + 70, "user", d=40)
    wan = builder.ibm_actor(f"{customer_prefix}WAN" if customer_name else "Enterprise WAN", left + 24, top + 170, "enterprise", d=40)

    conn_x = left + 250 + gap
    dl_label = _clean_diagram_label(str(direct_link.get("name") or "Private connectivity"))
    connectivity = builder.ibm_location(
        f"{dl_label} Connectivity", conn_x, top, 230, 360,
        shape="arrows--horizontal", stroke_color=COLOR["network"],
    )
    dl = builder.ibm_node(dl_label, conn_x + 40, top + 130, _stencil_shape(dl_label) or "ibm-cloud--direct-link-2--connect", d=44)

    classic_x = conn_x + 230 + gap
    classic = builder.ibm_location(
        "IBM Cloud Classic / Existing Network", classic_x, top, 400, 360,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )
    router_label = _component_label(router, "Classic routing / firewall")
    vsrx = builder.ibm_node(router_label, classic_x + 34, top + 70, _stencil_shape(router_label) or "ibm-cloud--security-groups-for-vpc", d=44)
    first_network = existing_networks[0] if existing_networks else {"name": "Existing Network", "purpose": "Customer network routed through Classic"}
    second_network = existing_networks[1] if len(existing_networks) > 1 else {"name": "Additional Existing Network", "purpose": "Additional routed network"}
    prod = builder.box(
        _label_with_cidr(_component_label(first_network, "Existing Network"), _find_cidr_for_name(ibm_cloud, str(first_network.get("name") or ""))),
        classic_x + 34, top + 150, 320, 70,
        fill=COLOR["Private"], stroke=COLOR["az_stroke"], font_size=11,
    )
    test = builder.box(
        _label_with_cidr(_component_label(second_network, "Additional Existing Network"), _find_cidr_for_name(ibm_cloud, str(second_network.get("name") or ""))),
        classic_x + 34, top + 245, 320, 70,
        fill="#E8DAFF", stroke=COLOR["az_stroke"], font_size=11,
    )

    tgw_x = classic_x + 400 + gap
    tgw_box = builder.box(
        "Classic routed handoff\nvia transit gateway",
        tgw_x, top + 95, 180, 155,
        fill="#FFFFFF", stroke=COLOR["network"], font_size=11,
    )
    tgw_label = _clean_diagram_label(str(tgw_item.get("name") or "Transit Gateway"))
    tgw = builder.transit_gateway(tgw_label, tgw_x + 64, top + 160)

    account_x = tgw_x + 180 + gap
    account_w = 790
    account = builder.ibm_location(
        "IBM Cloud VPC", account_x, top, account_w, 560,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )
    target_region = str((vpc_targets[0] if vpc_targets else {}).get("region") or "")
    if not target_region and ibm_cloud.get("regions"):
        target_region = str((ibm_cloud.get("regions") or [{}])[0].get("name") or "")
    region = builder.child_ibm_location(
        target_region or "Region",
        24, 56, account_w - 48, 470,
        "location", COLOR["grey"], account,
    )
    target_vpc = vpc_targets[0] if vpc_targets else {"name": "Workload VPC"}
    vpc = builder.child_ibm_location(
        _label_with_cidr(_component_label(target_vpc, "Workload VPC"), _find_cidr_for_name(ibm_cloud, str(target_vpc.get("name") or ""))),
        36, 70, account_w - 72, 380,
        "ibm-cloud--vpc", COLOR["network"], region,
    )

    subnets = [
        item for item in ibm_cloud.get("subnets", [])
        if isinstance(item, dict)
        and (
            str(item.get("vpc") or "").lower() == str(target_vpc.get("name") or "").lower()
            or str(target_vpc.get("name") or "").lower() in str(item.get("notes") or item.get("name") or "").lower()
            or all(
                token in str(item.get("name") or item.get("notes") or "").lower()
                for token in re.findall(r"[a-z0-9]+", str(target_vpc.get("name") or "").lower())
                if token not in {"vpc", "network", "environment"}
            )
        )
    ]
    if not subnets:
        subnets = [{"name": "Private subnet", "zone": "Zone 1", "cidr": ""}]
    subnets = sorted(subnets, key=lambda item: str(item.get("zone") or item.get("name") or ""))
    zone_y = 62
    cluster_id = ""
    for index, subnet in enumerate(subnets[:3]):
        zone = str(subnet.get("zone") or f"us-east-{index + 1}")
        cidr = str(subnet.get("cidr") or "")
        zone_id = builder.child_ibm_location(
            zone, 18, zone_y, account_w - 108, 74,
            "data--center", COLOR["grey"], vpc, dashed=True, icon_size=20,
        )
        subnet_id = builder.container(
            f"{subnet.get('name') or 'Private subnet'}\n{cidr}".strip(),
            14, 34, account_w - 140, 32,
            fill=COLOR["Private"], stroke=COLOR["az_stroke"], font_size=10,
            parent=zone_id,
        )
        if zone == "us-east-3" or index == len(subnets[:3]) - 1:
            cluster_id = builder.child_ibm_node(
                _component_label(compute, "Workload cluster"), 26, 2,
                _stencil_shape(str(compute.get("name") or "")) or "ibm-cloud--virtual-server-vpc", subnet_id, d=28,
            )
        zone_y += 90

    builder.edge(users, dl, "user / management traffic")
    builder.edge(wan, dl, "private WAN")
    builder.edge(dl, vsrx, "private connectivity terminates")
    builder.edge(vsrx, prod, "routes network")
    builder.edge(vsrx, test, "routes network")
    builder.edge(vsrx, tgw_box, "Classic routed handoff")
    builder.edge(tgw_box, tgw, "")
    builder.edge(tgw, vpc, "transit attachment")
    if cluster_id:
        builder.edge(vpc, cluster_id, "private VPC routing", dashed=True)

    builder.box(
        "Seller validation: confirm BGP/route tables, firewall policy zones, transit attachment details, CIDR ownership, and whether listed zones/subnets are active, reserved, or future expansion.",
        account_x, top + 590, account_w, 66,
        fill="#FFF1F1", stroke=COLOR["security"], font_size=11,
        align="left", vertical_align="middle",
    )


def _render_multi_region_deployment(
    builder: DrawioBuilder,
    ibm_cloud: dict,
    render_plan: dict,
    regions_data: list[dict],
    vpcs_data: list[dict],
    *,
    has_on_prem: bool,
    has_tgw: bool,
    has_powervs: bool,
    az_count: int,
) -> None:
    ent_w = 230
    conn_w = 170
    gap = 20
    cursor_x = _BASE_X
    users_node: str | None = None
    on_prem_node: str | None = None

    if has_on_prem:
        builder.ibm_location(
            "Enterprise Sites", cursor_x, _BASE_Y, ent_w, 460,
            shape="network--enterprise", stroke_color=COLOR["grey"],
        )
        users_node = builder.ibm_actor("Clinicians / Centers", cursor_x + 20, _BASE_Y + 70, "user", d=40)
        on_prem_node = builder.ibm_actor("Enterprise WAN", cursor_x + 20, _BASE_Y + 180, "enterprise", d=40)
        cursor_x += ent_w + gap

        conn_container = builder.ibm_location(
            "HA Direct Link", cursor_x, _BASE_Y, conn_w, 460,
            shape="arrows--horizontal", stroke_color=COLOR["network"],
        )
        if users_node:
            builder.edge(users_node, conn_container, "intake/retrieval")
        if on_prem_node:
            builder.edge(on_prem_node, conn_container, "")
        conn_label = str(render_plan.get("connectivity_label") or "HA Direct Link")
        builder.ibm_node(
            conn_label, cursor_x + 20, _BASE_Y + 90,
            _stencil_shape(conn_label) or "ibm-cloud--direct-link-2--connect", d=40,
        )
        cursor_x += conn_w + gap
    else:
        users_node = builder.ibm_actor("Users / Clients", cursor_x + 10, _BASE_Y + 80, "user", d=40)
        cursor_x += 90 + gap

    account_w = 1500
    account_h = 920
    ibm_account = builder.ibm_location(
        "IBM Cloud Account", cursor_x, _BASE_Y, account_w, account_h,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )
    if users_node and not has_on_prem:
        builder.edge(users_node, ibm_account, "HTTPS/API")

    displayed_regions = regions_data[:2]
    region_w = 710
    region_h = 585
    region_ids: list[str] = []
    vpc_ids: list[str] = []

    for idx, region in enumerate(displayed_regions):
        rx = 20 + idx * (region_w + gap)
        region_id = builder.child_ibm_location(
            _region_label(region, idx), rx, 60, region_w, region_h,
            "location", COLOR["grey"], ibm_account,
        )
        region_ids.append(region_id)

        region_vpcs = [v for v in vpcs_data if _vpc_matches_region(v, region)]
        if not region_vpcs and idx < len(vpcs_data):
            region_vpcs = [vpcs_data[idx]]
        if not region_vpcs:
            region_vpcs = [{"name": "Primary VPC" if idx == 0 else "DR VPC", "purpose": ""}]

        tgw_id: str | None = None
        if has_tgw:
            tgw_id = builder.child_ibm_node(
                "Transit Gateway", 20, 45, "ibm-cloud--transit-gateway", region_id, d=36,
            )

        vpc = region_vpcs[0]
        vpc_label = _clean_diagram_label(str(vpc.get("name") or f"VPC {idx + 1}"))
        if vpc.get("purpose") and _is_diagram_purpose(str(vpc.get("purpose"))):
            vpc_label += f"\n{_clean_diagram_label(str(vpc['purpose']))}"
        vpc_id = builder.child_ibm_location(
            vpc_label, 30, 95, region_w - 60, 380,
            "ibm-cloud--vpc", COLOR["network"], region_id,
        )
        vpc_ids.append(vpc_id)
        if tgw_id:
            builder.edge(tgw_id, vpc_id, "")

        if idx == 0:
            tier_items = _tiers_for_vpc(vpc, _regional_tier_items(ibm_cloud, region, include_unscoped=True))
        else:
            tier_items = _tiers_for_vpc(vpc, _fallback_dr_tier_items(ibm_cloud, region))
        _render_vpc_zones(builder, vpc_id, vpc_label, region_w - 60, 380, tier_items, az_count)

        if has_powervs:
            power_id = builder.child_ibm_location(
                "PowerVS Workspace", 30, 490, region_w - 60, 70,
                "ibm--power-vs", COLOR["compute"], region_id, dashed=True,
            )
            builder.child_service_tile("PowerVS servers", 18, 32, region_w - 120, power_id, "ibm--power-vs", d=20)
            builder.edge(vpc_id, power_id, "", dashed=True)

    if len(region_ids) > 1:
        builder.edge(region_ids[0], region_ids[1], "", dashed=True)

    foundation_label = str(
        render_plan.get("foundation_label")
        or "Foundation: PowerVS with VPC landing zone + security/observability foundation + regional DR extension"
    )
    svc_container = builder.child_ibm_location(
        "Shared Services / Compliance Foundation", 20, 665, 1460, 225,
        "cloud-services", COLOR["data"], ibm_account,
    )
    builder.container(
        foundation_label,
        18, 42, 1422, 34,
        fill="#f4f4f4", stroke=COLOR["grey"], font_size=12,
        font_style=1, parent=svc_container,
    )

    foundation_groups: list[tuple[str, str]] = [
        (
            "Security & Compliance",
            "SCC evidence collection\nKey Protect / HPCS\nSecrets Manager\nVirtual Private Endpoints",
        ),
        (
            "Operations Evidence",
            "Activity Tracker\nVPC Flow Logs\nMonitoring and Logging\nDR evidence / runbook",
        ),
        (
            "Shared Data Services",
            "Cloud Object Storage archive\nNFS File Storage\nCross-region replication\nPrivate service access",
        ),
    ]
    group_w = 456
    for group_idx, (group_label, summary) in enumerate(foundation_groups):
        gx = 18 + group_idx * (group_w + 18)
        builder.container(
            group_label, gx, 92, group_w, 28,
            fill="#f4f4f4", stroke=COLOR["grey"], font_size=12,
            font_style=1, parent=svc_container,
        )
        builder.container(
            summary,
            gx + 10, 132, group_w - 20, 78,
            fill="#ffffff", stroke=COLOR["grey"], font_size=12,
            font_style=0, parent=svc_container,
        )


def _render_executive_overview(builder: DrawioBuilder, project: dict, ibm_cloud: dict, render_plan: dict | None = None) -> None:
    """Render a seller-friendly first page from the active architecture model."""
    render_plan = render_plan or {}
    _render_title(builder, project, "executive overview")

    left = 90
    top = 130
    gap = 32
    enterprise_w = 260
    connectivity_w = 230
    cloud_x = left + enterprise_w + gap + connectivity_w + gap
    cloud_y = top
    cloud_w = 1440
    cloud_h = 650

    has_on_prem = _plan_bool(
        render_plan,
        "has_on_prem",
        any("direct link" in str(item.get("name", "")).lower() or "vpn" in str(item.get("name", "")).lower()
            for item in ibm_cloud.get("connectivity", []) if isinstance(item, dict)),
    )
    has_tgw = _plan_bool(render_plan, "has_tgw", _has_transit_gateway(ibm_cloud))
    has_powervs = _plan_bool(render_plan, "has_powervs", _has_powervs(ibm_cloud))
    planned_vpcs = _vpcs_from_render_plan(render_plan, ibm_cloud)
    regions = ibm_cloud.get("regions") or [{"name": "Region TBD"}]
    connectivity_items = _category_items(ibm_cloud, "connectivity", 4)
    planned_shared = render_plan.get("shared_services", [])
    if not isinstance(planned_shared, list):
        planned_shared = [planned_shared] if str(planned_shared).strip() else []
    shared_services = [
        *[{"name": str(name), "type": "shared_services"} for name in planned_shared if str(name).strip()],
        *_category_items(ibm_cloud, "security", 3),
        *_category_items(ibm_cloud, "observability", 3),
        *_category_items(ibm_cloud, "data", 3),
    ]

    enterprise = builder.ibm_location(
        "Enterprise / External", left, top + 80, enterprise_w, 260,
        shape="network--enterprise", stroke_color=COLOR["grey"],
    )
    users = builder.ibm_actor("Users / Clients", left + 32, top + 150, "user", d=44)
    external = builder.ibm_actor("Enterprise Network", left + 32, top + 245, "enterprise", d=44)

    conn_x = left + enterprise_w + gap
    connectivity = builder.ibm_location(
        "Connectivity", conn_x, top + 80, connectivity_w, 260,
        shape="arrows--horizontal", stroke_color=COLOR["network"],
    )
    if connectivity_items:
        for index, item in enumerate(connectivity_items[:3]):
            label = _clean_diagram_label(str(item.get("name") or "Connectivity"))
            builder.ibm_node(label, conn_x + 34, top + 130 + index * 62, _stencil_shape(label) or "arrows--horizontal", d=40)
    else:
        dl_label = str(render_plan.get("connectivity_label") or "Connectivity")
        builder.ibm_node(dl_label, conn_x + 34, top + 175, _stencil_shape(dl_label) or "arrows--horizontal", d=44)

    cloud = builder.ibm_location(
        "IBM Cloud Architecture", cloud_x, cloud_y, cloud_w, cloud_h,
        shape="ibm-cloud", stroke_color=COLOR["network"], stroke_width=2,
    )

    column_count = max(1, min(len(planned_vpcs) or len(regions), 3))
    region_w = (cloud_w - 80 - (column_count - 1) * 34) // column_count
    region_h = 355
    vpc_ids: list[str] = []
    for index in range(column_count):
        region = regions[min(index, len(regions) - 1)] if regions else {"name": "Region TBD"}
        vpc = planned_vpcs[index] if index < len(planned_vpcs) else (planned_vpcs[0] if planned_vpcs else {"name": "VPC"})
        rx = 40 + index * (region_w + 34)
        region_id = builder.child_ibm_location(
            _label(region, f"Region {index + 1}"),
            rx, 70, region_w, region_h,
            "location", COLOR["grey"], cloud,
        )
        vpc_label = _component_label(vpc, "VPC") + _cidr_suffix(ibm_cloud, str(vpc.get("name") or ""))
        vpc_id = builder.child_ibm_location(
            vpc_label,
            30, 90, region_w - 60, 160,
            "ibm-cloud--vpc", COLOR["network"], region_id,
        )
        vpc_ids.append(vpc_id)
        tier_names = [str(tier) for tier in vpc.get("tiers", []) if str(tier).strip()] if isinstance(vpc, dict) else []
        if not tier_names:
            tier_names = [item["name"] for item in _category_items(ibm_cloud, "compute", 2)] or ["Workload tier"]
        builder.container(
            "Planned tiers / workloads",
            44, 60, region_w - 112, 28,
            fill="#f4f4f4", stroke=COLOR["grey"], font_size=11,
            parent=vpc_id,
        )
        for tier_index, tier_name in enumerate(tier_names[:3]):
            builder.child_service_tile(
                _clean_diagram_label(tier_name),
                54 + tier_index * max(145, (region_w - 150) // 3),
                102,
                max(120, (region_w - 185) // 3),
                vpc_id,
                _stencil_shape(tier_name) or "ibm-cloud--subnets",
                d=20,
            )

        if has_tgw:
            tgw = builder.child_ibm_node("Transit Gateway", 36, 270, "ibm-cloud--transit-gateway", region_id, d=34)
            builder.edge(tgw, vpc_id, "")

    if has_powervs and vpc_ids:
        pwr = builder.child_ibm_location("PowerVS Workspace", 40, 445, 330, 86, "ibm--power-vs", COLOR["compute"], cloud, dashed=True)
        builder.child_service_tile("PowerVS workloads", 18, 36, 250, pwr, "ibm--power-vs", d=20)
        builder.edge(vpc_ids[0], pwr, "cloud connection", dashed=True)

    foundation = builder.child_ibm_location(
        "Shared Services / Foundation",
        40, 455, cloud_w - 80, 155,
        "cloud-services", COLOR["data"], cloud,
    )
    pattern_name = str(render_plan.get("pattern_name") or render_plan.get("pattern") or best_pattern({"ibm_cloud": ibm_cloud}).get("name") or "IBM pattern to confirm")
    service_names = []
    for item in shared_services:
        name = str(item.get("name") or "").strip()
        if name and name not in service_names:
            service_names.append(name)
    foundation_text = (
        f"IBM Think pattern: {_clean_diagram_label(pattern_name)}\n"
        f"Shared services: {', '.join(service_names[:8]) if service_names else 'To confirm from requirements'}\n"
        f"Seller validation: {render_plan.get('pattern_reason') or 'Confirm routing, security boundaries, resilience, and operations ownership.'}"
    )
    builder.container(
        foundation_text, 28, 54, cloud_w - 136, 78,
        fill="#ffffff", stroke=COLOR["grey"], font_size=13,
        font_style=0, parent=foundation,
    )

    builder.edge(users, connectivity, "user traffic")
    if has_on_prem:
        builder.edge(external, connectivity, "private connectivity")
    else:
        builder.edge(external, connectivity, "")
    builder.edge(connectivity, cloud, "")
    if len(vpc_ids) > 1:
        for source, target in zip(vpc_ids, vpc_ids[1:]):
            builder.edge(source, target, "planned routing", dashed=True)


def _render_deployment(builder: DrawioBuilder, project: dict, ibm_cloud: dict, render_plan: dict | None = None) -> None:  # noqa: PLR0912, PLR0915
    """Render a deployment diagram driven entirely by the extracted architecture model.

    No topology is assumed.  Every structural element (on-prem block, VPC count,
    AZ count, node types) is derived from the ibm_cloud dict.
    """
    render_plan = render_plan or {}
    if _should_render_classic_vcf_rovs(render_plan, ibm_cloud):
        _render_classic_vcf_rovs_deployment(builder, project, ibm_cloud, render_plan)
        return

    _render_title(builder, project, "deployment")

    regions_data   = ibm_cloud.get("regions")          or [{"name": "Region TBD"}]
    conn_items     = ibm_cloud.get("connectivity")      or []
    vpcs_data      = _vpcs_from_render_plan(render_plan, ibm_cloud)
    data_items     = ibm_cloud.get("data")              or []
    security_items = ibm_cloud.get("security")          or []
    obs_items      = ibm_cloud.get("observability")     or []
    private_eps    = ibm_cloud.get("private_endpoints") or []

    # ── Pattern detection — from extracted data, no assumptions ──────────
    detected_on_prem = any(
        kw in (c.get("name") or "").lower()
        for c in conn_items
        for kw in ("direct link", "vpn", "direct-link")
    )
    has_on_prem = _plan_bool(render_plan, "has_on_prem", detected_on_prem)
    has_tgw     = _plan_bool(render_plan, "has_tgw", _has_transit_gateway(ibm_cloud))
    has_powervs = _plan_bool(render_plan, "has_powervs", _has_powervs(ibm_cloud))
    has_dr      = _plan_bool(render_plan, "has_dr", len(regions_data) > 1)
    az_count    = int(render_plan.get("az_count") or _az_count_from_data(ibm_cloud))
    if str(render_plan.get("pattern") or "").lower() == "mzr":
        az_count = max(az_count, 3)
    vpc_count   = len(vpcs_data)

    region_names = {_region_name(region).lower() for region in regions_data if _region_name(region)}
    if has_dr and len(region_names) > 1 and any(
        _region_name(region).lower() == str(vpc.get("region") or "").lower()
        or _vpc_matches_region(vpc, region)
        for region in regions_data
        for vpc in vpcs_data
    ):
        _render_multi_region_deployment(
            builder,
            ibm_cloud,
            render_plan,
            regions_data,
            vpcs_data,
            has_on_prem=has_on_prem,
            has_tgw=has_tgw,
            has_powervs=has_powervs,
            az_count=az_count,
        )
        return

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
        if not non_tgw and render_plan.get("connectivity_label"):
            non_tgw = [{"name": str(render_plan.get("connectivity_label")), "type": "connectivity"}]
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
        vpc_label = _clean_diagram_label(vpc.get("name") or f"VPC {v_idx + 1}")
        if vpc.get("purpose") and _is_diagram_purpose(str(vpc.get("purpose"))):
            vpc_label += f"\n{_clean_diagram_label(str(vpc['purpose']))}"

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
        tier_items = _tiers_for_vpc(vpc, tier_items)

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
                        item_name = _clean_diagram_label(item.get("name") or tier)
                        shape = _stencil_shape(item_name)
                        if shape:
                            builder.child_ibm_node(
                                item_name,
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
    shared_services = render_plan.get("shared_services")
    if isinstance(shared_services, list) and shared_services:
        planned_services = [
            {"name": str(name), "type": "shared_services", "source": "render_plan"}
            for name in shared_services
            if str(name).strip()
        ]
        svc_items.append((planned_services[:6], "cloud-services", "Pattern Services"))
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
            name = sitem.get("name") if isinstance(sitem, dict) else sitem
            name = _clean_diagram_label(name or group_label)
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

def _names_for_category(ibm_cloud: dict, category: str, limit: int = 4) -> list[str]:
    items = ibm_cloud.get(category, [])
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("type") or "").strip()
        else:
            name = str(item).strip()
        if name and name not in names:
            names.append(name)
    return names[:limit]


def _decision_rows(architecture: dict) -> list[tuple[str, str, str]]:
    project = architecture.get("project", {}) if isinstance(architecture, dict) else {}
    ibm_cloud = architecture.get("ibm_cloud", {}) if isinstance(architecture, dict) else {}
    render_plan = architecture.get("render_plan", {}) if isinstance(architecture, dict) else {}
    questions = architecture.get("questions", {}) if isinstance(architecture, dict) else {}
    quality = architecture.get("quality", {}) if isinstance(architecture, dict) else {}
    review = quality.get("lastReview", {}) if isinstance(quality, dict) else {}
    pattern = best_pattern(architecture)

    selected_pattern = str(render_plan.get("pattern") or pattern.get("id") or "unclassified")
    pattern_name = str(render_plan.get("pattern_name") or pattern.get("name") or "IBM Think pattern to confirm")
    pattern_score = pattern.get("score")
    score_label = f"{pattern_score}/100 match" if pattern_score is not None else "not scored"

    regions = _names_for_category(ibm_cloud, "regions", 3)
    vpcs = _names_for_category(ibm_cloud, "vpcs", 4)
    connectivity = _names_for_category(ibm_cloud, "connectivity", 4)
    security = _names_for_category(ibm_cloud, "security", 4)
    observability = _names_for_category(ibm_cloud, "observability", 4)
    data = _names_for_category(ibm_cloud, "data", 4)

    open_questions = questions.get("open", []) if isinstance(questions, dict) else []
    open_count = len(open_questions) if isinstance(open_questions, list) else 0
    answered = questions.get("answered", []) if isinstance(questions, dict) else []
    answered_count = len(answered) if isinstance(answered, list) else 0

    rows = [
        ("Customer / workload", str(project.get("name") or "Customer architecture"), "Confirm business owner, workload criticality, and environment."),
        ("IBM foundation", f"{pattern_name} ({selected_pattern}, {score_label})", "Use the IBM Think Architecture pattern as the deployment baseline."),
        ("Regions", ", ".join(regions) if regions else "Primary region inferred", "Confirm data residency, latency, and DR location constraints."),
        ("Network topology", ", ".join(vpcs) if vpcs else "VPC landing zone inferred", "Confirm VPC boundaries, subnet tiers, and routing ownership."),
        ("Hybrid connectivity", ", ".join(connectivity) if connectivity else "No private connectivity captured", "Confirm Direct Link, VPN, BGP, and firewall handoff details."),
        ("Security foundation", ", ".join(security) if security else "SCC, key management, and secrets handling to confirm", "Confirm encryption, IAM, evidence, and compliance controls."),
        ("Operations evidence", ", ".join(observability) if observability else "Activity Tracker, flow logs, monitoring, and logging to confirm", "Confirm audit, retention, alerting, and runbook ownership."),
        ("Data services", ", ".join(data) if data else "Data tier and backup approach to confirm", "Confirm RPO/RTO, replication, backup immutability, and restore tests."),
        ("Question status", f"{answered_count} answered, {open_count} open", "Resolve open questions before treating this as final architecture."),
        ("Diagram quality", f"{review.get('score', 'Not analyzed')} {review.get('status', '')}".strip(), "Run quality analyzer after every model or Bob/MCP diagram edit."),
    ]
    return rows


def _render_assumptions_decisions(builder: DrawioBuilder, project: dict, architecture: dict) -> None:
    _render_title(builder, project, "assumptions and decisions")
    ibm_cloud = architecture.get("ibm_cloud", {}) if isinstance(architecture, dict) else {}
    top_patterns = match_patterns(architecture, top_n=3)

    x = 80
    y = 170
    w = 1460
    builder.box(
        "IBM Architecture Pattern Traceability",
        x, y, w, 44,
        fill="#EDF5FF",
        stroke=COLOR["network"],
        font_size=15,
        font_style=1,
        align="left",
    )

    row_y = y + 64
    for index, pattern in enumerate(top_patterns):
        label = f"{index + 1}. {pattern['name']} - {pattern['score']}/100"
        matched = ", ".join(str(item).replace("✓ ", "").replace("○ ", "").replace("⚠ ", "") for item in pattern.get("matched", [])[:3])
        missing = ", ".join(str(item).replace("✓ ", "").replace("○ ", "").replace("⚠ ", "") for item in pattern.get("missing", [])[:2])
        body = f"{label}\nMatched: {matched or 'None yet'}\nReview: {missing or 'No material gaps'}"
        builder.box(
            body,
            x + index * 490, row_y, 460, 120,
            fill="#FFFFFF",
            stroke=COLOR["grey"],
            font_size=11,
            align="left",
            vertical_align="top",
        )

    builder.box(
        "Assumptions, Decisions, And Seller Follow-Up",
        x, row_y + 160, w, 44,
        fill="#F4F4F4",
        stroke=COLOR["grey"],
        font_size=15,
        font_style=1,
        align="left",
    )

    table_y = row_y + 224
    col_w = [260, 520, 620]
    headers = ["Area", "Current Design Position", "Seller Validation"]
    cursor_x = x
    for idx, header in enumerate(headers):
        builder.box(header, cursor_x, table_y, col_w[idx], 36, fill="#E0E0E0", stroke=COLOR["grey"], font_size=12, font_style=1)
        cursor_x += col_w[idx]

    for row_index, row in enumerate(_decision_rows(architecture)):
        cursor_x = x
        row_top = table_y + 36 + row_index * 58
        for col_index, value in enumerate(row):
            builder.box(
                value,
                cursor_x, row_top, col_w[col_index], 58,
                fill="#FFFFFF",
                stroke="#C6C6C6",
                font_size=10,
                align="left",
                vertical_align="top",
            )
            cursor_x += col_w[col_index]

    service_count = sum(len(value) for value in ibm_cloud.values() if isinstance(value, list))
    footer = (
        f"Traceability source: IBM Think Architecture Patterns ({PATTERN_SOURCE_URL}). "
        f"Architecture model contains {service_count} IBM Cloud component entries. "
        "Treat analyzer-added components as recommendations until customer-confirmed."
    )
    builder.box(
        footer,
        x, table_y + 36 + len(_decision_rows(architecture)) * 58 + 28, w, 58,
        fill="#FFF1F1",
        stroke=COLOR["security"],
        font_size=11,
        align="left",
        vertical_align="middle",
    )


PATTERN_SOURCE_URL = "https://www.ibm.com/think/architectures/patterns"

DIAGRAM_PAGE_NAMES = {
    "executive":  "Executive Overview",
    "context":    "Context",
    "logical":    "Logical Architecture",
    "deployment": "Deployment",
    "decisions":  "Assumptions & Decisions",
}


def render_drawio(architecture: dict, *, diagram_type: str, style_memory: dict | None = None) -> str:
    """Return Draw.io XML for *architecture* using IBM Cloud stencil shapes.

    Layout conventions are derived from the LLM Architecture MD Files:
      - 00-style-guide.md     → IBM visual language, color palette
      - 01-context-diagram.md → context diagram layout
      - 02-logical-architecture.md → logical diagram layout
      - 03-deployment-architecture.md → deployment diagram layout

    Supported diagram_type values: "executive", "context", "logical",
    "deployment", "decisions".
    """
    project = architecture.get("project", {})
    ibm_cloud = architecture.get("ibm_cloud", {})
    render_plan = architecture.get("render_plan", {})
    builder = DrawioBuilder(_renderer_style_from_memory(style_memory))

    if diagram_type == "executive":
        _render_executive_overview(builder, project, ibm_cloud, render_plan=render_plan)
    elif diagram_type == "deployment":
        _render_deployment(builder, project, ibm_cloud, render_plan=render_plan)
    elif diagram_type == "logical":
        _render_logical(builder, project, ibm_cloud, render_plan=render_plan)
    elif diagram_type == "decisions":
        _render_assumptions_decisions(builder, project, architecture)
    else:
        _render_context(builder, project, ibm_cloud, render_plan=render_plan)

    return builder.render(diagram_name=DIAGRAM_PAGE_NAMES.get(diagram_type, "Context"))


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


def render_all_diagrams(architecture: dict, *, style_memory: dict | None = None) -> dict[str, str]:
    """Return all diagram types as a dict keyed by type name.

    Returns::

        {
            "context":    "<mxGraphModel>...</mxGraphModel>",
            "logical":    "<mxGraphModel>...</mxGraphModel>",
            "deployment": "<mxGraphModel>...</mxGraphModel>",
        }

    Suitable for multi-page imports via the MCP ``import-diagram`` tool.
    """
    return {
        "executive":  render_drawio(architecture, diagram_type="executive", style_memory=style_memory),
        "context":    render_drawio(architecture, diagram_type="context", style_memory=style_memory),
        "logical":    render_drawio(architecture, diagram_type="logical", style_memory=style_memory),
        "deployment": render_drawio(architecture, diagram_type="deployment", style_memory=style_memory),
        "decisions":  render_drawio(architecture, diagram_type="decisions", style_memory=style_memory),
    }


def render_multipage_drawio(architecture: dict, *, style_memory: dict | None = None) -> str:
    """Return a single multi-page Draw.io XML document with all diagram types.

    Each diagram type becomes a named page (``<diagram>`` element).  The result
    can be saved as a ``.drawio`` file and opened in Draw.io desktop or
    diagrams.net without the MCP server.
    """
    diagrams_xml: list[str] = []
    for dtype, page_name in DIAGRAM_PAGE_NAMES.items():
        inner_xml = render_drawio(architecture, diagram_type=dtype, style_memory=style_memory)
        # Strip the outer <?xml ...?><mxGraphModel> wrapper — we need just the
        # <root>...</root> content to embed as a named page.
        import re as _re
        root_match = _re.search(r"<root>(.*?)</root>", inner_xml, _re.DOTALL)
        root_content = root_match.group(1) if root_match else inner_xml
        # Escape for CDATA embedding
        diagrams_xml.append(
            f'  <diagram name="{escape(page_name)}">'
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
