# IBM Cloud Solutioning Workbook Format

This document describes the sheet and column structure of IBM Cloud Solutioning
pricing workbooks (`.xlsx`) as exported from the IBM Cloud Solutioning tool
(<https://cloud.ibm.com/solutioning>). Network Picasso uses these conventions in
[`read_solutioning_xlsx()`](../src/network_picasso/intake.py) to extract
components with higher accuracy than the generic keyword scanner.

---

## Identification

A workbook is treated as a Solutioning workbook when **either** of the following
conditions is true:

1. It contains a sheet named **"Detailed Estimate"** whose first row includes a
   column header **"Part Number"**.
2. It contains a sheet named **"Summary"** whose first row includes a column
   header **"Part Number"** (used when only a summary sheet is exported).

If neither condition is met, the file falls through to the generic `read_xlsx()`
path, which performs keyword-based scanning across all sheets.

---

## Known Sheets

| Sheet name         | Purpose                                                  | Priority |
|--------------------|----------------------------------------------------------|----------|
| `Detailed Estimate`| Line-item breakdown with part numbers, quantities, cost  | Primary  |
| `Summary`          | Rolled-up totals per category                            | Fallback |
| `Assumptions`      | Free-text pricing assumptions (not parsed)               | Ignored  |
| `Cover`            | Title / project metadata (not parsed)                    | Ignored  |

Network Picasso reads **"Detailed Estimate"** first, and falls back to
**"Summary"** if that sheet is absent.

---

## Column Reference — Detailed Estimate

| Column header              | Network Picasso field | Notes                                        |
|----------------------------|-----------------------|----------------------------------------------|
| `Part Number`              | `part_number`         | IBM Cloud SKU, e.g. `RC-VPCINFRA-VSI-BOST`  |
| `Part Description`         | `component`           | Human-readable service name (used as `name`)|
| `Category`                 | `category`            | Mapped through `CATEGORY_ALIASES` (see below)|
| `Region`                   | `region`              | IBM Cloud region slug, e.g. `us-south`       |
| `Notes` / `Description`    | `notes`               | Free-text remarks; either column accepted     |
| `Quantity`                 | `quantity`            | Number of units ordered                      |
| `Monthly Recurring Charge` | _(cost, not imported)_| Pricing data — not used in architecture model|
| `One Time Charge`          | _(cost, not imported)_| Pricing data — not used in architecture model|

Column matching is **case-insensitive** and **whitespace-normalised**. Columns
not listed above are silently ignored.

---

## Category Values and Aliases

The `Category` column in a real export uses marketing names that must be mapped
to the `ibm_cloud` keys used in the architecture schema. The following mappings
are registered in `CATEGORY_ALIASES` in [`intake.py`](../src/network_picasso/intake.py):

| Solutioning category value              | `ibm_cloud` key       |
|-----------------------------------------|-----------------------|
| `Compute`                               | `compute`             |
| `Storage` / `Object Storage`            | `data`                |
| `Database`                              | `data`                |
| `Network` / `Networking`                | `connectivity`        |
| `VPC Infrastructure`                    | `vpcs`                |
| `Security`                              | `security`            |
| `Observability` / `Monitoring`          | `observability`       |
| `DNS`                                   | `dns`                 |
| `Backup` / `Backup and Recovery`        | `backup_dr`           |
| `Private Endpoint` / `VPE`             | `private_endpoints`   |
| `Subnet`                                | `subnets`             |
| `Availability Zone`                     | `zones`               |

Category values that do not match any alias fall through to
`add_detected_facts()` via keyword scanning of the full row text.

---

## Sample Row (Detailed Estimate sheet)

```
Part Number          Part Description                   Category       Region     Quantity  Monthly Recurring Charge
RC-VPCINFRA-VSI-001  Virtual Server Instance (4x16)     Compute        us-south   2         $180.00
RC-COS-STD-001       Cloud Object Storage (Standard)    Storage        us-south   1         $25.00
RC-PGSQL-STD-001     Databases for PostgreSQL (std)     Database       us-east    1         $120.00
RC-TGW-001           Transit Gateway                    Network        us-south   1         $15.00
RC-KP-001            Key Protect                        Security       us-south   1         $50.00
```

---

## source_format Tag

When a file is recognised as a Solutioning workbook, the source entry in
`architecture.sources` includes:

```json
{
  "file": "path/to/workbook.xlsx",
  "type": "xlsx",
  "source_format": "ibm-solutioning",
  "records": 12
}
```

This lets the renderer and any future tooling identify how the component data
was extracted.

---

## Adding New Category Mappings

Edit the `CATEGORY_ALIASES` dict in [`intake.py`](../src/network_picasso/intake.py).
Keys are lowercase category strings as they appear in the workbook; values are
valid `ibm_cloud` keys from the architecture schema.
