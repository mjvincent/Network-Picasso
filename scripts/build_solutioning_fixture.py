"""Build examples/sample-inputs/solutioning-sample.xlsx using stdlib only.

Run once from the repo root:
    PYTHONPATH=src python3 scripts/build_solutioning_fixture.py
"""
from __future__ import annotations

import io
import textwrap
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

HEADERS = [
    "Part Number",
    "Part Description",
    "Category",
    "Region",
    "Quantity",
    "Monthly Recurring Charge",
    "Notes",
]

ROWS = [
    # Part Number, Part Description, Category, Region, Qty, MRC, Notes
    (
        "RC-VPCINFRA-VSI-001",
        "Virtual Server Instance (4 vCPU / 16 GB)",
        "Compute",
        "us-south",
        "2",
        "$180.00",
        "Application tier – zone 1 and zone 2",
    ),
    (
        "RC-COS-STD-001",
        "Cloud Object Storage (Standard plan)",
        "Object Storage",
        "us-south",
        "1",
        "$25.00",
        "Backup bucket for VSI snapshots",
    ),
    (
        "RC-PGSQL-STD-001",
        "Databases for PostgreSQL (standard 8/32)",
        "Database",
        "us-east",
        "1",
        "$120.00",
        "Primary relational DB – high availability enabled",
    ),
    (
        "RC-TGW-001",
        "Transit Gateway (local routing)",
        "Network",
        "us-south",
        "1",
        "$15.00",
        "Connect VPC to on-premises via Direct Link",
    ),
    (
        "RC-KP-001",
        "Key Protect (standard plan)",
        "Security",
        "us-south",
        "1",
        "$50.00",
        "Envelope encryption for COS and databases",
    ),
    (
        "RC-MON-001",
        "IBM Cloud Monitoring (graduated tier)",
        "Monitoring",
        "us-south",
        "1",
        "$35.00",
        "Platform metrics and application dashboards",
    ),
    (
        "RC-LB-PUB-001",
        "Load Balancer for VPC (public, ALB)",
        "VPC Infrastructure",
        "us-south",
        "1",
        "$22.00",
        "Public ingress for application tier",
    ),
    (
        "RC-LOGDNA-001",
        "IBM Log Analysis (7-day retention)",
        "Observability",
        "us-south",
        "1",
        "$18.00",
        "Centralised log aggregation",
    ),
]

# ---------------------------------------------------------------------------
# Minimal OOXML builder helpers
# ---------------------------------------------------------------------------

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"

# Content-Types XML
CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml"
    ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml"
    ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
"""

# Root .rels
ROOT_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="xl/workbook.xml"/>
</Relationships>
"""

# Workbook
WORKBOOK_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Detailed Estimate" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

# Workbook .rels
WORKBOOK_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
    Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings"
    Target="sharedStrings.xml"/>
</Relationships>
"""


def _col_letter(n: int) -> str:
    """Convert 0-based column index to Excel column letter(s)."""
    result = ""
    n += 1
    while n:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _ref(row: int, col: int) -> str:
    """Return Excel cell reference like 'A1' (1-based row, 0-based col)."""
    return f"{_col_letter(col)}{row}"


def build_shared_strings(all_data: list[list[str]]) -> tuple[list[str], dict[str, int]]:
    """Return (strings_list, string_to_index) for the shared string table."""
    seen: dict[str, int] = {}
    ordered: list[str] = []
    for row in all_data:
        for cell in row:
            if cell not in seen:
                seen[cell] = len(ordered)
                ordered.append(cell)
    return ordered, seen


def shared_strings_xml(strings: list[str]) -> str:
    count = len(strings)
    parts = [
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        f' count="{count}" uniqueCount="{count}">\n'
    ]
    for s in strings:
        # Minimal XML escaping
        escaped = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        parts.append(f"  <si><t>{escaped}</t></si>\n")
    parts.append("</sst>\n")
    return "".join(parts)


def sheet_xml(data: list[list[str]], string_index: dict[str, int]) -> str:
    """Build worksheet XML using shared string references."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n',
        "  <sheetData>\n",
    ]
    for row_num, row_data in enumerate(data, start=1):
        parts.append(f'    <row r="{row_num}">\n')
        for col_idx, cell_val in enumerate(row_data):
            ref = _ref(row_num, col_idx)
            si = string_index[cell_val]
            parts.append(f'      <c r="{ref}" t="s"><v>{si}</v></c>\n')
        parts.append("    </row>\n")
    parts.append("  </sheetData>\n</worksheet>\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    output_path = Path("examples/sample-inputs/solutioning-sample.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_data: list[list[str]] = [list(HEADERS)] + [list(r) for r in ROWS]
    strings, string_index = build_shared_strings(all_data)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", textwrap.dedent(CONTENT_TYPES).strip())
        zf.writestr("_rels/.rels", textwrap.dedent(ROOT_RELS).strip())
        zf.writestr("xl/workbook.xml", textwrap.dedent(WORKBOOK_XML).strip())
        zf.writestr("xl/_rels/workbook.xml.rels", textwrap.dedent(WORKBOOK_RELS).strip())
        zf.writestr("xl/sharedStrings.xml", shared_strings_xml(strings))
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml(all_data, string_index))

    output_path.write_bytes(buf.getvalue())
    print(f"Written: {output_path}  ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
