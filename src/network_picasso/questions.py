from __future__ import annotations


def _missing(value: object) -> bool:
    return value in (None, "", [], {})


def _names(items: object) -> list[str]:
    """Return lowercased name strings from a list of components or strings."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, dict):
            n = str(item.get("name") or "").lower()
            if n:
                result.append(n)
        elif isinstance(item, str):
            result.append(item.lower())
    return result


def _any_has(items: object, *tokens: str) -> bool:
    """Return True if any name/notes field in *items* contains one of *tokens*."""
    if not isinstance(items, list):
        return False
    for item in items:
        if isinstance(item, dict):
            haystack = (
                str(item.get("name") or "").lower()
                + " "
                + str(item.get("purpose") or "").lower()
                + " "
                + str(item.get("notes") or "").lower()
            )
        else:
            haystack = str(item).lower()
        if any(t in haystack for t in tokens):
            return True
    return False


def _zones_covered(items: object) -> bool:
    """Return True if components span all three AZs (zone-1/2/3 or z1/z2/z3)."""
    if not isinstance(items, list):
        return False
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            z = str(item.get("zone") or "").lower()
            if z:
                seen.add(z)
    return len(seen) >= 3


def find_design_gaps(architecture: dict) -> list[dict[str, str]]:
    """Return practical IBM Cloud networking questions for incomplete or shallow inputs."""
    ibm_cloud = architecture.get("ibm_cloud", {})
    questions: list[dict[str, str]] = []

    # ── Tier-1: fire when a key is completely absent ─────────────────────────

    absence_checks = [
        (
            "Regions and availability",
            ibm_cloud.get("regions"),
            "Which IBM Cloud region or regions are in scope, and is there a DR region?",
            "Production designs commonly identify a primary region, availability-zone spread, and whether disaster recovery is active/active, warm standby, or backup/restore.",
        ),
        (
            "VPC topology",
            ibm_cloud.get("vpcs"),
            "How many VPCs are required, and what is the purpose of each VPC?",
            "Start with clear VPC boundaries for workload, shared services, management, and connectivity. Add more VPCs when isolation, routing, or account boundaries require it.",
        ),
        (
            "Subnet design",
            ibm_cloud.get("subnets"),
            "Which public, private, management, and data subnets are needed in each availability zone?",
            "A solid IBM Cloud VPC diagram usually shows public ingress subnets separately from private application, data, and management subnets, with CIDRs and zone placement called out.",
        ),
        (
            "Connectivity",
            ibm_cloud.get("connectivity"),
            "Will users and systems connect over internet ingress, VPN, Direct Link, Transit Gateway, or a combination?",
            "For enterprise and regulated workloads, explicitly separate public user ingress from private hybrid connectivity and inter-VPC routing.",
        ),
        (
            "Ingress",
            ibm_cloud.get("ingress"),
            "What is the ingress pattern: IBM Cloud Internet Services, public load balancer, private load balancer, OpenShift router, or another entry point?",
            "Show where TLS terminates, which component is internet-facing, and whether private consumers use a separate private load balancer or route.",
        ),
        (
            "Compute",
            ibm_cloud.get("compute"),
            "Which compute platforms are in scope: VPC VSI, ROKS, Bare Metal on VPC, PowerVS, Code Engine, or Cloud Functions?",
            "Name each compute platform and place it in the right network boundary. PowerVS should be shown with its workspace and connectivity back to VPC or on-premises networks.",
        ),
        (
            "Security controls",
            ibm_cloud.get("security"),
            "What security groups, NACLs, IAM boundaries, secrets, keys, and certificate controls are required?",
            "At minimum, identify IAM, secrets, key management, security groups, NACLs, certificate management, and administrative access paths.",
        ),
        (
            "Private service access",
            ibm_cloud.get("private_endpoints"),
            "Which IBM Cloud services need private endpoints or VPE gateways instead of public service access?",
            "Prefer private service access for production data paths where supported, especially databases, object storage, container registry, logging, monitoring, and key services.",
        ),
        (
            "DNS and name resolution",
            ibm_cloud.get("dns"),
            "What DNS pattern is required for public, private, hybrid, and PowerVS name resolution?",
            "Call out public DNS, private DNS, forwarding/resolver behavior, and any on-premises or PowerVS name-resolution dependencies.",
        ),
        (
            "Observability",
            ibm_cloud.get("observability"),
            "What logs, metrics, flow logs, audit events, alerting, and retention requirements must be shown?",
            "Show platform monitoring, application logs, VPC flow logs, audit events, alerting, and retention targets for operational and compliance clarity.",
        ),
        (
            "Backup and DR",
            ibm_cloud.get("backup_dr"),
            "What are the RPO/RTO targets, backup services, replication paths, and failover responsibilities?",
            "Tie DR design to concrete RPO/RTO targets. Diagrams should show backup storage, replication direction, failover region, and restore ownership.",
        ),
    ]

    asked: set[str] = set()

    for area, value, question, guidance in absence_checks:
        if _missing(value):
            questions.append({"area": area, "question": question, "guidance": guidance, "source": "rules"})
            asked.add(question)

    # ── Tier-2: fire when a key exists but lacks depth ────────────────────────

    regions = ibm_cloud.get("regions")
    vpcs = ibm_cloud.get("vpcs")
    subnets = ibm_cloud.get("subnets")
    connectivity = ibm_cloud.get("connectivity")
    ingress = ibm_cloud.get("ingress")
    compute = ibm_cloud.get("compute")
    security = ibm_cloud.get("security")
    observability = ibm_cloud.get("observability")
    backup_dr = ibm_cloud.get("backup_dr")

    def _ask(area: str, question: str, guidance: str) -> None:
        if question not in asked:
            questions.append({"area": area, "question": question, "guidance": guidance, "source": "rules"})
            asked.add(question)

    # Regions: present but only one region (no DR)
    if not _missing(regions) and isinstance(regions, list) and len(regions) < 2:
        _ask(
            "Regions and availability",
            "Only one region is identified — is a disaster recovery or multi-region strategy planned?",
            "Enterprise workloads typically designate a primary and a DR region. Confirm whether DR is active/active, warm standby, or backup/restore, and capture the target region even if it is not fully designed yet.",
        )

    # Regions: no explicit zone spread anywhere in the model
    all_components = [item for v in ibm_cloud.values() if isinstance(v, list) for item in v]
    if not _missing(regions) and not _zones_covered(all_components):
        _ask(
            "Regions and availability",
            "No availability zone placement is recorded — which components span zone-1, zone-2, and zone-3?",
            "High-availability designs place compute, subnets, and load balancers across all three AZs. Confirm zone placement for every critical tier before finalising the diagram.",
        )

    # VPCs: only one VPC, no workload/management separation
    if not _missing(vpcs) and isinstance(vpcs, list) and len(vpcs) < 2:
        _ask(
            "VPC topology",
            "Only one VPC is identified — is a separate management or shared-services VPC needed?",
            "Separating workload and management VPCs improves blast-radius isolation and simplifies NACLs. A shared-services VPC for DNS, logging, and key management is a common IBM Cloud reference pattern.",
        )

    # Connectivity: no Direct Link or VPN (hybrid path missing)
    if not _missing(connectivity):
        has_dl = _any_has(connectivity, "direct link", "dl")
        has_vpn = _any_has(connectivity, "vpn", "site-to-site")
        has_tgw = _any_has(connectivity, "transit gateway", "tgw")
        if not has_dl and not has_vpn:
            _ask(
                "Connectivity",
                "No on-premises connectivity (Direct Link or VPN) is shown — is a hybrid connection required?",
                "If workloads must reach an on-premises data centre or private WAN, add Direct Link 2.0 or VPN as the primary path. Note that Direct Link is required for MPLS or sub-10 ms latency SLAs.",
            )
        if not has_tgw and isinstance(vpcs, list) and len(vpcs) > 1:
            _ask(
                "Connectivity",
                "Multiple VPCs are present but no Transit Gateway is shown — how will VPC-to-VPC routing work?",
                "Transit Gateway is the IBM Cloud standard for connecting multiple VPCs and on-premises networks. Without it, inter-VPC traffic must route over the public internet or via VPN tunnels.",
            )

    # Ingress: no private load balancer alongside a public one
    if not _missing(ingress):
        has_private_lb = _any_has(ingress, "private", "internal")
        has_public_lb = _any_has(ingress, "public", "internet services", "cis")
        if has_public_lb and not has_private_lb:
            _ask(
                "Ingress",
                "Only public ingress is shown — do internal consumers need a private load balancer or private route?",
                "Add a private application load balancer for internal service-to-service calls so that traffic stays within the VPC and does not exit to the public internet.",
            )

    # Compute: ROKS/OpenShift present but no ingress controller noted
    if not _missing(compute) and _any_has(compute, "openshift", "roks", "ocp"):
        has_router = _any_has(ingress or [], "router", "route")
        if not has_router:
            _ask(
                "Ingress",
                "OpenShift compute is present — is the OpenShift Router or an IBM Cloud ALB handling cluster ingress?",
                "ROKS clusters expose workloads via the OpenShift Router (HAProxy) or an IBM Cloud ALB. Document which component terminates external TLS and how it connects to IBM Cloud Internet Services or the public load balancer.",
            )

    # Security: no IAM explicitly called out
    if not _missing(security) and not _any_has(security, "iam", "identity", "access"):
        _ask(
            "Security controls",
            "No IAM or identity boundary is recorded — what IAM policies, service IDs, and trusted profiles govern access?",
            "IAM is the first line of defence on IBM Cloud. Capture service-to-service auth (trusted profiles, API keys), admin access paths, and least-privilege policies for each workload component.",
        )

    # Security: no NACL or security group explicitly noted
    if not _missing(security) and not _any_has(security, "nacl", "security group", "sg ", "acl"):
        _ask(
            "Security controls",
            "No network ACLs or security groups are documented — what VPC-level network controls are in place?",
            "Every IBM Cloud VPC subnet needs an attached Network ACL and every VSI/instance needs a security group. List allow/deny rules for each tier (public, private, management, data) so they can be shown on the diagram.",
        )

    # Observability: no flow logs
    if not _missing(observability) and not _any_has(observability, "flow log", "flowlog", "flow_log"):
        _ask(
            "Observability",
            "VPC Flow Logs are not listed — will they be enabled for traffic analysis and compliance?",
            "VPC Flow Logs capture accepted and rejected traffic per subnet or interface. They are essential for incident investigation, network troubleshooting, and many compliance frameworks.",
        )

    # Observability: no platform metrics / monitoring
    if not _missing(observability) and not _any_has(observability, "monitoring", "platform metrics", "sysdig", "metric"):
        _ask(
            "Observability",
            "No platform metrics or monitoring service is recorded — what collects CPU, memory, and network metrics?",
            "IBM Cloud Monitoring (formerly Sysdig) collects platform and application metrics. Without it, you have no visibility into resource utilisation, latency SLAs, or autoscaling triggers.",
        )

    # Backup/DR: no RPO/RTO targets captured
    if not _missing(backup_dr) and not _any_has(backup_dr, "rpo", "rto", "target", "objective"):
        _ask(
            "Backup and DR",
            "RPO and RTO targets are not captured — what are the recovery objectives for this workload?",
            "Document Recovery Point Objective (RPO) and Recovery Time Objective (RTO) before designing backup and DR. These targets drive choices between active/active, warm standby, and backup/restore patterns.",
        )

    # Backup/DR: no replication path
    if not _missing(backup_dr) and not _any_has(backup_dr, "replicate", "replication", "sync", "cross-region"):
        _ask(
            "Backup and DR",
            "No cross-region replication or backup path is shown — how is data protected against a regional failure?",
            "Cloud Object Storage cross-region buckets, database read replicas, or Veeam-based backup to a second region are common patterns. Confirm the replication direction and the restore process.",
        )

    return questions
