"""IBM Think Architecture Pattern Matcher.

Scores the extracted architecture model against every known IBM Cloud reference
architecture pattern and returns a ranked list with match evidence.

Reference: https://www.ibm.com/think/architectures/patterns

Each pattern is defined as a set of *signals* — named boolean predicates over
the ibm_cloud model.  Signals are weighted by importance.  The final score is
the sum of matched signal weights divided by the sum of all signal weights,
expressed as a percentage (0–100).

No LLM required — all scoring is deterministic and rule-based.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _names_text(ibm_cloud: dict) -> str:
    """Return a single lowercased string of all name/notes/purpose values."""
    parts: list[str] = []
    for items in ibm_cloud.values():
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    parts.extend(
                        str(it.get(k) or "")
                        for k in ("name", "purpose", "notes", "type")
                    )
                else:
                    parts.append(str(it))
    return " ".join(parts).lower()


def _has(ibm_cloud: dict, category: str, *tokens: str) -> bool:
    """True if any item in *category* contains one of *tokens*."""
    items = ibm_cloud.get(category, [])
    if not isinstance(items, list):
        return False
    for it in items:
        hay = (
            " ".join(str(it.get(k) or "") for k in ("name", "purpose", "notes"))
            if isinstance(it, dict)
            else str(it)
        ).lower()
        if any(t in hay for t in tokens):
            return True
    return False


def _count(ibm_cloud: dict, category: str) -> int:
    items = ibm_cloud.get(category, [])
    return len(items) if isinstance(items, list) else 0


def _any_text(ibm_cloud: dict, *tokens: str) -> bool:
    """True if the full text of all components contains one of *tokens*."""
    full = _names_text(ibm_cloud)
    return any(t in full for t in tokens)


def _vpc_count(ibm_cloud: dict) -> int:
    return _count(ibm_cloud, "vpcs")


def _region_count(ibm_cloud: dict) -> int:
    return _count(ibm_cloud, "regions")


def _zone_count(ibm_cloud: dict) -> int:
    zones = ibm_cloud.get("zones", [])
    if isinstance(zones, list) and zones:
        return len(zones)
    # Fallback: count zone tags in all component notes
    full = _names_text(ibm_cloud)
    seen = set()
    import re
    for m in re.finditer(r'zone[- _]?(\d)', full):
        seen.add(m.group(1))
    return len(seen)


# ---------------------------------------------------------------------------
# Pattern signal definitions
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    """A single scored evidence point for a pattern."""
    id: str
    label: str
    weight: float                    # positive = supports pattern; max meaningful weight ~3
    test: Callable[[dict], bool]     # receives ibm_cloud dict, returns bool
    matched: bool = field(default=False, init=False)
    negative: bool = False           # True → signal AGAINST this pattern (inverted in scoring)


@dataclass
class Pattern:
    """One IBM Think Architecture reference pattern with scoring signals."""
    id: str
    name: str
    description: str
    url: str
    signals: list[Signal]
    score: float = field(default=0.0, init=False)  # 0–100 after score()
    matched_signals: list[str] = field(default_factory=list, init=False)
    missing_signals: list[str] = field(default_factory=list, init=False)

    def score_against(self, ibm_cloud: dict, requirements_text: str = "") -> None:
        """Evaluate all signals and compute score."""
        full_context = _names_text(ibm_cloud) + " " + requirements_text.lower()
        total_positive = sum(s.weight for s in self.signals if not s.negative)
        earned = 0.0
        matched: list[str] = []
        missing: list[str] = []

        for sig in self.signals:
            result = sig.test(ibm_cloud)
            # Soft keyword check: if the primary test didn't fire, check whether
            # the requirements text mentions relevant keywords from the signal label.
            # Only applies to POSITIVE signals — negative signals are factual checks
            # and should never be overridden by keyword matches.
            if not result and not sig.negative and requirements_text:
                label_tokens = sig.label.lower().split()
                if any(t in full_context for t in label_tokens if len(t) > 4):
                    result = True

            if sig.negative:
                # Negative signal: if present it HURTS the score.
                # sig.weight is stored as a positive float even for negative signals;
                # the `negative=True` flag marks the inversion.
                if result:
                    earned -= abs(sig.weight)
                    matched.append(f"⚠ {sig.label}")
            else:
                if result:
                    earned += sig.weight
                    matched.append(f"✓ {sig.label}")
                else:
                    missing.append(f"○ {sig.label}")

        # Clamp to [0, 100]
        self.score = max(0.0, min(100.0, (earned / total_positive * 100) if total_positive else 0.0))
        self.matched_signals = matched
        self.missing_signals = missing


# ---------------------------------------------------------------------------
# Pattern catalogue
# ---------------------------------------------------------------------------

def _build_patterns() -> list[Pattern]:
    return [

        # ── Basic VPC ────────────────────────────────────────────────────────
        Pattern(
            id="basic-vpc",
            name="Basic VPC",
            description=(
                "Single VPC, one or two availability zones, internet-facing. "
                "Suitable for development, test, or simple production workloads "
                "with low HA requirements."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("vpc-present", "VPC present", 3.0,
                       lambda c: _vpc_count(c) >= 1),
                Signal("internet-ingress", "Internet ingress (LB or CIS)", 2.0,
                       lambda c: _has(c, "ingress", "load balancer", "cis", "internet services", "public")),
                Signal("compute-present", "Compute workload present", 2.0,
                       lambda c: _count(c, "compute") >= 1),
                Signal("single-vpc", "Single VPC (not hub-spoke)", 2.0,
                       lambda c: _vpc_count(c) == 1),
                Signal("no-direct-link", "No Direct Link (internet-first)", 1.0,
                       lambda c: not _has(c, "connectivity", "direct link")),
                Signal("no-tgw", "No Transit Gateway needed", 1.0,
                       lambda c: not _has(c, "connectivity", "transit gateway")),
                Signal("multi-vpc", "Multiple VPCs detected (prefers hub-spoke)", -2.0,
                       lambda c: _vpc_count(c) > 2, negative=True),
                Signal("three-zones", "Three zones detected (prefers MZR over basic)", -2.0,
                       lambda c: _zone_count(c) >= 3, negative=True),
            ],
        ),

        # ── Multi-Zone VPC (MZR) ─────────────────────────────────────────────
        Pattern(
            id="mzr",
            name="Multi-Zone VPC (MZR)",
            description=(
                "One VPC spanning all three availability zones in an IBM Cloud "
                "Multi-Zone Region. The IBM gold standard for production HA — "
                "workload, storage, and load balancers replicated across three zones."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("vpc-present", "VPC present", 3.0,
                       lambda c: _vpc_count(c) >= 1),
                Signal("three-zones", "Three availability zones", 3.0,
                       lambda c: _zone_count(c) >= 3),
                Signal("compute-present", "Compute workload present", 2.0,
                       lambda c: _count(c, "compute") >= 1),
                Signal("lb-present", "Load balancer for zone distribution", 2.0,
                       lambda c: _has(c, "ingress", "load balancer", "alb", "nlb")),
                Signal("subnets-present", "Subnets defined per zone", 1.5,
                       lambda c: _count(c, "subnets") >= 3),
                Signal("security-present", "Security controls defined", 1.0,
                       lambda c: _count(c, "security") >= 1),
                Signal("obs-present", "Observability configured", 1.0,
                       lambda c: _count(c, "observability") >= 1),
                Signal("single-vpc", "Single VPC (MZR pattern)", 1.5,
                       lambda c: _vpc_count(c) <= 2),
            ],
        ),

        # ── Hub-and-Spoke / Edge VPC ─────────────────────────────────────────
        Pattern(
            id="hub-and-spoke",
            name="Hub-and-Spoke (Edge VPC)",
            description=(
                "A dedicated Edge VPC handles all internet ingress and egress. "
                "Workload Spoke VPCs are 100% private. IBM Transit Gateway routes "
                "between them. Recommended for regulated industries and multi-team "
                "environments that share a common network perimeter."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("multiple-vpcs", "Multiple VPCs present", 3.0,
                       lambda c: _vpc_count(c) >= 2),
                Signal("tgw-present", "Transit Gateway for VPC interconnect", 3.0,
                       lambda c: _has(c, "connectivity", "transit gateway")),
                Signal("edge-vpc", "Edge/perimeter VPC detected", 2.0,
                       lambda c: _any_text(c, "edge", "perimeter", "hub", "spoke")),
                Signal("lb-present", "Load balancer in edge VPC", 1.5,
                       lambda c: _has(c, "ingress", "load balancer", "cis")),
                Signal("security-present", "Security controls present", 1.5,
                       lambda c: _count(c, "security") >= 1),
                Signal("private-workload", "Private workload VPC", 1.0,
                       lambda c: _any_text(c, "workload", "app", "private vpc", "spoke")),
            ],
        ),

        # ── Three-Tier VPC ───────────────────────────────────────────────────
        Pattern(
            id="three-tier-vpc",
            name="Three-Tier VPC",
            description=(
                "Presentation (public subnet), application (private subnet), and "
                "data (data subnet) tiers in one VPC. Classic pattern for "
                "web-facing applications with clear separation of concerns."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("vpc-present", "VPC present", 2.0,
                       lambda c: _vpc_count(c) >= 1),
                Signal("web-tier", "Web / presentation tier", 2.5,
                       lambda c: _any_text(c, "web", "frontend", "presentation", "public subnet",
                                           "load balancer", "cis", "internet services")),
                Signal("app-tier", "Application / logic tier", 2.5,
                       lambda c: _any_text(c, "app", "application", "api", "private subnet",
                                           "microservice", "roks", "vsi", "openshift")),
                Signal("data-tier", "Data / persistence tier", 2.5,
                       lambda c: _count(c, "data") >= 1 or _any_text(c, "database", "postgres",
                                                                       "object storage", "data subnet")),
                Signal("subnets-tiered", "Tiered subnets defined", 1.5,
                       lambda c: _count(c, "subnets") >= 2 or _any_text(c, "public subnet", "private subnet")),
                Signal("security-groups", "Security groups per tier", 1.0,
                       lambda c: _has(c, "security", "security group", "nacl", "acl")),
            ],
        ),

        # ── Hybrid Connectivity ──────────────────────────────────────────────
        Pattern(
            id="hybrid",
            name="Hybrid Connectivity",
            description=(
                "IBM Cloud Direct Link 2.0 or Site-to-Site VPN connects on-premises "
                "data centres to IBM Cloud VPC. Required when workloads need private "
                "access to existing on-premises systems."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("direct-link", "Direct Link present", 3.0,
                       lambda c: _has(c, "connectivity", "direct link")),
                Signal("vpn", "VPN gateway present", 2.0,
                       lambda c: _has(c, "connectivity", "vpn")),
                Signal("on-prem", "On-premises reference detected", 2.0,
                       lambda c: _any_text(c, "on-prem", "on prem", "on-premises", "data center",
                                           "data centre", "datacenter", "legacy", "corporate network")),
                Signal("bgp", "BGP / routing configured", 1.5,
                       lambda c: _any_text(c, "bgp", "route", "asn", "mpls")),
                Signal("tgw-present", "Transit Gateway for routing", 1.5,
                       lambda c: _has(c, "connectivity", "transit gateway")),
                Signal("private-endpoints", "Private endpoint access", 1.0,
                       lambda c: _count(c, "private_endpoints") >= 1),
                Signal("no-connectivity", "No connectivity services found", -3.0,
                       lambda c: _count(c, "connectivity") == 0, negative=True),
            ],
        ),

        # ── PowerVS ──────────────────────────────────────────────────────────
        Pattern(
            id="powervs",
            name="IBM Power Virtual Server (PowerVS)",
            description=(
                "IBM Power Virtual Servers (POWER9/POWER10) connected to VPC via "
                "IBM Cloud Direct Link or Transit Gateway. Required for AIX, IBM i, "
                "SAP HANA on Power, and Oracle on Power workloads."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("powervs-compute", "PowerVS compute detected", 4.0,
                       lambda c: _has(c, "compute", "power", "powervs", "aix", "ibm i", "ibm-i")),
                Signal("direct-link", "Direct Link or Cloud Connection", 2.0,
                       lambda c: _has(c, "connectivity", "direct link", "cloud connection")),
                Signal("tgw-present", "Transit Gateway to VPC", 1.5,
                       lambda c: _has(c, "connectivity", "transit gateway")),
                Signal("sap-oracle", "SAP or Oracle workload", 1.5,
                       lambda c: _any_text(c, "sap", "oracle", "hana", "db2")),
                Signal("power-keywords", "Power workload keywords", 2.0,
                       lambda c: _any_text(c, "power", "lpar", "partition", "power10", "power9",
                                           "aix", "ibm i", "as400", "iseries", "i5os")),
            ],
        ),

        # ── Financial Services Cloud ─────────────────────────────────────────
        Pattern(
            id="fsc",
            name="Financial Services Cloud (FSC)",
            description=(
                "IBM Cloud for Financial Services validated architecture. Mandatory "
                "controls: no public egress from workload VPCs, all service access "
                "via VPE, customer-managed keys (HPCS), Security and Compliance "
                "Center (SCC), and centralised logging and audit."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("hpcs-keys", "HPCS or Key Protect (BYOK/KYOK)", 3.0,
                       lambda c: _has(c, "security", "hpcs", "hyper protect", "key protect", "byok", "kyok")),
                Signal("scc", "Security and Compliance Center (SCC)", 3.0,
                       lambda c: _has(c, "security", "scc", "compliance center", "compliance")),
                Signal("private-endpoints", "All services via VPE", 2.0,
                       lambda c: _count(c, "private_endpoints") >= 2),
                Signal("no-public-egress", "No public egress from workload VPC", 2.0,
                       lambda c: _any_text(c, "no public", "private only", "no egress", "financial services",
                                           "fsc", "regulated")),
                Signal("secrets-manager", "IBM Secrets Manager", 1.5,
                       lambda c: _has(c, "security", "secrets", "secrets manager")),
                Signal("activity-tracker", "Activity Tracker for audit", 1.5,
                       lambda c: _has(c, "observability", "activity tracker", "audit")),
                Signal("hub-and-spoke", "Hub-and-Spoke network topology", 1.5,
                       lambda c: _vpc_count(c) >= 2 and _has(c, "connectivity", "transit gateway")),
                Signal("finance-keywords", "Financial/regulated keywords", 2.0,
                       lambda c: _any_text(c, "bank", "financial", "fintech", "pci", "sox", "hipaa",
                                           "regulatory", "audit trail", "immutable")),
            ],
        ),

        # ── ROKS / OpenShift ─────────────────────────────────────────────────
        Pattern(
            id="roks",
            name="Red Hat OpenShift on IBM Cloud (ROKS)",
            description=(
                "Fully managed OCP cluster on IBM Cloud VPC. IBM manages the "
                "control plane; worker nodes are VPC VSIs. Best for containerised "
                "microservices, CI/CD pipelines, and Kubernetes-native workloads."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("roks-compute", "OpenShift / ROKS cluster", 4.0,
                       lambda c: _has(c, "compute", "openshift", "roks", "ocp", "red hat openshift")),
                Signal("container-registry", "IBM Container Registry", 2.0,
                       lambda c: _has(c, "security", "container registry", "icr")
                                  or _any_text(c, "container registry", "icr", "image registry")),
                Signal("lb-ingress", "Load balancer or OCP router for ingress", 2.0,
                       lambda c: _has(c, "ingress", "router", "load balancer", "alb")),
                Signal("private-vpc", "VPC worker nodes in private subnets", 1.5,
                       lambda c: _count(c, "subnets") >= 1 or _count(c, "vpcs") >= 1),
                Signal("storage-class", "Persistent storage class configured", 1.0,
                       lambda c: _any_text(c, "block storage", "file storage", "portworx", "pvc", "persistent")),
                Signal("kubernetes-keywords", "Kubernetes/container keywords", 1.5,
                       lambda c: _any_text(c, "kubernetes", "k8s", "container", "pod", "namespace",
                                           "helm", "operator", "tekton")),
            ],
        ),

        # ── Security & Compliance ────────────────────────────────────────────
        Pattern(
            id="security-compliance",
            name="Security and Compliance Architecture",
            description=(
                "Evidence-based compliance posture using IBM Security and Compliance "
                "Center (SCC). Continuous scanning against CIS Benchmarks, "
                "IBM Cloud FS Validated controls, SOC 2, PCI DSS, HIPAA profiles."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("scc", "Security and Compliance Center (SCC)", 3.0,
                       lambda c: _has(c, "security", "scc", "compliance")),
                Signal("iam-defined", "IAM / Access Groups defined", 2.5,
                       lambda c: _has(c, "security", "iam", "identity", "access group")),
                Signal("key-mgmt", "Customer-managed keys (KP or HPCS)", 2.0,
                       lambda c: _has(c, "security", "key protect", "hpcs", "hyper protect", "byok")),
                Signal("secrets-manager", "Secrets Manager", 1.5,
                       lambda c: _has(c, "security", "secrets", "secrets manager")),
                Signal("activity-tracker", "Activity Tracker (full audit trail)", 2.0,
                       lambda c: _has(c, "observability", "activity tracker", "audit")),
                Signal("flow-logs", "VPC Flow Logs", 1.5,
                       lambda c: _has(c, "observability", "flow log")),
                Signal("compliance-keywords", "Compliance framework keywords", 2.0,
                       lambda c: _any_text(c, "pci", "hipaa", "sox", "iso 27001", "soc 2",
                                           "gdpr", "compliance", "audit", "nist")),
            ],
        ),

        # ── Resiliency and DR ─────────────────────────────────────────────────
        Pattern(
            id="resiliency-dr",
            name="Resiliency and Disaster Recovery",
            description=(
                "Multi-region active/active or warm-standby with defined RPO/RTO "
                "targets. Immutable backup (WORM / Object Lock) for ransomware "
                "protection. Cross-region COS replication and database failover."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("multi-region", "Multiple IBM Cloud regions", 3.0,
                       lambda c: _region_count(c) >= 2),
                Signal("backup-dr", "Backup / DR services defined", 3.0,
                       lambda c: _count(c, "backup_dr") >= 1),
                Signal("rpo-rto", "RPO / RTO targets stated", 2.0,
                       lambda c: _any_text(c, "rpo", "rto", "recovery point", "recovery time")),
                Signal("immutable-backup", "Immutable / WORM backup", 1.5,
                       lambda c: _any_text(c, "worm", "immutable", "object lock", "retention lock")),
                Signal("cross-region-cos", "Cross-region COS replication", 1.5,
                       lambda c: _any_text(c, "cross-region", "geo-replication", "cross region replication")),
                Signal("snapshot", "Volume snapshots", 1.0,
                       lambda c: _any_text(c, "snapshot", "point-in-time")),
                Signal("global-lb", "Global Load Balancer for failover", 1.0,
                       lambda c: _has(c, "ingress", "global load balancer", "cis", "anycast")),
            ],
        ),

        # ── Cloud-Native Containers ──────────────────────────────────────────
        Pattern(
            id="cloud-native",
            name="Cloud-Native and Container Orchestration",
            description=(
                "IBM Cloud Kubernetes Service (IKS) or ROKS with IBM Container "
                "Registry, CI/CD pipelines, service mesh, and Tekton. Designed "
                "for microservices and DevOps-first teams."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("k8s-roks", "Kubernetes (IKS or ROKS) cluster", 3.0,
                       lambda c: _has(c, "compute", "kubernetes", "iks", "roks", "openshift")),
                Signal("container-registry", "IBM Container Registry (ICR)", 2.0,
                       lambda c: _any_text(c, "container registry", "icr", "image registry", "docker")),
                Signal("cicd", "CI/CD pipeline (Tekton / CD toolchain)", 2.0,
                       lambda c: _any_text(c, "tekton", "ci/cd", "cicd", "pipeline", "continuous delivery",
                                           "github actions", "jenkins")),
                Signal("service-mesh", "Service mesh (Istio / OSSM)", 1.0,
                       lambda c: _any_text(c, "istio", "service mesh", "ossm", "mtls", "mutual tls")),
                Signal("microservices", "Microservices workload", 1.5,
                       lambda c: _any_text(c, "microservice", "api gateway", "service", "rest api")),
                Signal("observability", "Container observability", 1.5,
                       lambda c: _count(c, "observability") >= 1),
            ],
        ),

        # ── Event-Driven Architecture ────────────────────────────────────────
        Pattern(
            id="event-driven",
            name="Event-Driven Architecture",
            description=(
                "IBM Cloud Event Streams (Kafka) for high-throughput event ingestion. "
                "IBM MQ for guaranteed message delivery. IBM Cloud Code Engine for "
                "event-triggered serverless compute."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("event-streams", "IBM Event Streams (Kafka)", 3.5,
                       lambda c: _has(c, "data", "event streams", "kafka")),
                Signal("ibm-mq", "IBM MQ for messaging", 2.0,
                       lambda c: _has(c, "data", "ibm mq", "mq") or _any_text(c, "ibm mq", "mq server")),
                Signal("code-engine", "IBM Code Engine (serverless)", 1.5,
                       lambda c: _has(c, "compute", "code engine") or _any_text(c, "code engine", "serverless")),
                Signal("event-keywords", "Event-driven pattern keywords", 2.0,
                       lambda c: _any_text(c, "event", "stream", "async", "message", "queue",
                                           "publish", "subscribe", "topic", "consumer")),
                Signal("dead-letter", "Dead-letter queue strategy", 0.5,
                       lambda c: _any_text(c, "dead letter", "dlq", "poison message")),
            ],
        ),

        # ── AI and Data Platform ─────────────────────────────────────────────
        Pattern(
            id="ai-data",
            name="AI and Data Platform (watsonx)",
            description=(
                "IBM watsonx.ai, watsonx.data, and watsonx.governance for AI/ML "
                "workloads. GPU infrastructure for model training and inference. "
                "IBM Cloud Object Storage and lakehouse for training data."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("watsonx", "IBM watsonx platform", 4.0,
                       lambda c: _any_text(c, "watsonx", "watson studio", "watson machine learning",
                                           "wml", "wkc", "watson knowledge catalog")),
                Signal("gpu", "GPU infrastructure", 2.0,
                       lambda c: _any_text(c, "gpu", "gx2", "a100", "h100", "nvidia", "cuda")),
                Signal("data-storage", "Training data storage (COS / lakehouse)", 2.0,
                       lambda c: _count(c, "data") >= 1 or _any_text(c, "object storage", "data lake",
                                                                       "lakehouse", "iceberg")),
                Signal("ai-keywords", "AI / ML workload keywords", 2.5,
                       lambda c: _any_text(c, "ai", "ml", "machine learning", "deep learning",
                                           "model", "inference", "training", "llm", "foundation model",
                                           "generative ai", "rag", "vector")),
                Signal("governance", "Data governance (watsonx.governance)", 1.0,
                       lambda c: _any_text(c, "governance", "lineage", "bias", "fairness", "openscale")),
            ],
        ),

        # ── IBM Satellite / Edge ─────────────────────────────────────────────
        Pattern(
            id="satellite",
            name="IBM Satellite and Edge",
            description=(
                "IBM Satellite extends IBM Cloud services to on-premises or edge "
                "locations. Satellite Connector provides a lightweight link. "
                "Required for data-residency, latency-sensitive, or air-gapped deployments."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("satellite-compute", "IBM Satellite location or host", 4.0,
                       lambda c: _has(c, "compute", "satellite") or _any_text(c, "satellite location",
                                                                                "satellite host")),
                Signal("satellite-connector", "Satellite Connector / Link", 2.0,
                       lambda c: _any_text(c, "satellite connector", "satellite link", "link endpoint")),
                Signal("edge-keywords", "Edge / data-residency keywords", 2.0,
                       lambda c: _any_text(c, "edge", "on-prem", "data residency", "air gap",
                                           "latency", "disconnected", "remote site")),
                Signal("satellite-services", "IBM Cloud services at Satellite location", 1.5,
                       lambda c: _any_text(c, "roks on satellite", "openshift satellite",
                                           "databases for satellite")),
            ],
        ),

        # ── DevOps and IaC ───────────────────────────────────────────────────
        Pattern(
            id="devops-iac",
            name="DevOps and Infrastructure as Code",
            description=(
                "IBM Cloud Schematics (Terraform) for IaC, IBM Continuous Delivery "
                "toolchains, and IBM Cloud DevSecOps pipelines. Automation-first "
                "approach to IBM Cloud infrastructure management."
            ),
            url="https://www.ibm.com/think/architectures/patterns",
            signals=[
                Signal("schematics", "IBM Cloud Schematics (Terraform)", 3.0,
                       lambda c: _any_text(c, "schematics", "terraform", "iac", "infrastructure as code")),
                Signal("cicd", "CI/CD toolchain or pipeline", 2.5,
                       lambda c: _any_text(c, "ci/cd", "cicd", "continuous delivery", "tekton",
                                           "toolchain", "pipeline", "devsecops")),
                Signal("gitops", "GitOps / source control", 1.5,
                       lambda c: _any_text(c, "gitops", "git", "github", "gitlab", "source control")),
                Signal("container-registry", "Container Registry for image pipeline", 1.5,
                       lambda c: _any_text(c, "container registry", "icr", "image scan", "vulnerability")),
                Signal("automation-keywords", "Automation / DevOps keywords", 2.0,
                       lambda c: _any_text(c, "automation", "deploy", "pipeline", "build", "release",
                                           "devops", "devsecops", "shift left")),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_patterns(
    architecture: dict,
    requirements_text: str = "",
    top_n: int | None = None,
) -> list[dict]:
    """Score all IBM Think Architecture patterns against *architecture*.

    Parameters
    ----------
    architecture:
        The extracted architecture model dict (``ibm_cloud`` key at top level).
    requirements_text:
        Free-text customer requirements (from ``architecture["requirements"]``
        if available, or passed explicitly).
    top_n:
        If set, return only the top *top_n* results by score.

    Returns
    -------
    List of pattern result dicts, sorted by score descending:
    ``{id, name, description, url, score, matched, missing}``
    """
    ibm_cloud = architecture.get("ibm_cloud", {})

    # Fold requirements from the architecture model if not passed explicitly
    if not requirements_text:
        reqs = architecture.get("requirements", [])
        if isinstance(reqs, list):
            requirements_text = " ".join(r.get("text", "") for r in reqs if isinstance(r, dict))

    patterns = _build_patterns()
    for pat in patterns:
        pat.score_against(ibm_cloud, requirements_text)

    patterns.sort(key=lambda p: p.score, reverse=True)

    results = [
        {
            "id":          pat.id,
            "name":        pat.name,
            "description": pat.description,
            "url":         pat.url,
            "score":       round(pat.score, 1),
            "matched":     pat.matched_signals,
            "missing":     pat.missing_signals,
        }
        for pat in patterns
    ]

    if top_n is not None:
        results = results[:top_n]

    return results


def best_pattern(architecture: dict, requirements_text: str = "") -> dict:
    """Return the single highest-scoring pattern result dict."""
    results = match_patterns(architecture, requirements_text)
    return results[0] if results else {}
