# Network Picasso User Guide

This guide is written for technical sellers and solution architects using Network Picasso to
create IBM-aligned network architecture diagrams. It is designed to become the screenshot-based
handbook for the entire tool, not just Bob/MCP.

Screenshots should be captured from a clean Docker Compose run at `http://127.0.0.1:5174` so the
guide matches the end-user experience.

## Screenshot Checklist

Capture these screens when preparing the illustrated guide:

| Section | Screenshot |
|---|---|
| Start the app | Terminal running `docker compose up --build` |
| Home workspace | Browser open at `http://127.0.0.1:5174` |
| Projects | Empty Projects tab with New customer folder and New project actions |
| Customer folder | Customer folder selected with project subfolders visible |
| Upload | Wizard upload page with accepted file types |
| Model review | Extracted architecture model summary |
| Questions | Design-gap question list with answer controls |
| Advisor | Architecture Advisor recommendation and logical design |
| Diagram generation | Generate diagram options and four-page flow |
| Quality analyzer | Findings plus remediation actions |
| Project Activity | Autosave, events, restore points, and timeline filters |
| Restore preview | Current vs restore-point comparison modal |
| Bob MCP settings | Bob showing `drawio` connected |
| MCP editor | Browser open at `http://127.0.0.1:4000` |
| Bob edit | Bob prompt plus updated Draw.io page |

Store screenshots under:

```text
docs/images/user-guide/
```

Use descriptive names such as:

```text
01-docker-compose-start.png
02-projects-empty.png
03-create-customer-folder.png
04-upload-source-files.png
05-restore-preview.png
```

## 1. Start Network Picasso

Recommended end-user startup:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:5174
```

Why this is preferred:

- One command starts the UI, API, and Postgres.
- Postgres enables Project Activity, restore points, and event history.
- No local Python or npm setup is required.
- Ports avoid the other local RVTools stacks.

## 2. Create A Customer And Project

Open **Projects** first.

1. Click **New customer folder**.
2. Enter the customer name.
3. Open that folder.
4. Click **New project in this folder**.
5. Enter a project name.

Use customer folders for accounts and project subfolders for opportunities, architecture
versions, workshops, phases, or named proposals.

## 3. Upload Source Files

Open the wizard and upload customer evidence:

- IBM Cloud Solutioning/pricing exports.
- BOM spreadsheets.
- CSV/TSV inventories.
- Discovery notes.
- Architecture descriptions.
- Existing Network Picasso JSON.

Good inputs describe business context, workload type, compliance requirements, regions,
connectivity, existing network topology, compute, storage, security, monitoring, backup, and DR.

## 4. Review Extracted Architecture

The model review page summarizes what the app found. Check that major IBM Cloud services are
classified correctly:

- Regions.
- VPCs.
- Connectivity.
- Compute.
- Storage and data.
- Security and compliance.
- Observability.
- Backup and DR.

If AI-assisted intake is enabled, review low-confidence items before they become part of the
architecture.

## 5. Answer Design-Gap Questions

Network Picasso asks questions where the customer input is incomplete. These questions help
technical sellers avoid common network architecture gaps:

- HA and multi-zone requirements.
- DR region and recovery objectives.
- Direct Link or VPN connectivity.
- Transit Gateway and VPC routing.
- Private endpoints and service access.
- Security, keys, secrets, logging, and compliance.
- Storage durability and replication.

Answers are saved into the active project and influence the next architecture review and diagram.

## 6. Review Architecture Advisor

The Architecture Advisor connects customer input to IBM-style architecture guidance:

- Recommended pattern.
- Alternative patterns.
- Pattern foundation.
- Well-Architected-style pillar review.
- Priority open decisions.
- Seller next actions.
- Logical design narrative.

Use this section to validate the architecture before creating customer-facing diagrams.

## 7. Generate Draw.io Diagrams

Network Picasso generates four diagram pages:

| Page | Use it for |
|---|---|
| Executive Overview | Customer story, business flow, primary/DR posture |
| Context | External actors, IBM Cloud boundary, major platform services |
| Logical Architecture | Component relationships, shared services, dependencies |
| Deployment | Regions, VPCs, zones, subnets, services, connectivity |

Recommended first action:

1. Click **Generate all diagram types**.
2. Confirm diagrams.net opens one file with four page tabs.
3. Review the Deployment page for label clarity and routing.

## 8. Analyze Diagram Quality

Run **Diagram quality analyzer** after generation.

It checks:

- Label fit and overlap risk.
- Crowded containers or subnet bands.
- Connector clarity.
- IBM pattern alignment.
- Customer-readiness issues.

Use **Apply analyzer fixes** when the analyzer identifies missing IBM pattern-foundation
elements. Network Picasso updates the architecture model with traceable recommendations, then
you can regenerate the diagram and re-analyze.

Use the remediation prompt if Bob/MCP is available for visual layout issues such as overlapping
labels, cramped text, connector routing, and final presentation polish. Re-run the analyzer after editing.

## 9. Use Project Activity And Restore Points

Project Activity shows whether the project is saving correctly.

Use it to:

- Confirm autosave is working.
- See the architecture JSON path.
- Confirm Postgres is connected.
- Check latest quality score.
- Review recent events.
- Restore an earlier architecture state.

Timeline filters help find useful checkpoints:

- Milestones.
- All restore points.
- Autosaves.
- Intake and imports.
- Design decisions.
- Quality checks.
- Restores and syncs.

Before restore, Network Picasso shows a comparison between the current model and the selected
restore point.

Routine autosave restore points are capped per project so the database does not grow forever.
Milestone restore points such as intake, design decisions, quality checks, imports, and manual
restores are retained. The default autosave limit is `25`; change it in **Settings > Restore retention**.

## 10. Export The Customer Package

Use **Project Activity > Export package** when the project is ready for handoff.

The ZIP includes:

- Saved `architecture.json`.
- Four-page Draw.io architecture file.
- Architecture summary report.
- IBM pattern alignment report.
- Diagram quality report.
- Assumptions, open questions, and answered questions.
- Project activity and restore-point metadata.

## 11. Edit With Bob And MCP

Use Bob/MCP when deterministic generation gets you close but the diagram needs professional
polish.

Setup:

1. Open this repo in IBM Bob.
2. Open Bob settings and find MCP.
3. Confirm `drawio` is connected.
4. Open `http://127.0.0.1:4000`.
5. In Network Picasso, click **Open in MCP editor**.

