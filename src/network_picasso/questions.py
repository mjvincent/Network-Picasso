from __future__ import annotations

# ---------------------------------------------------------------------------
# IBM Cloud Reference Architecture Pattern — guided design interview
# ---------------------------------------------------------------------------
#
# Question tiers:
#
#   Tier 0 — ALWAYS ask.  Foundational questions that every IBM Cloud
#             architecture must answer regardless of what was extracted from
#             source files.  These drive the entire diagram.
#
#   Tier 1 — Ask when the corresponding ibm_cloud key is ABSENT.  Core
#             topology gaps that prevent a useful diagram from being generated.
#
#   Tier 2 — Ask when the key EXISTS but lacks depth.  Pattern-specific
#             quality checks based on IBM Cloud reference architectures.
#
# Reference: https://www.ibm.com/think/architectures/patterns
# Patterns covered:
#   • Multi-Zone VPC (MZR)          — three AZs, public/private/management subnets
#   • Hub-and-Spoke / Edge VPC      — dedicated edge VPC + Transit Gateway
#   • Three-Tier VPC                — presentation, application, data tiers
#   • Hybrid Connectivity           — Direct Link 2.0 or VPN for on-prem
#   • PowerVS                       — Power workloads + Cloud Connection
#   • Financial Services Cloud      — FSC-compliant controls, no public egress
#   • Red Hat OpenShift (ROKS)      — OCP on VPC, Router/ALB ingress
#   • Security & Compliance (SCC)   — Evidence-based compliance posture
# ---------------------------------------------------------------------------


def _missing(value: object) -> bool:
    return value in (None, "", [], {})


