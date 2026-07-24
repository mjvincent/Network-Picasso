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
        ),
        (
            "VPC topology",
            ibm_cloud.get("vpcs"),
            "How many VPCs are required, and what is the purpose of each VPC?",
        ),
        (
            "Subnet design",
            ibm_cloud.get("subnets"),
            "Which public, private, management, and data subnets are needed in each availability zone?",
        ),
        (
            "Connectivity",
            ibm_cloud.get("connectivity"),
            "Will users and systems connect over internet ingress, VPN, Direct Link, Transit Gateway, or a combination?",
        ),
        (
            "Ingress",
            ibm_cloud.get("ingress"),
            "What is the ingress pattern: IBM Cloud Internet Services, public load balancer, private load balancer, OpenShift router, or another entry point?",
        ),
        (
            "Compute",
            ibm_cloud.get("compute"),
            "Which compute platforms are in scope: VPC VSI, ROKS, Bare Metal on VPC, PowerVS, Code Engine, or Cloud Functions?",
        ),
        (
            "Security controls",
            ibm_cloud.get("security"),
            "What security groups, NACLs, IAM boundaries, secrets, keys, and certificate controls are required?",
        ),
        (
            "Private service access",
            ibm_cloud.get("private_endpoints"),
            "Which IBM Cloud services need private endpoints or VPE gateways instead of public service access?",
        ),
        (
            "DNS and name resolution",
            ibm_cloud.get("dns"),
            "What DNS pattern is required for public, private, hybrid, and PowerVS name resolution?",
        ),
        (
            "Observability",
            ibm_cloud.get("observability"),
            "What logs, metrics, flow logs, audit events, alerting, and retention requirements must be shown?",
        ),
        (
            "Backup and DR",
            ibm_cloud.get("backup_dr"),
            "What are the RPO/RTO targets, backup services, replication paths, and failover responsibilities?",
        ),
    ]

    for area, value, question in checks:
        if _missing(value):
            questions.append({"area": area, "question": question})

    return questions
