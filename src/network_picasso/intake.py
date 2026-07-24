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
    "compute": "compute",
    "connectivity": "connectivity",
    "data": "data",
    "database": "data",
    "dns": "dns",
    "dr": "backup_dr",
    "ingress": "ingress",
    "observability": "observability",
    "private endpoint": "private_endpoints",
    "security": "security",
    "subnet": "subnets",
    "vpc": "vpcs",
    "zone": "zones",
}

IBM_REGION_PATTERN = re.compile(r"\b(?:us|eu|ca|jp|au|br)-[a-z]+\b")


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
        sources.append(
            {
                "file": str(file_path),
                "type": file_path.suffix.lower().lstrip("."),
                "records": len(rows),
            }
        )
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
                        f"{sheet_name}.{headers[index] or f'column_{index + 1}'}": value
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
            facts[category].append(
                {
                    "name": concise_name(text),
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
            if 3 <= len(candidate) <= 80:
                return candidate
    return cleaned[:80] or "Unlabeled component"


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