def _names(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [
        str(it.get("name") or "").lower() if isinstance(it, dict) else str(it).lower()
        for it in items
    ]


def _any_has(items: object, *tokens: str) -> bool:
    """True if any name/purpose/notes field in *items* contains one of *tokens*."""
    if not isinstance(items, list):
        return False
    for it in items:
        if isinstance(it, dict):
            hay = " ".join(
                str(it.get(k) or "") for k in ("name", "purpose", "notes")
            ).lower()
        else:
            hay = str(it).lower()
        if any(t in hay for t in tokens):
            return True
    return False


def _zones_covered(ibm_cloud: dict) -> bool:
    """True if at least 3 distinct AZ tags appear across all components."""
    seen: set[str] = set()
    for items in ibm_cloud.values():
        if not isinstance(items, list):
            continue
        for it in items:
            if isinstance(it, dict):
                z = str(it.get("zone") or "").lower()
                if z:
                    seen.add(z)
    return len(seen) >= 3


def find_design_gaps(architecture: dict) -> list[dict[str, str]]:
    """Return IBM Cloud reference-architecture-driven design questions.

    The returned list drives the Step-3 guided interview.  Every question
    includes rich IBM-specific coaching so an inexperienced user can answer
    confidently without prior IBM Cloud knowledge.
    """
    ibm_cloud = architecture.get("ibm_cloud", {})
    asked: set[str] = set()
    questions: list[dict[str, str]] = []

    def _ask(area: str, question: str, guidance: str, source: str = "rules") -> None:
        if question not in asked:
            questions.append({
                "area": area,
                "question": question,
                "guidance": guidance,
                "source": source,
            })
            asked.add(question)

    regions     = ibm_cloud.get("regions")
    vpcs        = ibm_cloud.get("vpcs")
    subnets     = ibm_cloud.get("subnets")
    connectivity= ibm_cloud.get("connectivity")
    ingress     = ibm_cloud.get("ingress")
    compute     = ibm_cloud.get("compute")
    security    = ibm_cloud.get("security")
    private_eps = ibm_cloud.get("private_endpoints")
    dns         = ibm_cloud.get("dns")
    observability = ibm_cloud.get("observability")
    backup_dr   = ibm_cloud.get("backup_dr")
    data        = ibm_cloud.get("data")

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 0 — Foundational pattern questions (ALWAYS asked)
    # IBM reference: every architecture starts by choosing a pattern.
    # ═══════════════════════════════════════════════════════════════════════

    _ask(
        "Architecture pattern",
        "Which IBM Cloud reference architecture pattern best describes this workload?",
        (
            "IBM Cloud publishes proven reference architecture patterns at "
            "ibm.com/think/architectures/patterns. The most common are:\n\n"
            "• Basic VPC — single VPC, one or two AZs, suitable for dev/test.\n"
            "• Multi-Zone VPC (MZR) — one VPC spanning all three availability zones "
            "(zone-1, zone-2, zone-3) in a region. The IBM Cloud gold standard for "
            "production HA. Compute, storage, and load balancers are replicated across "
            "all three zones so that a single data-centre failure does not cause downtime.\n"
            "• Hub-and-Spoke (Edge VPC) — a dedicated Edge VPC handles all ingress "
            "and egress traffic (internet, Direct Link, VPN). Spoke VPCs contain "
            "workloads. Transit Gateway connects them. Recommended when multiple teams "
            "or workloads share a common network perimeter.\n"
            "• Three-Tier VPC — separates presentation (public subnet), application "
            "(private subnet), and data (data subnet) tiers. Classic pattern for "
            "web-facing applications.\n"
            "• PowerVS — IBM Power Virtual Servers connected to VPC or on-premises "
            "via Cloud Connection or Direct Link. Required for AIX, IBM i, or SAP "
            "HANA on Power workloads.\n"
            "• Financial Services Cloud (FSC) — IBM Cloud for Financial Services "
            "validated architecture. Mandatory controls include: no public egress from "
            "workload VPCs, all service access via Virtual Private Endpoints (VPE), "
            "customer-managed keys (HPCS or Key Protect), Security and Compliance "
            "Center (SCC) for evidence, and centralised logging/audit.\n\n"
            "Choosing a pattern now drives every subsequent question."
        ),
    )

    _ask(
        "Regions and availability",
        "Which IBM Cloud region is the primary deployment region, and is a disaster recovery region required?",
        (
            "IBM Cloud Multi-Zone Regions (MZRs) provide three physically separate "
            "availability zones within a single region. Use an MZR for production "
            "workloads — zone-1, zone-2, zone-3 all share low-latency private "
            "connectivity within the region.\n\n"
            "Primary region options: us-south (Dallas), us-east (Washington DC), "
            "eu-de (Frankfurt), eu-gb (London), ca-tor (Toronto), jp-tok (Tokyo), "
            "au-syd (Sydney), br-sao (São Paulo).\n\n"
            "For DR: decide between active/active (both regions handle live traffic), "
            "warm standby (secondary is running but idle), or backup/restore "
            "(secondary is rebuilt from backup on failure). Active/active requires "
            "Global Load Balancer via IBM Cloud Internet Services (CIS). Warm standby "
            "requires cross-region replication of databases and object storage."
        ),
    )

    _ask(
        "Account and resource structure",
        "How many IBM Cloud accounts are involved, and how are resources organized into Resource Groups?",
        (
            "IBM Cloud uses a single flat account model — there are no sub-accounts. "
            "Large enterprises often use multiple accounts (one per environment: "
            "dev/test/prod, or one per business unit) connected via IBM Cloud "
            "Enterprise.\n\n"
            "Within an account, Resource Groups act as logical containers for IAM "
            "boundary enforcement and billing. IBM best practice: create separate "
            "Resource Groups for each workload tier (e.g. 'network-rg', 'workload-rg', "
            "'security-rg', 'observability-rg'). All IAM policies grant access to "
            "a Resource Group, not to individual resources."
        ),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 1 — Core topology (ask when key is ABSENT)
    # ═══════════════════════════════════════════════════════════════════════

    if _missing(vpcs):
        _ask(
            "VPC topology",
            "How many VPCs are needed and what is the purpose of each?",
            (
                "IBM Cloud VPC (Virtual Private Cloud) is the fundamental network "
                "boundary. Every IBM Cloud workload lives inside at least one VPC.\n\n"
                "Common IBM Cloud VPC patterns:\n"
                "• Single workload VPC — all tiers (ingress, app, data, management) "
                "in one VPC, separated by subnets. Simple and cost-effective for "
                "single-team workloads.\n"
                "• Workload + Management VPC — the management VPC hosts bastion hosts, "
                "CI/CD toolchains, and admin jump servers. Keeps operational traffic "
                "separate from production traffic and simplifies security group rules.\n"
                "• Hub-and-Spoke — Edge VPC (public-facing) + one or more Spoke VPCs "
                "(workloads). Transit Gateway routes between them. The Edge VPC is "
                "the only VPC with a public gateway or floating IP. Spoke VPCs are "
                "100% private. This is the IBM Cloud recommended pattern for regulated "
                "industries and multi-team environments.\n\n"
                "Name each VPC and state its purpose (e.g. 'edge-vpc — internet "
                "ingress and egress', 'app-vpc — production application workloads')."
            ),
        )

    if _missing(subnets):
        _ask(
            "Subnet design",
            "What subnets are needed in each availability zone, and which tier does each belong to?",
            (
                "IBM Cloud VPC subnets are zone-scoped (a subnet lives in exactly "
                "one AZ). For a production Multi-Zone VPC, replicate the same subnet "
                "structure in all three zones.\n\n"
                "IBM Cloud standard subnet tiers:\n"
                "• Public subnet — hosts internet-facing components: public load "
                "balancers, NAT gateways, VPN gateways. Attach a Public Gateway for "
                "outbound-only internet access.\n"
                "• Private subnet — hosts application servers, ROKS worker nodes, "
                "VSIs. No public gateway. All outbound traffic via Public Gateway on "
                "the public subnet or via Private Service Access.\n"
                "• Management subnet — hosts bastion hosts, admin tooling, CI/CD "
                "runners. Restrict inbound access to corporate IP ranges only.\n"
                "• Data subnet — hosts databases, message queues, caches. Only "
                "accepts traffic from the private subnet. Consider using Virtual "
                "Private Endpoints (VPE) instead of placing managed services here.\n\n"
                "Use /24 CIDR blocks (256 addresses) for each subnet — IBM Cloud "
                "reserves 5 addresses per subnet. Use a /22 or larger VPC CIDR so "
                "you have room to grow (e.g. 10.240.0.0/22 for us-south)."
            ),
        )

    if _missing(connectivity):
        _ask(
            "Hybrid connectivity",
            "Does this workload need to connect to an on-premises data centre, private WAN, or another cloud?",
            (
                "IBM Cloud hybrid connectivity options:\n\n"
                "• IBM Cloud Direct Link 2.0 Connect — private, dedicated Layer-2 "
                "circuit to IBM Cloud via a network service provider. Speeds: "
                "50 Mbps to 10 Gbps. Best for consistent, low-latency, high-bandwidth "
                "workloads (e.g. SAP, databases). SLA-backed. Recommended for "
                "regulated industries.\n"
                "• IBM Cloud Direct Link 2.0 Dedicated — your own physical port at "
                "an IBM PoP. Same as Connect but without the provider intermediary. "
                "Best for maximum throughput.\n"
                "• IBM Cloud VPN for VPC (Site-to-Site) — IPsec tunnel over the "
                "internet. Free to set up but internet-dependent. Use as backup path "
                "for Direct Link or for dev/test environments.\n"
                "• Transit Gateway — connects VPCs within IBM Cloud (same account or "
                "cross-account). Required for Hub-and-Spoke patterns.\n"
                "• IBM Cloud Satellite — extends IBM Cloud services to your "
                "on-premises location. Suitable for data-residency requirements.\n\n"
                "If no on-premises connection is needed, state 'internet only' — "
                "this still requires a decision about public gateways and floating IPs."
            ),
        )

    if _missing(ingress):
        _ask(
            "Ingress and load balancing",
            "How does external traffic enter the system — what is the ingress path from the internet to the application?",
            (
                "IBM Cloud ingress patterns:\n\n"
                "• IBM Cloud Internet Services (CIS) — global Anycast CDN + WAF + "
                "DDoS protection + Global Load Balancer. The IBM recommended front "
                "door for any publicly accessible workload. CIS terminates TLS at "
                "the edge and proxies to your origin load balancer.\n"
                "• Application Load Balancer (ALB) for VPC — Layer-7 load balancer "
                "inside the VPC. Routes HTTP/HTTPS to VSIs, OpenShift, or IP-based "
                "backends. Supports health checks, sticky sessions, and mutual TLS.\n"
                "• Network Load Balancer (NLB) for VPC — Layer-4, for TCP/UDP "
                "workloads. Ultra-low latency. Used for non-HTTP protocols.\n"
                "• OpenShift Router (HAProxy) — ROKS clusters have a built-in "
                "ingress controller. Routes are exposed via IBM-managed wildcard DNS. "
                "Combine with CIS for WAF and global routing.\n\n"
                "Typical production path: Internet → CIS (WAF/CDN) → Public Load "
                "Balancer (public subnet) → Application Servers (private subnet).\n\n"
                "Private consumers (internal APIs, service-to-service): use a "
                "Private ALB (no public IP) or direct VPE access."
            ),
        )

    if _missing(compute):
        _ask(
            "Compute platform",
            "What compute platform will host the workload — VSI, OpenShift, Kubernetes, Bare Metal, or PowerVS?",
            (
                "IBM Cloud compute options:\n\n"
                "• VPC Virtual Server Instance (VSI) — x86 virtual machines on "
                "dedicated or shared hosts. Profiles: bx2 (balanced), cx2 (compute), "
                "mx2 (memory), gx2 (GPU). Choose the profile closest to your sizing. "
                "Fastest to provision. Ideal for lift-and-shift or custom OS images.\n"
                "• Red Hat OpenShift on IBM Cloud (ROKS) — fully managed OCP cluster. "
                "IBM manages the control plane. Worker nodes are VPC VSIs that you "
                "own. Recommended for containerised microservices, CI/CD, and "
                "Kubernetes-native workloads.\n"
                "• IBM Cloud Kubernetes Service (IKS) — upstream Kubernetes, no "
                "OpenShift. Lighter-weight, lower cost per node.\n"
                "• Bare Metal on VPC — dedicated physical servers in a VPC. Required "
                "for workloads that need hardware isolation, NUMA pinning, or SR-IOV "
                "(e.g. NFV, high-performance HPC).\n"
                "• IBM Power Virtual Server (PowerVS) — Power processor VMs (POWER9, "
                "POWER10) for AIX, IBM i, and Linux on Power. Used for SAP HANA, "
                "Oracle, Db2, and mainframe-adjacent workloads. Connects to VPC via "
                "Cloud Connection or Direct Link.\n"
                "• IBM Cloud Code Engine — fully serverless containers and functions. "
                "No cluster management. Ideal for event-driven workloads, batch jobs, "
                "and APIs with variable traffic."
            ),
        )

    if _missing(security):
        _ask(
            "Security controls",
            "What IAM, key management, secrets, network, and compliance controls are required?",
            (
                "IBM Cloud security is multi-layered. Cover all of these:\n\n"
                "1. IAM (Identity and Access Management) — define who can do what. "
                "Use Access Groups (not per-user policies). Assign least-privilege "
                "roles (Viewer, Operator, Editor, Administrator). Use Trusted Profiles "
                "for compute-to-service auth (no API keys stored in code).\n\n"
                "2. Key Management — choose between:\n"
                "   • IBM Key Protect — FIPS 140-2 Level 3, shared HSM, cost-effective.\n"
                "   • IBM Hyper Protect Crypto Services (HPCS) — FIPS 140-2 Level 4, "
                "   dedicated HSM, required for Financial Services Cloud and PCI.\n"
                "   All COS buckets, block volumes, and databases should use "
                "   customer-managed encryption (BYOK or KYOK via Key Protect/HPCS).\n\n"
                "3. Secrets Management — IBM Secrets Manager stores API keys, "
                "certificates, and database credentials. Applications retrieve secrets "
                "at runtime via the Secrets Manager API or Kubernetes CSI driver. "
                "Never store secrets in environment variables or config maps.\n\n"
                "4. Network Controls:\n"
                "   • Security Groups — stateful, instance-level firewall (like AWS SGs). "
                "   Define allow rules only. Deny is implicit.\n"
                "   • Network ACLs (NACLs) — stateless, subnet-level. Use as a second "
                "   layer of defence for inter-subnet traffic.\n"
                "   • No public gateway on data or management subnets.\n\n"
                "5. Compliance — IBM Security and Compliance Center (SCC) continuously "
                "scans your IBM Cloud resources against CIS Benchmarks, IBM Cloud "
                "FS Validated controls, SOC 2, PCI DSS, and HIPAA profiles."
            ),
        )

    if _missing(private_eps):
        _ask(
            "Private service access",
            "Which IBM Cloud managed services will be accessed privately via Virtual Private Endpoints (VPE)?",
            (
                "IBM Cloud Virtual Private Endpoints (VPE) allow your VPC to reach "
                "IBM Cloud managed services (Cloud Object Storage, databases, Key "
                "Protect, Secrets Manager, Container Registry, etc.) over the "
                "IBM private backbone — no public internet, no floating IP needed.\n\n"
                "IBM Cloud reference architecture rule: ALL production data-path "
                "service access should use VPE. Public service endpoints should be "
                "disabled in production.\n\n"
                "Common services that need VPE:\n"
                "• IBM Cloud Object Storage (COS)\n"
                "• IBM Cloud Databases (PostgreSQL, Elasticsearch, Redis, etc.)\n"
                "• IBM Cloud Container Registry\n"
                "• IBM Key Protect / HPCS\n"
                "• IBM Secrets Manager\n"
                "• IBM Cloud Monitoring / Log Analysis\n"
                "• IBM Cloud Activity Tracker\n\n"
                "Each VPE is a reserved IP in your VPC subnet. DNS resolves the "
                "service's private hostname to that IP. The connection never leaves "
                "the IBM Cloud private network."
            ),
        )

    if _missing(dns):
        _ask(
            "DNS and name resolution",
            "What DNS strategy is required — public DNS, IBM Cloud DNS Services, hybrid forwarding, or all three?",
            (
                "IBM Cloud DNS options:\n\n"
                "• IBM Cloud Internet Services (CIS) DNS — authoritative public DNS, "
                "managed by IBM. Supports DNSSEC, geo-routing, and health checks. "
                "Use for any externally resolvable hostname (e.g. api.mycompany.com).\n\n"
                "• IBM Cloud DNS Services (private DNS) — private DNS zones visible "
                "only inside your VPC. Use for internal service-to-service resolution "
                "(e.g. 'payments.internal.mycompany.com'). Supports split-horizon: "
                "same hostname resolves to private IP inside VPC and public IP outside.\n\n"
                "• Hybrid DNS forwarding — required when on-premises systems need "
                "to resolve IBM Cloud private hostnames, or when IBM Cloud workloads "
                "need to resolve on-premises DNS. Configure a DNS resolver in your "
                "VPC that forwards queries to on-premises DNS servers via Direct Link "
                "or VPN.\n\n"
                "• VPE DNS — IBM Cloud automatically creates private DNS records for "
                "VPE gateway IPs. When you create a VPE for Cloud Object Storage, IBM "
                "DNS resolves 's3.direct.us-south.cloud-object-storage.appdomain.cloud' "
                "to your VPE IP. No manual configuration needed."
            ),
        )

    if _missing(observability):
        _ask(
            "Observability",
            "What logging, metrics, tracing, and audit event requirements must the architecture satisfy?",
            (
                "IBM Cloud observability stack (the 'three pillars'):\n\n"
                "1. Logs — IBM Cloud Logs (formerly Log Analysis) collects application "
                "and platform logs. VPC Flow Logs capture all accepted and rejected "
                "packets at the subnet or interface level — required for network "
                "forensics and many compliance frameworks. Configure Flow Logs to "
                "write to Cloud Object Storage.\n\n"
                "2. Metrics — IBM Cloud Monitoring (Sysdig-based) collects platform "
                "metrics (CPU, memory, disk, network) from VSIs, ROKS, and IBM Cloud "
                "services. Define alert policies and dashboards. SLA measurement "
                "requires metrics.\n\n"
                "3. Activity Tracker — captures every IBM Cloud API call as a "
                "structured audit event (who did what, when, from where). Required "
                "for SOC 2, PCI DSS, HIPAA, and ISO 27001. Events are written to "
                "Cloud Object Storage for long-term retention.\n\n"
                "4. Application Performance Monitoring (APM) — use IBM Instana or "
                "Dynatrace for distributed tracing, code-level visibility, and "
                "automatic dependency mapping.\n\n"
                "IBM Cloud best practice: route all observability data to a "
                "centralised observability account (separate from workload accounts) "
                "so operators can investigate incidents without production access."
            ),
        )

    if _missing(backup_dr):
        _ask(
            "Backup and DR",
            "What are the Recovery Point Objective (RPO) and Recovery Time Objective (RTO) for this workload, and what backup strategy is required?",
            (
                "Define RPO and RTO before choosing a backup strategy:\n\n"
                "• RPO (Recovery Point Objective) — maximum acceptable data loss. "
                "Example: RPO = 1 hour means backups must run at least every hour.\n"
                "• RTO (Recovery Time Objective) — maximum acceptable downtime. "
                "Example: RTO = 4 hours means the system must be restored within 4 "
                "hours of a failure.\n\n"
                "IBM Cloud backup patterns:\n\n"
                "• IBM Cloud Backup — agent-based, block-level backup for VSIs. "
                "Supports incremental backups and bare-metal restore.\n"
                "• Snapshot for VPC — crash-consistent point-in-time snapshots of "
                "block volumes. Near-zero RPO. Snapshots are cross-zone and can be "
                "copied cross-region.\n"
                "• Database auto-backups — IBM Cloud Databases (ICD) performs "
                "automatic daily backups with 30-day retention. Restore is "
                "point-in-time. Cross-region restore is available.\n"
                "• Cross-region COS replication — Cloud Object Storage supports "
                "automatic object replication between COS instances in different "
                "regions. Used for disaster recovery of unstructured data.\n\n"
                "DR strategy choices:\n"
                "• Active/Active — both regions serve live traffic. Zero RTO but "
                "highest cost. Requires Global Load Balancer (CIS).\n"
                "• Warm Standby — secondary region is running but idle. RTO ~15–30 min.\n"
                "• Backup/Restore — secondary is rebuilt from backups. RTO ~hours."
            ),
        )

    if _missing(data):
        _ask(
            "Data services",
            "What databases, object storage, file storage, and messaging services are required?",
            (
                "IBM Cloud managed data services:\n\n"
                "Relational databases:\n"
                "• IBM Cloud Databases for PostgreSQL — open-source, HA, cross-region "
                "read replicas. Most common choice for new workloads.\n"
                "• IBM Cloud Databases for MySQL — compatible with MySQL 8.\n"
                "• Db2 on Cloud — IBM's enterprise relational database.\n\n"
                "NoSQL / Cache:\n"
                "• IBM Cloud Databases for Redis — in-memory cache and message broker.\n"
                "• IBM Cloud Databases for MongoDB — document store.\n"
                "• IBM Cloud Databases for Elasticsearch — full-text search.\n\n"
                "Object storage:\n"
                "• IBM Cloud Object Storage (COS) — S3-compatible. Three resiliency "
                "tiers: Cross-Region (highest), Regional, Single Site. Use Cross-Region "
                "for DR and compliance. Enable Object Versioning for accidental-delete "
                "protection.\n\n"
                "Messaging / Streaming:\n"
                "• IBM Event Streams — fully managed Apache Kafka. Use for "
                "event-driven architectures, CQRS, and real-time data pipelines.\n"
                "• IBM MQ on Cloud — enterprise message queuing. Required for "
                "financial and telecom workloads that use MQ protocols.\n\n"
                "File storage: IBM Cloud File Storage for VPC (NFS shares). "
                "Suitable for shared file access between VSIs in the same AZ."
            ),
        )

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 2 — Depth checks (ask when key EXISTS but pattern is incomplete)
    # ═══════════════════════════════════════════════════════════════════════

    # ── Region / AZ ──────────────────────────────────────────────────────

    if not _missing(regions) and isinstance(regions, list) and len(regions) < 2:
        _ask(
            "Regions and availability",
            "Only one region is identified — is a disaster recovery region required, and which pattern applies?",
            (
                "IBM Cloud Multi-Zone Regions already provide intra-region HA "
                "(three AZs). However a single MZR does NOT protect against a full "
                "regional failure or a catastrophic event.\n\n"
                "Add a DR region if:\n"
                "• RTO < 4 hours — warm standby in a second region is the minimum.\n"
                "• RPO < 15 minutes — active/active with CIS Global Load Balancer.\n"
                "• Regulatory requirement for geographic separation (DORA, FFIEC, etc.).\n\n"
                "Recommended DR region pairings: us-south ↔ us-east, eu-de ↔ eu-gb, "
                "ca-tor ↔ us-east, jp-tok ↔ jp-osa."
            ),
        )

    if not _missing(regions) and not _zones_covered(ibm_cloud):
        _ask(
            "Regions and availability",
            "No availability zone placement is recorded — which components are replicated across zone-1, zone-2, and zone-3?",
            (
                "IBM Cloud Multi-Zone Regions have three AZs (zone-1, zone-2, zone-3). "
                "For production HA, each tier should span all three zones:\n\n"
                "• Subnets: create one subnet per tier per zone (e.g. public-zone-1, "
                "public-zone-2, public-zone-3). IBM Cloud does not auto-expand subnets "
                "across zones.\n"
                "• Load balancers: IBM Cloud ALB and NLB are MZR-aware — they "
                "distribute traffic across backends in all three zones automatically.\n"
                "• Compute (VSI): place instances in all three zones behind an ALB. "
                "Use Instance Groups with a multi-zone load balancer policy.\n"
                "• ROKS: worker pools span all three zones. Use zone-affinity "
                "rules for pod scheduling.\n"
                "• Block storage: IBM Cloud Block Storage for VPC is zone-scoped. "
                "For cross-zone data access, use Cloud Object Storage (cross-zone) "
                "or a distributed database (ICD PostgreSQL with read replicas)."
            ),
        )

    # ── VPC ──────────────────────────────────────────────────────────────

    if not _missing(vpcs) and isinstance(vpcs, list) and len(vpcs) < 2:
        _ask(
            "VPC topology",
            "Only one VPC is defined — does the workload need a separate Edge VPC, Management VPC, or Shared Services VPC?",
            (
                "IBM Cloud reference patterns that use multiple VPCs:\n\n"
                "• Hub-and-Spoke (Edge + Workload): an Edge VPC holds all "
                "public-facing resources (CIS origin, public ALB, VPN gateway, "
                "Direct Link attachment). Workload VPCs hold application tiers. "
                "Transit Gateway routes traffic between them. This isolates internet "
                "exposure to a single VPC and lets you apply strict NACLs at the "
                "edge.\n\n"
                "• Management VPC: hosts bastion hosts (or IBM Cloud Security Groups "
                "for Terraform/Ansible), CI/CD toolchains, monitoring agents, and "
                "admin jump servers. Keeps operational traffic out of workload VPCs.\n\n"
                "• Shared Services VPC: hosts DNS resolvers, NTP, shared NFS mounts, "
                "and centralised logging forwarders. All workload VPCs peer to it "
                "via Transit Gateway.\n\n"
                "If all of the above are needed, the IBM FSC reference architecture "
                "uses four VPCs: Edge, Management, Workload, and Shared Services."
            ),
        )

    # ── Connectivity ─────────────────────────────────────────────────────

    if not _missing(connectivity):
        has_dl  = _any_has(connectivity, "direct link")
        has_vpn = _any_has(connectivity, "vpn")
        has_tgw = _any_has(connectivity, "transit gateway", "tgw")

        if not has_dl and not has_vpn:
            _ask(
                "Hybrid connectivity",
                "No Direct Link or VPN is shown — is the workload purely internet-facing, or is on-premises connectivity required?",
                (
                    "If the workload is cloud-native and internet-only, no hybrid "
                    "connectivity is needed. State this explicitly so it appears on "
                    "the diagram (external users access via CIS + ALB only).\n\n"
                    "If on-premises connectivity IS required:\n"
                    "• Direct Link 2.0 Connect — recommended. Order via a network "
                    "service provider. Provisioning takes 3–10 business days. "
                    "Supports BGP routing. Single or redundant circuits.\n"
                    "• VPN for VPC (Site-to-Site) — deploy VPN gateways in the public "
                    "subnet. Policy-based or route-based. Maximum 1 Gbps. Use as "
                    "backup for Direct Link or for dev/test.\n"
                    "• Both: IBM recommends Direct Link as primary + VPN as failover "
                    "for any production workload with on-prem dependency."
                ),
            )

        if not has_tgw and isinstance(vpcs, list) and len(vpcs) > 1:
            _ask(
                "Hybrid connectivity",
                "Multiple VPCs are defined but no Transit Gateway is shown — how will VPC-to-VPC routing work?",
                (
                    "IBM Cloud Transit Gateway is the only IBM-native way to connect "
                    "multiple VPCs in the same or different regions.\n\n"
                    "Without Transit Gateway, VPCs are fully isolated from each other "
                    "(no automatic peering). You would need VPN tunnels between VPCs "
                    "or route traffic via Direct Link, which adds cost and latency.\n\n"
                    "Transit Gateway features:\n"
                    "• Connect up to 20 VPCs per gateway (default).\n"
                    "• Cross-account connections (e.g. dev account → shared services).\n"
                    "• Global routing (cross-region) is an add-on.\n"
                    "• Each connection is priced per GB of data transferred.\n\n"
                    "In Hub-and-Spoke: the Transit Gateway connects the Edge VPC and "
                    "all Spoke VPCs. The Edge VPC propagates a default route "
                    "(0.0.0.0/0) that forces all outbound internet traffic through "
                    "the Edge VPC's public gateway — this is the IBM recommended "
                    "'traffic inspection' pattern for regulated workloads."
                ),
            )

    # ── Ingress ──────────────────────────────────────────────────────────

    if not _missing(ingress):
        has_cis = _any_has(ingress, "internet services", "cis")
        has_pub = _any_has(ingress, "public", "application load balancer", "alb")
        has_prv = _any_has(ingress, "private", "internal")

        if not has_cis and has_pub:
            _ask(
                "Ingress and load balancing",
                "A public load balancer is shown but IBM Cloud Internet Services (CIS) is not — is WAF and DDoS protection required?",
                (
                    "IBM Cloud Internet Services (CIS) is the recommended front-door "
                    "for any production workload exposed to the internet.\n\n"
                    "CIS provides:\n"
                    "• Layer-7 WAF (OWASP top-10 rules, custom rules)\n"
                    "• Volumetric DDoS mitigation (Cloudflare network)\n"
                    "• Global Anycast CDN with edge caching\n"
                    "• Global Load Balancer across multiple origin regions\n"
                    "• TLS termination at the edge (reduces load on origin)\n"
                    "• Bot management and rate limiting\n\n"
                    "Without CIS, your public load balancer IP is directly exposed. "
                    "Any DDoS or Layer-7 attack hits your infrastructure directly.\n\n"
                    "Add CIS even if you do not need CDN — the WAF and DDoS "
                    "protection alone justify the cost for production workloads."
                ),
            )

        if has_pub and not has_prv:
            _ask(
                "Ingress and load balancing",
                "Only public ingress is shown — do internal services need a private load balancer for service-to-service traffic?",
                (
                    "IBM Cloud Application Load Balancer (ALB) for VPC supports both "
                    "public (internet-facing) and private (internal) modes.\n\n"
                    "Add a Private ALB when:\n"
                    "• Microservices call each other within the VPC (service mesh "
                    "or direct HTTP).\n"
                    "• On-premises systems need to reach IBM Cloud services via "
                    "Direct Link without traversing the public internet.\n"
                    "• Multiple VPCs communicate via Transit Gateway and one VPC "
                    "hosts shared APIs that other VPCs consume.\n\n"
                    "A Private ALB has no public IP. DNS resolves to a private RFC1918 "
                    "address. It is free from internet attack surface and does not "
                    "require a public subnet."
                ),
            )

    # ── Compute ──────────────────────────────────────────────────────────

    if not _missing(compute):
        is_roks = _any_has(compute, "openshift", "roks", "ocp")
        is_vsi  = _any_has(compute, "vsi", "virtual server", "bx2", "mx2", "cx2")
        has_powervs_compute = _any_has(compute, "power", "powervs", "aix", "ibm i")

        if is_roks and not _any_has(ingress or [], "router", "route", "cis"):
            _ask(
                "Ingress and load balancing",
                "OpenShift (ROKS) is the compute platform — how is cluster ingress handled: OpenShift Router, IBM Cloud ALB, or CIS?",
                (
                    "ROKS exposes workloads via two mechanisms:\n\n"
                    "1. OpenShift Router (HAProxy) — IBM-managed, built into every "
                    "ROKS cluster. Exposes Route objects. IBM provides a wildcard DNS "
                    "entry (*.cluster-id.us-south.containers.appdomain.cloud) that "
                    "resolves to the Router's load balancer IP. Add a custom domain "
                    "via CIS CNAME.\n\n"
                    "2. IBM Cloud ALB — deploy the IBM Cloud ALB Ingress controller "
                    "in your cluster. More control over health checks, TLS config, and "
                    "session affinity. Recommended when you need fine-grained routing "
                    "or mutual TLS between services.\n\n"
                    "Best practice for production: put CIS in front of the ROKS "
                    "ingress. CIS forwards to the Router or ALB. This adds WAF, "
                    "DDoS, and global routing without changing application code."
                ),
            )

        if is_vsi and not _any_has(security or [], "security group", "sg", "nacl"):
            _ask(
                "Security controls",
                "VSIs are in scope — what Security Group and NACL rules define the allowed traffic for each tier?",
                (
                    "IBM Cloud VPC network security is enforced at two levels:\n\n"
                    "Security Groups (instance-level, stateful):\n"
                    "• Assign one or more SGs to each VSI network interface.\n"
                    "• Default SG: allows all outbound, denies all inbound.\n"
                    "• Public subnet VSIs (load balancers): allow inbound 443 from "
                    "0.0.0.0/0, allow outbound to private subnet CIDR.\n"
                    "• Private subnet VSIs (app): allow inbound from public subnet "
                    "CIDR only, allow outbound to data subnet CIDR.\n"
                    "• Management subnet: allow inbound from corporate CIDR on "
                    "port 22 (SSH) or 3389 (RDP).\n\n"
                    "Network ACLs (subnet-level, stateless):\n"
                    "• Apply to all traffic crossing a subnet boundary.\n"
                    "• Rules are evaluated in order (like iptables).\n"
                    "• IBM recommendation: use NACLs as a coarse-grained "
                    "quarantine mechanism (block known-bad CIDR ranges, limit "
                    "management access), and Security Groups for fine-grained control."
                ),
            )

        if has_powervs_compute:
            _ask(
                "Compute platform",
                "PowerVS compute is in scope — how does the PowerVS workspace connect to the VPC and on-premises network?",
                (
                    "IBM Power Virtual Server (PowerVS) runs in IBM's Power data "
                    "centres (co-located with IBM Cloud but on separate infrastructure). "
                    "To connect PowerVS to VPC or on-premises:\n\n"
                    "• Cloud Connection (deprecated, legacy) — private L2 circuit "
                    "between PowerVS workspace and IBM Cloud VPC backbone. Being "
                    "replaced by Direct Link.\n"
                    "• Direct Link 2.0 — recommended. PowerVS workspaces can attach "
                    "to a Direct Link gateway. The same Direct Link can carry both "
                    "PowerVS and on-premises traffic.\n"
                    "• Transit Gateway — PowerVS workspaces can be connected to a "
                    "Transit Gateway as a PowerVS connection type. Enables routing "
                    "between PowerVS, VPC, and on-premises (via Direct Link attached "
                    "to the same Transit Gateway).\n\n"
                    "IBM reference pattern for PowerVS:\n"
                    "PowerVS workspace → Direct Link 2.0 → Transit Gateway → VPC.\n"
                    "On-premises → Direct Link 2.0 → same Transit Gateway.\n"
                    "All traffic flows through the Transit Gateway hub."
                ),
            )

    # ── Security ─────────────────────────────────────────────────────────

    if not _missing(security):
        if not _any_has(security, "iam", "identity", "access", "trusted profile"):
            _ask(
                "Security controls",
                "IAM and identity boundaries are not defined — what IAM Access Groups, Trusted Profiles, and service-to-service authorizations are required?",
                (
                    "IBM Cloud IAM governs all resource access. Design it before "
                    "deploying anything.\n\n"
                    "Access Groups (recommended over per-user policies):\n"
                    "• Create one Access Group per role (e.g. 'network-admins', "
                    "'app-deployers', 'security-auditors', 'read-only-viewers').\n"
                    "• Assign Resource Group-scoped roles to each group.\n"
                    "• Add users and Service IDs to groups, not to policies directly.\n\n"
                    "Trusted Profiles (compute-to-service, no API keys):\n"
                    "• ROKS pods, VSI compute, and Code Engine instances can assume "
                    "a Trusted Profile at runtime.\n"
                    "• The profile grants IAM roles to the compute identity without "
                    "a stored credential. IBM-recommended for all non-human access.\n\n"
                    "Service-to-Service Authorizations:\n"
                    "• Required for: Key Protect → COS (envelope encryption), "
                    "Secrets Manager → Key Protect (key wrapping), "
                    "ROKS → Cloud Object Storage (registry backups).\n"
                    "• Created via IAM → Authorizations. Grant the minimum role needed."
                ),
            )

        if not _any_has(security, "key protect", "hpcs", "key management", "encryption"):
            _ask(
                "Security controls",
                "No key management service is recorded — will Cloud Object Storage, block volumes, and databases use customer-managed encryption keys?",
                (
                    "IBM Cloud supports two forms of encryption key management:\n\n"
                    "• IBM Key Protect — FIPS 140-2 Level 3. Shared HSM. "
                    "Low cost. Suitable for most workloads. Integrates with COS, "
                    "Block Storage for VPC, ICD, Secrets Manager, and ROKS etcd.\n\n"
                    "• IBM Hyper Protect Crypto Services (HPCS) — FIPS 140-2 Level 4. "
                    "Dedicated HSM. Required for Financial Services Cloud, PCI DSS, "
                    "and workloads requiring 'Keep Your Own Key' (KYOK) assurance. "
                    "You initialise the HSM with your own master key material — IBM "
                    "cannot access it.\n\n"
                    "IBM reference architecture requirement: all data at rest must be "
                    "encrypted with BYOK (Bring Your Own Key). Create a root key in "
                    "Key Protect or HPCS and use it to wrap data encryption keys for "
                    "COS, Block Storage, and all ICD databases."
                ),
            )

        if not _any_has(security, "scc", "compliance", "security and compliance"):
            _ask(
                "Security controls",
                "Is IBM Security and Compliance Center (SCC) required to continuously validate the architecture against a compliance profile?",
                (
                    "IBM Security and Compliance Center (SCC) is IBM's built-in "
                    "compliance automation platform.\n\n"
                    "SCC scans IBM Cloud resource configurations against:\n"
                    "• IBM Cloud Framework for Financial Services (FS Cloud) — "
                    "mandatory for IBM Cloud for Financial Services deployments.\n"
                    "• CIS IBM Cloud Foundations Benchmark — baseline for all "
                    "IBM Cloud deployments.\n"
                    "• SOC 2, PCI DSS, HIPAA, ISO 27001, NIST SP 800-53.\n\n"
                    "SCC generates an evidence report showing pass/fail for each "
                    "control, with links to the specific misconfigured resource. "
                    "Results can be forwarded to Activity Tracker for auditor access.\n\n"
                    "If your workload has any regulatory requirement, add SCC to the "
                    "architecture and state which compliance profile applies."
                ),
            )

    # ── Observability ────────────────────────────────────────────────────

    if not _missing(observability):
        if not _any_has(observability, "flow log", "flowlog"):
            _ask(
                "Observability",
                "VPC Flow Logs are not listed — will they be enabled to capture network traffic for forensics and compliance?",
                (
                    "IBM Cloud VPC Flow Logs capture metadata about every accepted "
                    "and rejected IP flow at the subnet or network interface level.\n\n"
                    "Flow Log record fields include: source/dest IP, source/dest port, "
                    "protocol, bytes, packets, action (accepted/rejected), initiator "
                    "type (VM or LB), and timestamp.\n\n"
                    "Flow Logs write to a Cloud Object Storage bucket in near real-time. "
                    "They are required for:\n"
                    "• PCI DSS (network traffic logging)\n"
                    "• HIPAA (access logging for PHI systems)\n"
                    "• Incident response (tracing lateral movement)\n"
                    "• IBM Cloud FS Validated control C-030 (network monitoring)\n\n"
                    "Enable Flow Logs at the VPC level (covers all subnets and "
                    "interfaces) or at the subnet/interface level for more granular "
                    "capture. Store logs in a separate, write-protected COS bucket."
                ),
            )

        if not _any_has(observability, "monitoring", "sysdig", "metrics", "platform"):
            _ask(
                "Observability",
                "No platform metrics service is defined — what collects CPU, memory, network, and custom application metrics?",
                (
                    "IBM Cloud Monitoring is the IBM Cloud-native metrics platform "
                    "(powered by Sysdig).\n\n"
                    "Platform metrics (auto-collected from IBM Cloud services):\n"
                    "• VPC VSI: CPU, memory, disk I/O, network throughput.\n"
                    "• IBM Load Balancer: requests/sec, active connections, latency.\n"
                    "• ROKS: node metrics, pod metrics, container resource usage.\n"
                    "• ICD databases: connections, queries/sec, replication lag.\n\n"
                    "Custom metrics: instrument applications with Prometheus. "
                    "IBM Cloud Monitoring scrapes Prometheus endpoints and stores "
                    "metrics in its time-series database.\n\n"
                    "Alerting: configure alert policies (Slack, PagerDuty, email) "
                    "for threshold breaches, anomaly detection, and uptime checks.\n\n"
                    "One IBM Cloud Monitoring instance per region. Connect it to the "
                    "centralised observability account to separate operator access "
                    "from application team access."
                ),
            )

    # ── Backup / DR ──────────────────────────────────────────────────────

    if not _missing(backup_dr):
        if not _any_has(backup_dr, "rpo", "rto", "objective"):
            _ask(
                "Backup and DR",
                "RPO and RTO targets are not stated — what are the recovery objectives that drive the backup and DR strategy?",
                (
                    "IBM Cloud DR patterns by RTO:\n\n"
                    "• RTO < 1 hour (Active/Active):\n"
                    "  — Deploy identical stacks in two regions.\n"
                    "  — CIS Global Load Balancer with health checks routes traffic "
                    "to the healthy region automatically.\n"
                    "  — Databases use active/active replication (IBM HyperSwap or "
                    "cross-region ICD read replica + application-level failover).\n\n"
                    "• RTO 1–4 hours (Warm Standby):\n"
                    "  — Deploy infrastructure in DR region but keep compute scaled down.\n"
                    "  — Scale up on a runbook trigger.\n"
                    "  — Use COS cross-region replication for object data.\n"
                    "  — Use ICD cross-region restore for databases.\n\n"
                    "• RTO > 4 hours (Backup/Restore):\n"
                    "  — Daily Snapshots of block volumes.\n"
                    "  — ICD daily automated backups (30-day retention).\n"
                    "  — Restore to a new region from snapshots/backups.\n"
                    "  — Suitable for dev/test or low-criticality workloads."
                ),
            )

    return questions