Recommended prompt:

```text
Use the ibm-drawio-editing skill. Inspect the open Draw.io MCP document before making changes.
Use IBM Cloud stencil patterns, keep labels non-overlapping, and preserve the existing architecture pages.
```

Examples:

```text
On the Deployment page, improve label placement and connector routing without changing the architecture.
```

```text
On the Logical Architecture page, make the private service access path clearer and preserve IBM container boundaries.
```

```text
Review the four pages for customer-readiness and list any page that still needs manual cleanup.
```

## 12. Other Export Options

Additional export options:

- Save selected `.drawio` file.
- Open generated diagrams in diagrams.net.
- Generate all four pages.
- Export project `architecture.json`.

Recommended working practice:

1. Generate all pages.
2. Use Diagram Quality Analyzer.
3. Use Bob/MCP for final cleanup if needed.
4. Export the customer package from Project Activity.
5. Keep customer deliverables outside Git unless intentionally versioned.

## Troubleshooting Quick Reference

| Issue | Likely cause | Action |
|---|---|---|
| No restore points | Postgres is off or no project event has occurred | Use Docker Compose and trigger an autosave/intake/quality check |
| Bob cannot edit Draw.io | Bob MCP is disconnected or editor tab is not open | Refresh Bob MCP, open `http://127.0.0.1:4000`, retry Option E |
| Diagram labels overlap | Generated layout needs polish | Run quality analyzer, copy Bob remediation prompt, re-analyze |
| Only one Draw.io page | Browser has stale app state or single-page option was used | Use Generate all diagram types and refresh the app |
| AI questions seem generic | Ollama mode may be off or source files lack detail | Add requirements text or discovery notes and re-run intake |

## Suggested Expansion

The next documentation pass should add real screenshots to each section and a short "seller demo"
walkthrough using a sample customer project. The guide should show exactly what to click and what
the user should expect after each click.
