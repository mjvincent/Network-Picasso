from __future__ import annotations


def _missing(value: object) -> bool:
    return value in (None, "", [], {})


def find_design_gaps(architecture: dict) -> list[dict[str, str]]:
    """Return practical IBM Cloud networking questions for incomplete inputs."""
    ibm_cloud = architecture.get("ibm_cloud", {})
    questions: list[dict[str, str]] = []

    checks = [
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

    for area, value, question, guidance in checks:
        if _missing(value):
            questions.append({"area": area, "question": question, "guidance": guidance})

    return questions
