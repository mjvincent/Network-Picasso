from __future__ import annotations

import csv
import json
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".csv", ".json", ".md", ".txt", ".tsv", ".xlsx"}

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
    "connectivity": ["direct link", "vpn", "transit gateway", "bgp", "hybrid", "mpls"],
    "ingress": ["ingress", "load balancer", "cloud internet services", "cis", "router", "gateway"],
    "compute": ["vsi", "virtual server", "roks", "openshift", "kubernetes", "bare metal", "powervs", "power"],
    "data": ["database", "postgres", "db2", "object storage", "cos", "storage", "bucket"],
    "private_endpoints": ["private endpoint", "vpe", "virtual private endpoint"],
    "dns": ["dns", "resolver", "domain", "hostname"],
    "security": ["iam", "secrets", "key protect", "hpcs", "certificate", "security group", "nacl", "firewall"],
    "observability": ["monitoring", "logging", "logs", "activity tracker", "audit", "flow log", "metrics"],
    "backup_dr": ["backup", "restore", "dr", "disaster recovery", "rpo", "rto", "replication"],
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
    "Regions and availability": ["regions"],
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


def discover_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []

    files: list[Path] = []
    for child in path.rglob("*"):
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(child)
    return sorted(files)


def build_architecture_from_inputs(input_path: Path, *, project_name: str | None = None) -> dict:
    files = discover_inputs(input_path)
    facts: dict[str, list[dict[str, str]]] = {key: [] for key in KEYWORDS}
    sources: list[dict[str, object]] = []

    for file_path in files:
        rows = list(read_input_rows(file_path))
        source_entry: dict[str, object] = {
            "file": str(file_path),
            "type": file_path.suffix.lower().lstrip("."),
            "records": len(rows),
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
            name = concise_name(text)
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


def add_structured_fact(facts: dict[str, list[dict[str, str]]], row: dict[str, str], *, source: str) -> bool:
    lowered = {key.lower().strip(): value.strip() for key, value in row.items() if value.strip()}
    category_value = first_value(lowered, ["category", "type", "service category", "component category"])
    name = first_value(lowered, ["component", "name", "service", "item", "resource"])
    notes = first_value(lowered, ["notes", "description", "purpose", "comment"])
    region = first_value(lowered, ["region", "location"])

    category = CATEGORY_ALIASES.get(category_value.lower()) if category_value else None
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


def dedupe_components(components: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for component in components:
        key = (component["type"], component["name"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(component)
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
    target_keys = AREA_TO_KEYS.get(area, [])
    if not target_keys:
        # Unknown area — fall back to scanning all categories.
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
