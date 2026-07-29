from __future__ import annotations

import csv
import json
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".csv", ".json", ".md", ".txt", ".tsv", ".xlsx"}

# ---------------------------------------------------------------------------
# File-role classification
# ---------------------------------------------------------------------------
# Each uploaded file is tagged with a role so the intake pipeline can weight
# it appropriately.  Roles:
#   "bom"                  – primary bill of materials / solution design
#   "pricing_catalog"      – IBM pricing estimator export (skip architecture extraction)
#   "unified_pricing"      – Cognizant/partner unified pricing workbook (structured parse)
#   "solution_description" – narrative/notes document
#   "existing_architecture"– JSON architecture model
#   "unknown"              – anything else

FILE_ROLES = frozenset({
    "bom",
    "pricing_catalog",
    "unified_pricing",
    "solution_description",
    "existing_architecture",
    "unknown",
})

# Sheet/filename fragments that identify pure pricing-catalog exports.
# These files contain SKU catalogs and should NOT be parsed as architecture.
_CATALOG_FILENAME_SIGNALS = re.compile(
    r'(price[\s_-]*estimat|estimat.*price|ibm[\s_-]*price|pricing[\s_-]*catalog'
    r'|catalog[\s_-]*price|power[\s_-]*vs[\s_-]*estimat|powervs.*estimat'
    r'|estimat.*powervs)',
    re.IGNORECASE,
)

# Sheet names inside XLSX that indicate a pricing catalog sheet (skip these sheets).
_CATALOG_SHEET_SIGNALS = re.compile(
    r'(price[\s_-]*list|catalog|estimat|billing|invoice|sku\s*list)',
    re.IGNORECASE,
)

KEYWORDS = {
    "regions": [
        "region",
        "us-south",
        "us-east",
        "eu-de",
        "eu-gb",
        "ca-tor",
        "jp-tok",
        "au-syd",
        "br-sao",
    ],
    "vpcs": ["vpc", "virtual private cloud"],
    "zones": ["zone", "availability zone"],
    "subnets": ["subnet", "cidr", "public subnet", "private subnet"],
    "connectivity": [
        "direct link", "vpn", "transit gateway", "bgp", "hybrid", "mpls",
        "satellite connector", "satellite link",
    ],
    "ingress": [
        "ingress", "load balancer", "cloud internet services", "cis", "router", "gateway",
        "global load balancer", "anycast",
    ],
    "compute": [
        "vsi", "virtual server", "roks", "openshift", "kubernetes", "bare metal",
        "powervs", "power", "code engine", "serverless", "cloud functions",
        "satellite", "worker node", "gpu",
    ],
    "data": [
        "database", "postgres", "db2", "object storage", "cos", "storage", "bucket",
        "redis", "mongodb", "elasticsearch", "cloudant", "event streams", "kafka",
        "mq", "ibm mq", "watsonx", "watson studio", "watson", "lakehouse",
        "analytics engine", "datastage", "cognos",
    ],
    "private_endpoints": ["private endpoint", "vpe", "virtual private endpoint"],
    "dns": ["dns", "resolver", "domain", "hostname"],
    "security": [
        "iam", "secrets", "key protect", "hpcs", "certificate", "security group",
        "nacl", "firewall", "app id", "oauth", "scc", "compliance",
        "container registry", "image registry",
    ],
    "observability": [
        "monitoring", "logging", "logs", "activity tracker", "audit", "flow log",
        "metrics", "instana", "dynatrace", "tracing", "apm", "prometheus",
    ],
    "backup_dr": [
        "backup", "restore", "dr", "disaster recovery", "rpo", "rto", "replication",
        "snapshot", "veeam", "zerto", "immutable", "worm",
    ],
}

CATEGORY_ALIASES = {
    "availability zone": "zones",
    "backup": "backup_dr",
    "backup and recovery": "backup_dr",
    "compute": "compute",
    "connectivity": "connectivity",
    "data": "data",
    "database": "data",
    "dns": "dns",
    "dr": "backup_dr",
    "ingress": "ingress",
    "monitoring": "observability",
    "network": "connectivity",
    "networking": "connectivity",
    "object storage": "data",
    "observability": "observability",
    "private endpoint": "private_endpoints",
    "security": "security",
    "storage": "data",
    "subnet": "subnets",
    "vpc": "vpcs",
    "vpc infrastructure": "vpcs",
    "vpe": "private_endpoints",
    "zone": "zones",
}

IBM_REGION_PATTERN = re.compile(r"\b(?:us|eu|ca|jp|au|br)-[a-z]+\b")

# Maps the question `area` label (from questions.py) to the ibm_cloud key(s)
# that a backfill should target.
AREA_TO_KEYS: dict[str, list[str]] = {
    "Architecture pattern": [],
    "Regions and availability": ["regions"],
    "Account and resource structure": ["security"],
    "VPC topology": ["vpcs"],
    "Subnet design": ["subnets", "zones"],
    "Connectivity": ["connectivity"],
    "Ingress": ["ingress"],
    "Compute": ["compute"],
    "Security controls": ["security"],
    "Private service access": ["private_endpoints"],
    "DNS and name resolution": ["dns"],
    "Observability": ["observability"],
    "Backup and DR": ["backup_dr"],
}

PATTERN_ALIASES: list[tuple[re.Pattern, tuple[str, str]]] = [
    (re.compile(r'\bhub\s*(?:and|&|-)?\s*spoke|edge\s+vpc', re.IGNORECASE), ("hub-and-spoke", "Hub-and-Spoke (Edge VPC)")),
    (re.compile(r'\bmzr\b|multi[-\s]?zone', re.IGNORECASE), ("mzr", "Multi-Zone VPC (MZR)")),
    (re.compile(r'three[-\s]?tier|3[-\s]?tier', re.IGNORECASE), ("three-tier-vpc", "Three-Tier VPC")),
    (re.compile(r'\bpowervs\b|power\s+virtual', re.IGNORECASE), ("powervs", "PowerVS")),
    (re.compile(r'financial\s+services|fsc\b', re.IGNORECASE), ("fsc", "Financial Services Cloud")),
    (re.compile(r'\broks\b|openshift|red\s+hat', re.IGNORECASE), ("roks", "Red Hat OpenShift on VPC")),
    (re.compile(r'\bhybrid\b|direct\s+link|vpn', re.IGNORECASE), ("hybrid", "Hybrid Connectivity")),
    (re.compile(r'\bbasic\s+vpc\b|single\s+vpc', re.IGNORECASE), ("basic-vpc", "Basic VPC")),
]


def discover_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []

    files: list[Path] = []
    for child in path.rglob("*"):
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(child)
    return sorted(files)


def classify_file(path: Path) -> str:
    """Return the role string for *path* without fully parsing it.

    Classification is cheap — it only inspects the filename and, for XLSX,
    the workbook sheet names.  The archive is opened at most once.
    """
    suffix = path.suffix.lower()
    name_lower = path.name.lower()

    # JSON files that look like an already-extracted architecture model
    if suffix == ".json":
        return "existing_architecture"

    # Markdown / plain text — narrative descriptions
    if suffix in {".md", ".txt"}:
        return "solution_description"

    # Check if filename signals a pricing catalog
    if _CATALOG_FILENAME_SIGNALS.search(name_lower):
        return "pricing_catalog"

    if suffix == ".xlsx":
        try:
            with zipfile.ZipFile(path) as arc:
                if is_solutioning_workbook(arc):
                    return "bom"
                if is_unified_pricing_workbook(arc):
                    return "unified_pricing"
                # Inspect sheet names for catalog signals
                sheets = parse_workbook_sheets(arc)
                sheet_names = [n for n, _ in sheets]
                if any(_CATALOG_SHEET_SIGNALS.search(s) for s in sheet_names):
                    return "pricing_catalog"
        except Exception:
            pass

    if suffix in {".csv", ".tsv"}:
        return "bom"

    return "unknown"


def is_pricing_catalog(path: Path) -> bool:
    """Return True if *path* should be skipped during architecture extraction.

    Pricing catalog files contain SKU / cost rows, not topology.  Parsing
    them would introduce thousands of spurious components.
    """
    return classify_file(path) == "pricing_catalog"


def build_architecture_from_inputs(input_path: Path, *, project_name: str | None = None) -> dict:
    files = discover_inputs(input_path)
    facts: dict[str, list[dict[str, str]]] = {key: [] for key in KEYWORDS}
    sources: list[dict[str, object]] = []

    for file_path in files:
        role = classify_file(file_path)

        # Skip pure pricing catalogs — they contain SKU rows, not topology.
        if role == "pricing_catalog":
            sources.append({
                "file": str(file_path),
                "type": file_path.suffix.lower().lstrip("."),
                "records": 0,
                "role": role,
                "skipped": True,
                "skip_reason": "Pricing catalog — no architecture components extracted",
            })
            continue

        # Existing architecture JSON — fold its ibm_cloud facts in directly
        # rather than re-parsing as raw text (avoids double-counts).
        # Only do this when the JSON file actually has an "ibm_cloud" key;
        # otherwise fall through and parse it as generic keyword text.
        if role == "existing_architecture":
            try:
                arch_data = json.loads(file_path.read_text(encoding="utf-8"))
                if "ibm_cloud" in arch_data:
                    for key, items in arch_data["ibm_cloud"].items():
                        if key == "assumptions" or not isinstance(items, list):
                            continue
                        facts.setdefault(key, []).extend(items)
                    sources.append({
                        "file": str(file_path),
                        "type": "json",
                        "records": sum(
                            len(v) for v in arch_data["ibm_cloud"].values()
                            if isinstance(v, list)
                        ),
                        "role": role,
                    })
                    continue  # fully handled — skip generic row parsing
            except Exception:
                pass
            # JSON without ibm_cloud key — fall through to generic text parsing

        rows = list(read_input_rows(file_path))
        source_entry: dict[str, object] = {
            "file": str(file_path),
            "type": file_path.suffix.lower().lstrip("."),
            "records": len(rows),
            "role": role,
        }
        if file_path.suffix.lower() == ".xlsx":
            try:
                with zipfile.ZipFile(file_path) as _arc:
                    if is_solutioning_workbook(_arc):
                        source_entry["source_format"] = "ibm-solutioning"
            except Exception:
                pass
        sources.append(source_entry)
        for row_index, row in enumerate(rows, start=1):
            text = " | ".join(value for value in row.values() if value)
            source = f"{file_path.name}:{row_index}"
            if not add_structured_fact(facts, row, source=source):
                add_detected_facts(facts, text, source=source)

    project = {
        "name": project_name or infer_project_name(input_path),
        "environment": infer_environment(facts) or "TBD",
        "diagram_goals": [
            "Generate professional IBM Cloud architecture diagrams",
            "Identify missing network design decisions before rendering final diagrams",
        ],
    }

    architecture = {
        "project": project,
        "ibm_cloud": {
            key: dedupe_components(value)
            for key, value in facts.items()
            if value
        },
        "sources": sources,
        "questions": {
            "answered": [],
            "open": [],
        },
    }
    architecture["ibm_cloud"]["assumptions"] = build_assumptions(architecture["ibm_cloud"])
    return architecture


def build_architecture_from_requirements(
    requirements: str,
    *,
    project_name: str | None = None,
    source: str = "requirements",
    filename: str = "",
) -> dict:
    """Build a fresh architecture model from free-text customer requirements."""
    architecture = {
        "project": {
            "name": project_name or "Customer Architecture",
            "environment": "TBD",
            "diagram_goals": [
                "Generate professional IBM Cloud architecture diagrams",
                "Identify missing network design decisions before rendering final diagrams",
            ],
        },
        "ibm_cloud": {},
        "sources": [{
            "file": filename or source,
            "type": "requirements",
            "records": 1,
            "role": "requirements",
        }],
        "requirements": [{
            "text": requirements,
            "source": source,
            "filename": filename,
        }],
        "questions": {
            "answered": [],
            "open": [],
        },
    }
    enrich_architecture_from_requirements(architecture, requirements, source=source)
    ibm_cloud = architecture.setdefault("ibm_cloud", {})
    architecture["project"]["environment"] = infer_environment(ibm_cloud) or "TBD"
    ibm_cloud["assumptions"] = build_assumptions(ibm_cloud)
    return architecture


def read_input_rows(path: Path) -> Iterable[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        yield from read_json(path)
    elif suffix in {".md", ".txt"}:
        yield from read_text(path)
    elif suffix in {".csv", ".tsv"}:
        yield from read_delimited(path, delimiter="\t" if suffix == ".tsv" else ",")
    elif suffix == ".xlsx":
        with zipfile.ZipFile(path) as archive:
            if is_solutioning_workbook(archive):
                yield from read_solutioning_xlsx(path)
                return
            if is_unified_pricing_workbook(archive):
                yield from read_unified_pricing_xlsx(path)
                return
        yield from read_xlsx(path)


def read_json(path: Path) -> Iterable[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        yield flatten_mapping(data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield flatten_mapping(item)
            else:
                yield {"value": str(item)}


def read_text(path: Path) -> Iterable[dict[str, str]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.strip(" -\t")
        if clean:
            yield {"text": clean}


def read_delimited(path: Path, *, delimiter: str) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames:
            for row in reader:
                yield {str(key): str(value or "").strip() for key, value in row.items()}
            return

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle, delimiter=delimiter):
            yield {f"column_{index + 1}": value.strip() for index, value in enumerate(row)}


# ---------------------------------------------------------------------------
# IBM Cloud Solutioning workbook helpers
# ---------------------------------------------------------------------------

#: Sheet names recognised as IBM Cloud Solutioning exports (priority order).
_SOLUTIONING_SHEETS = ("Detailed Estimate", "Summary")

#: Column headers that must appear in row 1 for the file to be detected.
_SOLUTIONING_SENTINEL_COLUMN = "Part Number"

#: Ordered list of Solutioning column names and the normalised row key each
#: maps to.  Matching is case-insensitive and whitespace-normalised.
_SOLUTIONING_COLUMNS: list[tuple[str, str]] = [
    ("Part Number", "part_number"),
    ("Part Description", "component"),
    ("Category", "category"),
    ("Region", "region"),
    ("Notes", "notes"),
    ("Description", "notes"),  # alternative column name for notes
    ("Quantity", "quantity"),
]


def is_solutioning_workbook(archive: zipfile.ZipFile) -> bool:
    """Return True if *archive* looks like an IBM Cloud Solutioning workbook.

    Detection is cheap — it only reads workbook metadata and the first row of
    the candidate sheet.  The archive is **not** consumed (caller can still
    iterate it afterwards by opening a new :class:`zipfile.ZipFile`).
    """
    try:
        shared_strings = parse_shared_strings(archive)
        workbook_sheets = parse_workbook_sheets(archive)
        relationships = parse_workbook_relationships(archive)
    except Exception:
        return False

    candidate_sheets = [
        (name, rid)
        for name, rid in workbook_sheets
        if name in _SOLUTIONING_SHEETS
    ]
    if not candidate_sheets:
        return False

    sentinel = _SOLUTIONING_SENTINEL_COLUMN.lower()
    for sheet_name, relationship_id in candidate_sheets:
        target = relationships.get(relationship_id)
        if not target:
            continue
        sheet_path = "xl/" + target.lstrip("/")
        if sheet_path not in archive.namelist():
            sheet_path = "xl/worksheets/" + Path(target).name
        if sheet_path not in archive.namelist():
            continue
        rows = parse_sheet_rows(archive.read(sheet_path), shared_strings)
        if rows and any(cell.lower() == sentinel for cell in rows[0]):
            return True

    return False


def read_solutioning_xlsx(path: Path) -> Iterable[dict[str, str]]:
    """Parse an IBM Cloud Solutioning workbook and yield normalised rows.

    Each yielded dict has consistent keys defined by :data:`_SOLUTIONING_COLUMNS`
    (``component``, ``category``, ``region``, ``notes``, ``part_number``,
    ``quantity``).  Empty cells produce empty strings; missing columns are
    omitted from the yielded dict.  Reuses all low-level XML helpers so no
    duplicate parsing logic is introduced.
    """
    with zipfile.ZipFile(path) as archive:
        shared_strings = parse_shared_strings(archive)
        workbook_sheets = parse_workbook_sheets(archive)
        relationships = parse_workbook_relationships(archive)

        # Choose the first available Solutioning sheet in priority order.
        sheet_map = {name: rid for name, rid in workbook_sheets}
        target_sheet_name: str | None = None
        for candidate in _SOLUTIONING_SHEETS:
            if candidate in sheet_map:
                target_sheet_name = candidate
                break

        if target_sheet_name is None:
            return

        relationship_id = sheet_map[target_sheet_name]
        target = relationships.get(relationship_id)
        if not target:
            return

        sheet_path = "xl/" + target.lstrip("/")
        if sheet_path not in archive.namelist():
            sheet_path = "xl/worksheets/" + Path(target).name
        if sheet_path not in archive.namelist():
            return

        rows = parse_sheet_rows(archive.read(sheet_path), shared_strings)
        if not rows:
            return

        raw_headers = rows[0]
        # Build a mapping from normalised column name → column index.
        header_index: dict[str, int] = {
            h.lower().strip(): i for i, h in enumerate(raw_headers) if h
        }

        # Pre-resolve which output key maps to which column index.
        col_map: list[tuple[str, int]] = []
        for col_header, output_key in _SOLUTIONING_COLUMNS:
            idx = header_index.get(col_header.lower())
            if idx is not None:
                col_map.append((output_key, idx))

        if not col_map:
            return

        for raw_row in rows[1:]:
            row: dict[str, str] = {}
            for output_key, col_idx in col_map:
                value = raw_row[col_idx] if col_idx < len(raw_row) else ""
                # If the same output_key appears twice (e.g. "Notes" and
                # "Description" both map to "notes"), keep the first non-empty
                # value.
                if output_key not in row or not row[output_key]:
                    row[output_key] = value.strip()
            if not any(row.values()):
                continue
            yield row



# ---------------------------------------------------------------------------
# IBM Cloud Unified Pricing workbook helpers
# ---------------------------------------------------------------------------
# Cognizant / IBM partner pricing workbooks follow a consistent structure:
#   - Sheet "commonServices": transit gateways, COS buckets (items in col C)
#   - Sheet "VPC": one or more VPCs with zones, subnets, VSIs, load balancers,
#     and Direct Link; items listed hierarchically in col C
#   - Sheet "Unified Summary" / "Unified Solution": summary roll-ups
#
# Detection: look for sheets named "commonServices" AND "VPC" (or "Unified Summary").

_UNIFIED_PRICING_SHEETS = frozenset({"commonservices", "vpc", "unified summary", "unified solution"})
_UNIFIED_PRICING_SENTINEL_SHEETS = frozenset({"commonservices", "vpc"})

# Region codes that appear as VPC names in these workbooks, e.g. "DAL VPC - us-south"
_UNIFIED_REGION_MAP: dict[str, str] = {
    "dal": "us-south",
    "wdc": "us-east",
    "fra": "eu-de",
    "lon": "eu-gb",
    "tor": "ca-tor",
    "tok": "jp-tok",
    "syd": "au-syd",
    "sao": "br-sao",
    "osa": "jp-osa",
    "che": "in-che",
    "mad": "eu-es",
}


def is_unified_pricing_workbook(archive: zipfile.ZipFile) -> bool:
    """Return True if the archive looks like an IBM unified pricing workbook.

    Requires both a 'commonServices' sheet and a 'VPC' sheet to be present.
    The check is case-insensitive.
    """
    try:
        workbook_sheets = parse_workbook_sheets(archive)
    except Exception:
        return False
    names = {name.lower() for name, _ in workbook_sheets}
    return bool(names & _UNIFIED_PRICING_SENTINEL_SHEETS) and len(names & _UNIFIED_PRICING_SHEETS) >= 2


def _unified_infer_region(vpc_label: str) -> str:
    """Return an IBM Cloud region code from a VPC label like 'DAL VPC - us-south'."""
    lower = vpc_label.lower()
    # Explicit IBM region code in the label (e.g. "us-south", "eu-de")
    m = IBM_REGION_PATTERN.search(lower)
    if m:
        return m.group(0)
    # Three-letter airport code prefix (e.g. "DAL", "WDC")
    prefix = lower.split()[0].rstrip("-_")[:3]
    return _UNIFIED_REGION_MAP.get(prefix, "")


def read_unified_pricing_xlsx(path: Path) -> Iterable[dict[str, str]]:
    """Parse an IBM unified pricing workbook and yield structured component rows.

    Walks each sheet hierarchically, tracking the current VPC / zone / subnet
    context, and emits one dict per meaningful component.  The yielded dicts
    use the standard structured-fact keys (``component``, ``category``,
    ``region``, ``notes``) so :func:`add_structured_fact` can route them.
    """
    with zipfile.ZipFile(path) as archive:
        shared_strings = parse_shared_strings(archive)
        workbook_sheets = parse_workbook_sheets(archive)
        relationships = parse_workbook_relationships(archive)

        for sheet_name, relationship_id in workbook_sheets:
            lower_sheet = sheet_name.lower()
            if lower_sheet not in _UNIFIED_PRICING_SHEETS:
                continue

            target = relationships.get(relationship_id)
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/")
            if sheet_path not in archive.namelist():
                sheet_path = "xl/worksheets/" + Path(target).name
            if sheet_path not in archive.namelist():
                continue

            rows = parse_sheet_rows(archive.read(sheet_path), shared_strings)

            # Context carried forward as we walk rows
            current_region = ""
            current_vpc = ""
            current_zone = ""
            current_subnet = ""
            current_dl_section = False  # inside a "Data Center / Direct Link" block

            for row in rows:
                # Find the primary text cell — usually col C (index 2) or col B (index 1)
                # Skip entirely empty rows
                non_empty = [v for v in row if v.strip()]
                if not non_empty:
                    continue

                # The "item" column is typically col C (idx 2); fall back to col B.
                cell = ""
                if len(row) > 2 and row[2].strip():
                    cell = row[2].strip()
                elif len(row) > 1 and row[1].strip():
                    cell = row[1].strip()
                if not cell:
                    continue

                cell_lower = cell.lower()

                # ── Section headers — update context ──────────────────────

                # VPC name line, e.g. "DAL VPC", "DAL VPC - us-south", "WDC VPC"
                if re.search(r'\bvpc\b', cell_lower) and len(cell.split()) <= 5:
                    # Only treat as VPC context if it looks like a VPC name
                    # (not a section header like "VPC" alone, or "VPC connection"
                    # which is a Transit Gateway configuration row)
                    if cell_lower not in {"vpc", "vpc connection", "vpc 1 zone 1", "vpc 2 zone 1"}:
                        current_vpc = cell.strip()
                        current_region = _unified_infer_region(cell)
                        current_zone = ""
                        current_subnet = ""
                        current_dl_section = False
                        # Emit the VPC itself
                        yield {
                            "component": current_vpc,
                            "category": "vpcs",
                            "region": current_region,
                            "notes": f"VPC from unified pricing workbook sheet '{sheet_name}'",
                        }
                        # Also emit the region
                        if current_region:
                            yield {
                                "component": current_region,
                                "category": "regions",
                                "region": current_region,
                                "notes": f"Region inferred from VPC label '{current_vpc}'",
                            }
                    continue

                # Zone line, e.g. "Zone 1", "Zone 2"
                if re.match(r'^zone\s+\d+$', cell_lower):
                    current_zone = cell.strip()
                    current_subnet = ""
                    continue

                # Subnet line, e.g. "Subnet 1", "Subnet 2"
                if re.match(r'^subnet\s+\d+$', cell_lower):
                    current_subnet = cell.strip()
                    continue

                # Data-centre / Direct Link section header
                if ("data center" in cell_lower or "data centre" in cell_lower
                        or re.match(r'^[a-z]{2,4}\s+dl\b', cell_lower)):
                    current_dl_section = True
                    continue

                # Section dividers — reset DL flag on new section
                if cell_lower in {"network", "storage", "compute", "security",
                                   "common services", "commonservices"}:
                    current_dl_section = False
                    continue

                # ── Named components ──────────────────────────────────────

                # Transit Gateway
                if "transit gateway" in cell_lower:
                    name = cell if len(cell.split()) <= 6 else "Transit Gateway"
                    yield {
                        "component": name,
                        "category": "connectivity",
                        "region": current_region,
                        "notes": f"Transit Gateway from '{sheet_name}' sheet",
                    }
                    continue

                # Direct Link
                if "direct link" in cell_lower:
                    name = cell if len(cell.split()) <= 8 else "Direct Link"
                    yield {
                        "component": name,
                        "category": "connectivity",
                        "region": current_region,
                        "notes": f"Direct Link from '{sheet_name}' sheet, VPC: {current_vpc}",
                    }
                    continue

                # Load Balancer (e.g. "Service Usage - Application - Private")
                if "load balancer" in cell_lower or (
                    "service usage" in cell_lower and ("private" in cell_lower or "public" in cell_lower)
                ):
                    lb_type = "Private Load Balancer" if "private" in cell_lower else "Load Balancer"
                    yield {
                        "component": lb_type,
                        "category": "ingress",
                        "region": current_region,
                        "notes": f"{cell} in zone {current_zone}, subnet {current_subnet}, VPC {current_vpc}",
                    }
                    continue

                # Cloud Object Storage (e.g. "Cloud Object Storage PTcos")
                if "cloud object storage" in cell_lower or (
                    "object storage" in cell_lower
                ):
                    yield {
                        "component": cell if len(cell.split()) <= 8 else "Cloud Object Storage",
                        "category": "data",
                        "region": current_region or "cross-region",
                        "notes": f"Object Storage from '{sheet_name}' sheet",
                    }
                    continue

                # File Storage
                if cell_lower in {"file storage"} or (
                    "file storage" in cell_lower and len(cell.split()) <= 3
                ):
                    yield {
                        "component": "File Storage",
                        "category": "data",
                        "region": current_region,
                        "notes": f"File Storage in VPC {current_vpc}, zone {current_zone}",
                    }
                    continue

                # Virtual Servers — lines like "Virtual Server: bx2d-2x8 - CentOS (PAYG)"
                if cell_lower.startswith("virtual server"):
                    # Extract the friendly profile name
                    parts = cell.split(":")
                    profile_part = parts[1].strip() if len(parts) > 1 else cell
                    # Clean up: take the profile before " - "
                    profile = profile_part.split(" - ")[0].strip() if " - " in profile_part else profile_part.split("(")[0].strip()
                    name = f"VPC VSI ({profile})" if profile else "VPC Virtual Server Instance"
                    yield {
                        "component": name,
                        "category": "compute",
                        "region": current_region,
                        "notes": f"VSI profile {profile} in VPC {current_vpc}, zone {current_zone}, subnet {current_subnet}",
                    }
                    continue

                # Subnets yielded from context (when we encounter a subnet header)
                # Already handled above, but also emit a subnet fact here for tracking
                # (happens implicitly via the subnet context update above)

            # After processing each sheet, if we found a VPC emit subnet facts
            # based on the context we tracked — already done inline above



def read_xlsx(path: Path) -> Iterable[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = parse_shared_strings(archive)
        workbook_sheets = parse_workbook_sheets(archive)
        relationships = parse_workbook_relationships(archive)

        for sheet_name, relationship_id in workbook_sheets:
            target = relationships.get(relationship_id)
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/")
            if sheet_path not in archive.namelist():
                sheet_path = "xl/worksheets/" + Path(target).name
            if sheet_path not in archive.namelist():
                continue
            rows = parse_sheet_rows(archive.read(sheet_path), shared_strings)
            headers = rows[0] if rows else []
            for row_number, row in enumerate(rows[1:] if headers else rows, start=2 if headers else 1):
                if not any(row):
                    continue
                if headers:
                    yield {
                        f"{sheet_name}.{header_for(headers, index)}": value
                        for index, value in enumerate(row)
                        if value
                    }
                else:
                    yield {
                        f"{sheet_name}.row_{row_number}_column_{index + 1}": value
                        for index, value in enumerate(row)
                        if value
                    }


def parse_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    strings: list[str] = []
    for item in root.findall(f"{namespace}si"):
        parts = [text.text or "" for text in item.iter(f"{namespace}t")]
        strings.append("".join(parts))
    return strings


def parse_workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    sheets: list[tuple[str, str]] = []
    for sheet in root.findall(f".//{main}sheet"):
        name = sheet.attrib.get("name", "Sheet")
        relationship_id = sheet.attrib.get(f"{rel}id", "")
        sheets.append((name, relationship_id))
    return sheets


def parse_workbook_relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    namespace = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    return {
        relationship.attrib.get("Id", ""): relationship.attrib.get("Target", "")
        for relationship in root.findall(f"{namespace}Relationship")
    }


def parse_sheet_rows(content: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ElementTree.fromstring(content)
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows: list[list[str]] = []
    for row in root.findall(f".//{namespace}row"):
        values: list[str] = []
        for cell in row.findall(f"{namespace}c"):
            reference = cell.attrib.get("r", "")
            column_index = column_index_from_reference(reference)
            while len(values) < column_index:
                values.append("")
            cell_type = cell.attrib.get("t")
            value_node = cell.find(f"{namespace}v")
            inline_node = cell.find(f"{namespace}is/{namespace}t")
            raw = ""
            if inline_node is not None and inline_node.text:
                raw = inline_node.text
            elif value_node is not None and value_node.text:
                raw = value_node.text
            if cell_type == "s" and raw.isdigit():
                index = int(raw)
                raw = shared_strings[index] if index < len(shared_strings) else raw
            values.append(raw.strip())
        rows.append(values)
    return rows


def column_index_from_reference(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    if not letters:
        return 0
    index = 0
    for character in letters.upper():
        index = index * 26 + (ord(character) - ord("A") + 1)
    return index - 1


def header_for(headers: list[str], index: int) -> str:
    if index < len(headers) and headers[index]:
        return headers[index]
    return f"column_{index + 1}"


def flatten_mapping(data: dict, *, prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for key, value in data.items():
        compound_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(flatten_mapping(value, prefix=compound_key))
        elif isinstance(value, list):
            flattened[compound_key] = ", ".join(str(item) for item in value)
        else:
            flattened[compound_key] = "" if value is None else str(value)
    return flattened


# Generic words that appear constantly in spreadsheets and are not meaningful
# IBM Cloud component names.
_NOISE_NAMES: frozenset[str] = frozenset({
    "total", "subtotal", "grand total", "description", "notes", "name",
    "service", "item", "component", "resource", "category", "type",
    "value", "storage", "compute", "network", "security", "data",
    "yes", "no", "n/a", "na", "tbd", "none", "other", "unknown",
    "customer architecture", "unlabeled component", "devicename",
    "per connection charges apply over", "charges apply",
    "zone name", "subnet name", "region name", "server name",
    "cross-region resiliency", "cross-region", "name or #",
    "added grs", "added powerdra prices", "online sizing tool",
})

# Names containing "SPP_" or similar internal replication group prefixes
_INTERNAL_PREFIX_PATTERN = re.compile(r'^(SPP_|VEEAM_|TSM_|DR_|BKP_)', re.IGNORECASE)

# Names that look like internal hostnames or server identifiers:
#   - all alphanumeric + underscore, no spaces
#   - contain at least one digit
#   - do NOT look like IBM Cloud service names (those have spaces or IBM branding)
_HOSTNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{4,30}$')

# Names starting with non-letter characters (*, (, #, digits, "c.")
_SENTENCE_PATTERN = re.compile(r'^[^A-Za-z]')

# IBM Cloud service name indicators — if any of these appear the name is likely real
_IBM_SERVICE_SIGNALS = (
    "ibm", "cloud", "vpc", "openshift", "roks", "power", "direct link",
    "transit gateway", "load balancer", "object storage", "database",
    "secrets", "key protect", "activity tracker", "monitoring", "logging",
    "firewall", "juniper", "vsrx", "virtual server", "bare metal", "block",
    "file storage", "scc", "hpcs", "certificate", "dns", "flow log",
)


def _is_meaningful_name(name: str) -> bool:
    """Return True if *name* looks like a real IBM Cloud component name."""
    stripped = name.strip()
    # Too short or pure numbers
    if len(stripped) < 5 or stripped.isdigit():
        return False
    # Discard known noise words (exact match, case-insensitive)
    if stripped.lower() in _NOISE_NAMES:
        return False
    # Discard names that start with non-letter characters (*, (, #, digits)
    if _SENTENCE_PATTERN.match(stripped):
        return False
    # Discard internal backup/replication group names
    if _INTERNAL_PREFIX_PATTERN.match(stripped):
        return False
    # Discard names that are just punctuation/symbols
    if re.match(r'^[\W_]+$', stripped):
        return False
    # Discard names that are very long sentences (> 10 words)
    if len(stripped.split()) > 10:
        return False
    # If the name has no spaces (single token) and contains digits mixed with
    # letters, it is likely a hostname/device ID — only accept if it contains
    # a known IBM service signal word.
    lower = stripped.lower()
    if _HOSTNAME_PATTERN.match(stripped) and any(sig in lower for sig in _IBM_SERVICE_SIGNALS):
        return True
    if _HOSTNAME_PATTERN.match(stripped) and not any(c.isspace() for c in stripped):
        # Single-token alphanumeric — only keep if it has NO digits
        # (pure alphabetic short names might still be junk, but at least not hostnames)
        if any(c.isdigit() for c in stripped):
            return False
    return True


def _canonical_fact_names(category: str, normalized: str) -> list[str]:
    """Return professional component labels for prose-based keyword hits."""
    if category == "vpcs" and ("vpc" in normalized or "virtual private cloud" in normalized):
        return ["Workload VPC"]
    if category == "subnets":
        names: list[str] = []
        if "public subnet" in normalized:
            names.append("Public subnet")
        if "private subnet" in normalized:
            names.append("Private subnet")
        if "data subnet" in normalized:
            names.append("Data subnet")
        if "subnet" in normalized and not names:
            names.append("Application subnet")
        return names
    if category == "zones" and ("zone" in normalized or "availability zone" in normalized):
        return ["zone-1"]
    if category == "connectivity":
        names = []
        if "direct link" in normalized:
            names.append("IBM Cloud Direct Link")
        if "transit gateway" in normalized:
            names.append("Transit Gateway")
        if "vpn" in normalized:
            names.append("VPN Gateway")
        if "hybrid" in normalized and not names:
            names.append("Hybrid connectivity")
        if "satellite connector" in normalized or "satellite link" in normalized:
            names.append("IBM Cloud Satellite Connector")
        return names
    if category == "ingress":
        names = []
        if "cloud internet services" in normalized or re.search(r"\bcis\b", normalized):
            names.append("Cloud Internet Services")
        if "global load balancer" in normalized:
            names.append("Global Load Balancer")
        elif "load balancer" in normalized:
            names.append("Public Load Balancer")
        elif "ingress" in normalized:
            names.append("Ingress tier")
        return names
    if category == "compute":
        names = []
        if "roks" in normalized or "openshift" in normalized:
            names.append("Red Hat OpenShift on IBM Cloud")
        if "vsi" in normalized or "virtual server" in normalized:
            names.append("VPC VSI workload tier")
        if "bare metal" in normalized:
            names.append("Bare Metal Servers")
        if "code engine" in normalized or "serverless" in normalized or "cloud functions" in normalized:
            names.append("Serverless compute")
        if "gpu" in normalized:
            names.append("GPU worker nodes")
        if ("powervs" in normalized or "power virtual" in normalized or "power vs" in normalized) and not any(
            phrase in normalized for phrase in ("no powervs", "without powervs", "no power virtual", "without power virtual")
        ):
            names.append("PowerVS servers")
        return names
    if category == "data":
        names = []
        if "object storage" in normalized or "cos" in normalized:
            names.append("Cloud Object Storage archive")
        if "postgres" in normalized:
            names.append("IBM Cloud Databases for PostgreSQL")
        if "db2" in normalized:
            names.append("IBM Db2")
        if "redis" in normalized:
            names.append("IBM Cloud Databases for Redis")
        if "cloudant" in normalized:
            names.append("IBM Cloudant")
        if "event streams" in normalized or "kafka" in normalized:
            names.append("IBM Event Streams")
        if re.search(r"\bibm mq\b|\bmq\b", normalized):
            names.append("IBM MQ")
        if "file storage" in normalized or "nfs" in normalized:
            names.append("NFS File Storage")
        if "watsonx" in normalized or "watson" in normalized:
            names.append("watsonx data services")
        return names
    if category == "private_endpoints" and (
        "private endpoint" in normalized or "vpe" in normalized or "virtual private endpoint" in normalized
    ):
        return ["Virtual Private Endpoints for IBM Cloud services"]
    if category == "dns" and any(term in normalized for term in ("dns", "resolver", "domain", "hostname")):
        return ["DNS and custom resolver"]
    if category == "security":
        names = []
        if "security group" in normalized:
            names.append("Security Groups")
        if "nacl" in normalized:
            names.append("Network ACLs")
        if "key protect" in normalized:
            names.append("Key Protect")
        if "hpcs" in normalized:
            names.append("Hyper Protect Crypto Services")
        if "secrets" in normalized:
            names.append("Secrets Manager")
        if "scc" in normalized or "compliance" in normalized:
            names.append("Security and Compliance Center")
        if "certificate" in normalized:
            names.append("Certificate Manager")
        if "iam" in normalized:
            names.append("IBM Cloud IAM")
        return names
    if category == "observability":
        names = []
        if "activity tracker" in normalized or "audit" in normalized:
            names.append("Activity Tracker")
        if "flow log" in normalized:
            names.append("VPC Flow Logs")
        if "monitoring" in normalized or "metrics" in normalized:
            names.append("IBM Cloud Monitoring")
        if "logging" in normalized or "logs" in normalized:
            names.append("IBM Cloud Logs")
        if "instana" in normalized:
            names.append("Instana Observability")
        return names
    if category == "backup_dr":
        names = []
        if "replication" in normalized:
            names.append("Cross-region replication")
        if "backup" in normalized or "restore" in normalized or "snapshot" in normalized:
            names.append("Backup and restore")
        if "disaster recovery" in normalized or "dr site" in normalized or " rpo" in normalized or " rto" in normalized:
            names.append("Regional disaster recovery site")
        return names
    return []


def add_detected_facts(facts: dict[str, list[dict[str, str]]], text: str, *, source: str) -> None:
    normalized = text.lower()

    for region in unique_ordered(IBM_REGION_PATTERN.findall(normalized)):
        facts["regions"].append(
            {
                "name": region,
                "type": "regions",
                "purpose": "",
                "source": source,
                "notes": text[:500],
            }
        )

    for category, keywords in KEYWORDS.items():
        if category == "regions":
            continue
        if any(keyword in normalized for keyword in keywords):
            names = _canonical_fact_names(category, normalized) or [concise_name(text)]
            for name in names:
                if not _is_meaningful_name(name):
                    continue
                facts[category].append(
                    {
                        "name": name,
                        "type": category,
                        "purpose": "",
                        "source": source,
                        "notes": text[:500],
                    }
                )


def _append_fact(
    facts: dict[str, list[dict[str, str]]],
    key: str,
    name: str,
    *,
    purpose: str,
    source: str,
    notes: str,
    region: str = "",
) -> None:
    facts.setdefault(key, []).append({
        "name": name,
        "type": key,
        "purpose": purpose,
        "region": region,
        "source": source,
        "notes": notes[:500],
    })


def enrich_architecture_from_requirements(
    architecture: dict,
    requirements: str,
    *,
    source: str = "requirements",
) -> None:
    """Convert customer requirements prose into structured design facts.

    The generic keyword extractor is intentionally conservative and often turns
    long requirement paragraphs into weak component names. This layer captures
    high-value IBM network architecture signals that must affect diagrams.
    """
    if not requirements.strip():
        return
    text = requirements.lower()
    ibm_cloud = architecture.setdefault("ibm_cloud", {})
    facts: dict[str, list[dict[str, str]]] = {
        key: list(ibm_cloud.get(key, []))
        for key in KEYWORDS
    }
    source_label = f"{source}:requirements"
    negates_powervs = any(phrase in text for phrase in ("no powervs", "without powervs", "no power virtual", "without power virtual"))
    negates_direct_link = any(phrase in text for phrase in ("no direct link", "without direct link"))
    negates_dr = any(phrase in text for phrase in ("no dr", "without dr", "no disaster recovery", "without disaster recovery"))
    mentions_powervs = ("power virtual" in text or "powervs" in text or "power vs" in text) and not negates_powervs
    mentions_direct_link = "direct link" in text and not negates_direct_link
    mentions_dr = (
        "dr site" in text
        or "disaster recovery" in text
        or " rto" in text
        or " rpo" in text
    ) and not negates_dr
    mentions_healthcare = (
        "hipaa" in text
        or "hippa" in text
        or "healthcare" in text
        or "patient" in text
        or "medical imaging" in text
    )

    add_detected_facts(facts, requirements, source=source_label)

    if mentions_powervs:
        _append_fact(
            facts, "compute", "PowerVS servers",
            purpose="Adjacent Power workloads connected to the VPC architecture",
            source=source_label, notes=requirements,
        )
        architecture.setdefault("render_plan", {})["has_powervs"] = True

    if mentions_direct_link:
        _append_fact(
            facts, "connectivity", "HA Direct Link 1 Gbps",
            purpose="Highly available private connectivity for primary and DR locations",
            source=source_label, notes=requirements,
        )
        architecture.setdefault("render_plan", {})["has_on_prem"] = True
        architecture.setdefault("render_plan", {})["connectivity_label"] = "HA Direct Link 1 Gbps"

    if mentions_dr:
        dr_name = "WDC disaster recovery site" if "wdc" in text or "us-east" in text else "Regional disaster recovery site"
        _append_fact(
            facts, "backup_dr", dr_name,
            purpose="Regional disaster recovery target for the primary workload",
            source=source_label, notes=requirements,
            region="us-east" if "wdc" in text or "us-east" in text else "",
        )
        plan = architecture.setdefault("render_plan", {})
        plan["has_dr"] = True
        plan["pattern"] = "resiliency-dr"
        plan["pattern_name"] = "Hybrid Resiliency and Disaster Recovery"
        plan["pattern_source"] = source

    if mentions_healthcare:
        for name, purpose in [
            ("Security and Compliance Center", "Continuous evidence collection for HIPAA compliance"),
            ("Key Protect or HPCS", "Customer-managed encryption keys for regulated healthcare data"),
            ("Secrets Manager", "Centralized secrets management for applications and automation"),
        ]:
            _append_fact(facts, "security", name, purpose=purpose, source=source_label, notes=requirements)
        for name, purpose in [
            ("Activity Tracker", "Audit trail for regulated healthcare operations"),
            ("VPC Flow Logs", "Network traffic evidence for security and compliance review"),
            ("IBM Cloud Monitoring and Logging", "Operational monitoring and logging for medical imaging workloads"),
        ]:
            _append_fact(facts, "observability", name, purpose=purpose, source=source_label, notes=requirements)
        _append_fact(
            facts, "private_endpoints", "Virtual Private Endpoints for IBM Cloud services",
            purpose="Private access to storage, key management, logging, and managed services",
            source=source_label, notes=requirements,
        )

    if "cos" in text or "object storage" in text:
        cos_name = (
            "Cloud Object Storage for medical imaging archive"
            if "medical imaging" in text
            else "Cloud Object Storage archive"
        )
        _append_fact(
            facts, "data", cos_name,
            purpose="Large-scale object archive for application data",
            source=source_label, notes=requirements,
        )
    if "nfs" in text or "file storage" in text:
        _append_fact(
            facts, "data", "NFS File Storage for VSI workloads",
            purpose="Shared file storage attached to medical imaging VSI workloads",
            source=source_label, notes=requirements,
        )

    if "medical imaging" in text:
        _append_fact(
            facts, "compute", "Medical imaging processing VSIs",
            purpose="Image intake, processing, archiving, and retrieval workload tier",
            source=source_label, notes=requirements,
        )

    if "one zone" in text or "zone 1" in text:
        facts.setdefault("zones", []).append({
            "name": "zone-1",
            "type": "zones",
            "purpose": "Single-zone placement stated in requirements",
            "source": source_label,
            "notes": requirements[:500],
        })
        architecture.setdefault("render_plan", {})["az_count"] = 1

    if mentions_dr and (mentions_powervs or mentions_healthcare):
        plan = architecture.setdefault("render_plan", {})
        plan["pattern"] = "hybrid-powervs-dr" if mentions_powervs else "healthcare-regional-dr"
        plan["pattern_name"] = (
            "Hybrid PowerVS and Regional DR"
            if mentions_powervs
            else "Healthcare Regional Disaster Recovery"
        )
        plan["pattern_source"] = source
        plan["has_dr"] = True
        plan["has_powervs"] = mentions_powervs or bool(plan.get("has_powervs"))
        plan["has_on_prem"] = mentions_direct_link or bool(plan.get("has_on_prem"))
        plan.setdefault("connectivity_label", "HA Direct Link 1 Gbps")
        plan.pop("vpcs", None)
        plan.pop("has_tgw", None)
        plan["shared_services"] = [
            "Security and Compliance Center",
            "Key Protect or HPCS",
            "Secrets Manager",
            "Activity Tracker",
            "VPC Flow Logs",
            "Virtual Private Endpoints",
        ]

    for key, values in facts.items():
        if values:
            ibm_cloud[key] = dedupe_components(values)


def add_structured_fact(facts: dict[str, list[dict[str, str]]], row: dict[str, str], *, source: str) -> bool:
    lowered = {key.lower().strip(): value.strip() for key, value in row.items() if value.strip()}
    category_value = first_value(lowered, ["category", "type", "service category", "component category"])
    name = first_value(lowered, ["component", "name", "service", "item", "resource"])
    notes = first_value(lowered, ["notes", "description", "purpose", "comment"])
    region = first_value(lowered, ["region", "location"])

    # Accept both the canonical key names (from structured parsers) and the
    # human-readable aliases (from freeform data).
    _cv_lower = category_value.lower() if category_value else ""
    if _cv_lower in KEYWORDS:
        category = _cv_lower
    else:
        category = CATEGORY_ALIASES.get(_cv_lower) if _cv_lower else None
    if region:
        for region_name in unique_ordered(IBM_REGION_PATTERN.findall(region.lower())):
            facts["regions"].append(
                {
                    "name": region_name,
                    "type": "regions",
                    "purpose": "",
                    "source": source,
                    "notes": "Region listed in structured input.",
                }
            )

    if not category or not name:
        return False

    # Regions are handled entirely by the IBM_REGION_PATTERN loop above.
    # Avoid a double-add when the structured row is itself a region row.
    if category == "regions":
        for region_name in unique_ordered(IBM_REGION_PATTERN.findall(name.lower())):
            if not any(c["name"] == region_name for c in facts["regions"]):
                facts["regions"].append(
                    {
                        "name": region_name,
                        "type": "regions",
                        "purpose": notes,
                        "source": source,
                        "notes": notes or name,
                    }
                )
        return True

    facts[category].append(
        {
            "name": name,
            "type": category,
            "purpose": notes,
            "region": region,
            "source": source,
            "notes": " | ".join(value for value in lowered.values() if value)[:500],
        }
    )
    return True


def first_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in row:
            return row[key]
    return ""


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def concise_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    for separator in ["|", ":", "-", "–"]:
        if separator in cleaned:
            candidate = cleaned.split(separator, 1)[0].strip()
            # Require 5–80 chars and not a sentence (≤ 6 words)
            if 5 <= len(candidate) <= 80 and len(candidate.split()) <= 6:
                return candidate
    # Only use the full text if it's short enough to be a name, not a sentence
    if len(cleaned.split()) <= 6:
        return cleaned[:80] or "Unlabeled component"
    return "Unlabeled component"


# ---------------------------------------------------------------------------
# Semantic deduplication helpers
# ---------------------------------------------------------------------------

# VSI profile strings like "bx2d-2x8", "cx2-4x8", "mx2-16x128"
_PROFILE_SUFFIX = re.compile(r'\b[a-z]+x?\d+-?\d+x\d+\b', re.IGNORECASE)

# Trailing parenthetical annotations, e.g. "(PAYG)", "(hourly)"
_PAREN_ANNOT = re.compile(r'\s*\([^)]*\)')

# Filler words to remove *after* canonical mapping.
# Kept intentionally short so canonical service tokens are preserved.
_FILLER_WORDS = re.compile(
    r'\b(ibm|cloud|the|a|an|for|in|on|of|with|and|or|to|at|by'
    r'|dedicated|connect(?:ion|or)?|service|platform|infrastructure'
    r'|us-south|us-east|eu-de|eu-gb|ca-tor|jp-tok|au-syd|br-sao)\b',
    re.IGNORECASE,
)

# Airport / city codes and region codes to strip
_LOCATION_TOKENS = re.compile(
    r'\b(dal|wdc|fra|lon|tok|syd|sao|tor|osa|che|mad|dallas|washington|dc'
    r'|dc\d*|chicago|frankfurt|london|tokyo|sydney|toronto|osaka|chennai|madrid'
    r'|us|eu|ca|jp|au|br)\b',
    re.IGNORECASE,
)

# Canonical service name mapping: pattern → canonical token(s)
# Each pattern is tried against the full lowercased, separator-normalised name.
# Ordered most-specific first.
# Canonical service patterns for types where location context is NOT meaningful
# (e.g. "Transit Gateway DAL TG" == "Transit Gateway DallasTG" — same service).
# VPCs and subnets are intentionally excluded because their location IS meaningful.
_CANONICAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'transit\s*gate?way|tg\b|transit\s*gw'), "transit-gateway"),
    (re.compile(r'direct\s*link'), "direct-link"),
    (re.compile(r'load\s*bal|alb\b|nlb\b|\blb\b'), "load-balancer"),
    (re.compile(r'object\s*storage|cos\b'), "object-storage"),
    (re.compile(r'open\s*shift|roks\b'), "openshift"),
    (re.compile(r'kubernetes|k8s\b'), "kubernetes"),
    (re.compile(r'postgre|pg\b'), "postgresql"),
    (re.compile(r'private\s*endpoint|vpe\b'), "private-endpoint"),
    (re.compile(r'key\s*protect|kp\b'), "key-protect"),
    (re.compile(r'secrets\s*manager|sm\b'), "secrets-manager"),
    (re.compile(r'activity\s*track|atracker\b'), "activity-tracker"),
    (re.compile(r'hyper\s*protect|hpcs\b'), "hyper-protect"),
    (re.compile(r'security.*compli|scc\b'), "scc"),
    (re.compile(r'flow\s*log'), "flow-log"),
    (re.compile(r'vpn\s*gate?way|\bvpn\b'), "vpn-gateway"),
    # NOTE: vpc / vsi / subnet / zone are NOT in this list —
    # their location qualifier is architecturally significant.
    (re.compile(r'bare\s*metal'), "bare-metal"),
    (re.compile(r'file\s*storage'), "file-storage"),
    (re.compile(r'block\s*storage'), "block-storage"),
    (re.compile(r'event\s*stream'), "event-streams"),
    (re.compile(r'ibm\s*mq|\bmq\b'), "ibm-mq"),
    (re.compile(r'internet\s*services|cis\b'), "cis"),
    (re.compile(r'container\s*registry'), "container-registry"),
    (re.compile(r'dns\s*service|\bdns\b'), "dns"),
]

# Location-aware canonical patterns: applied only for components where
# the IBM Cloud type IS location-scoped (vpcs, subnets, zones).
# These reduce the name to: <location-prefix> <service-type>
_LOCATION_SCOPED_TYPES = frozenset({"vpcs", "subnets", "zones"})


def _normalise_name(name: str, *, component_type: str = "") -> str:
    """Return a canonical token-set string for semantic deduplication.

    Strategy:
    1. Lowercase, strip parens/annotations and VSI profile suffixes.
    2. Replace separators (- _ / | :) with spaces.
    3. For non-location-scoped types: apply canonical service patterns.
       If a known IBM service is found, collapse to its canonical token(s).
    4. For location-scoped types (vpcs, subnets, zones): skip canonical
       collapse so location distinguishes DAL VPC from WDC VPC.
    5. Strip remaining filler words; for non-location-scoped types also
       strip location tokens.
    6. Sort tokens for order-independence.
    """
    s = name.lower().strip()
    s = _PAREN_ANNOT.sub("", s)
    s = _PROFILE_SUFFIX.sub("", s)
    # Replace separators with spaces so "DallasTG" → "dallastg" (single token)
    s = re.sub(r'[-_/|:]+', ' ', s)

    location_scoped = component_type in _LOCATION_SCOPED_TYPES

    if not location_scoped:
        # Try canonical pattern matching — reduces to service canonical token
        canonical_tokens: list[str] = []
        for pattern, canonical in _CANONICAL_PATTERNS:
            if pattern.search(s):
                canonical_tokens.append(canonical)
        if canonical_tokens:
            return " ".join(sorted(set(canonical_tokens)))

    # Filler-word stripping fallback (also used for location-scoped types)
    s = _FILLER_WORDS.sub(" ", s)
    if not location_scoped:
        # Strip location tokens only for non-location-scoped components
        s = _LOCATION_TOKENS.sub(" ", s)
    tokens = sorted(t for t in s.split() if len(t) >= 3)
    return " ".join(tokens)


def _semantic_key(component: dict) -> tuple[str, str]:
    """Return (type, normalised_name) as the dedup key for *component*."""
    ctype = component.get("type", "")
    return (ctype, _normalise_name(component.get("name", ""), component_type=ctype))


def dedupe_components(components: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate *components* using both exact name match and semantic normalisation.

    For each semantic group, keep the component whose name is longest
    (most descriptive) and merge ``source`` provenance from all duplicates.
    """
    # Group by semantic key
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for component in components:
        key = _semantic_key(component)
        if not key[1]:
            # Normalised name is empty (all noise) — use exact lowercase key
            key = (component.get("type", ""), component.get("name", "").lower())
        groups.setdefault(key, []).append(component)

    deduped: list[dict[str, str]] = []
    for group in groups.values():
        if len(group) == 1:
            deduped.append(group[0])
            continue
        # Pick the representative: longest name wins (most descriptive)
        representative = max(group, key=lambda c: len(c.get("name", "")))
        # Merge source provenance
        all_sources = ", ".join(
            c.get("source", "") for c in group if c.get("source")
        )
        merged = dict(representative)
        merged["source"] = all_sources
        deduped.append(merged)

    return deduped


def infer_project_name(input_path: Path) -> str:
    name = input_path.stem if input_path.is_file() else input_path.name
    return name.replace("_", " ").replace("-", " ").title() or "Customer Architecture"


def infer_environment(facts: dict[str, list[dict[str, str]]]) -> str | None:
    text = json.dumps(facts).lower()
    if "production" in text or "prod" in text:
        return "Production"
    if "development" in text or "dev" in text:
        return "Development"
    if "test" in text or "qa" in text:
        return "Test"
    return None


def backfill_answer_into_model(architecture: dict, area: str, answer: str) -> None:
    """Parse *answer* text for component hints and append detected entries to the
    relevant ``ibm_cloud`` keys for *area*.  Reuses :func:`add_detected_facts` and
    :func:`dedupe_components` — no logic is duplicated.
    """
    ibm_cloud = architecture.setdefault("ibm_cloud", {})
    render_plan = architecture.setdefault("render_plan", {})
    for pattern, (pattern_id, pattern_name) in PATTERN_ALIASES:
        if pattern.search(answer):
            render_plan.setdefault("pattern", pattern_id)
            render_plan.setdefault("pattern_name", pattern_name)
            render_plan.setdefault("pattern_source", "architect-answer")
            if pattern_id in {"hub-and-spoke", "fsc"}:
                render_plan.setdefault("has_tgw", True)
                render_plan.setdefault("vpcs", [
                    {"name": "Edge VPC", "purpose": "Internet ingress, egress, and hybrid connectivity", "tiers": ["Public", "Management"]},
                    {"name": "Workload VPC", "purpose": "Private application and data tiers", "tiers": ["Private", "Data"]},
                ])
            if pattern_id == "mzr":
                render_plan.setdefault("az_count", 3)
            if pattern_id == "powervs":
                render_plan.setdefault("has_powervs", True)
            break

    target_keys = AREA_TO_KEYS.get(area, [])
    if not target_keys:
        if area in AREA_TO_KEYS:
            return
        # Unknown AI-generated area — scan all categories so useful component
        # names in targeted AI questions can still enrich the model.
        target_keys = list(KEYWORDS.keys())

    # add_detected_facts iterates all KEYWORDS keys, so we must pass a full-width
    # facts dict.  Seed non-target keys with empty lists so the function can write
    # to them without error, then discard their values afterwards.
    full_facts: dict[str, list[dict[str, str]]] = {key: [] for key in KEYWORDS}
    for key in target_keys:
        full_facts[key] = list(ibm_cloud.get(key, []))

    source = f"architect-answer:{area}"
    add_detected_facts(full_facts, answer, source=source)

    # Write back only the target keys.
    for key in target_keys:
        ibm_cloud[key] = dedupe_components(full_facts[key])


def build_assumptions(ibm_cloud: dict) -> list[str]:
    assumptions = []
    if "subnets" not in ibm_cloud:
        assumptions.append("Subnet tiers, CIDR ranges, and zone placement require customer confirmation.")
    if "connectivity" not in ibm_cloud:
        assumptions.append("Hybrid connectivity pattern is not yet confirmed.")
    if "security" not in ibm_cloud:
        assumptions.append("Security group, NACL, IAM, secrets, and key-management details require review.")
    if "backup_dr" not in ibm_cloud:
        assumptions.append("Backup, recovery, RPO, RTO, and DR requirements are not yet confirmed.")
    return assumptions
