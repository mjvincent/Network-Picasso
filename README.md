# Network Picasso

**Network Picasso** is a local-first IBM Cloud architecture advisor and Draw.io diagram
workbench for technical sellers, solution architects, and teams that need to turn early customer
inputs into professional architecture diagrams quickly.

It ingests BOMs, IBM Cloud Solutioning/pricing exports, spreadsheets, notes, and customer
requirements; asks targeted design-gap questions; recommends an IBM-aligned architecture pattern;
and generates Draw.io diagrams using IBM Cloud stencil conventions.

The app is designed for sellers who may not be deep network designers. It provides guardrails,
question prompts, IBM-pattern traceability, and Bob/Draw.io MCP hand-holding so the user can move
from rough discovery notes to a customer-ready architecture conversation.

Current version: **0.6.13**

---

## What This Tool Does

Network Picasso helps answer:

- What architecture pattern best fits the customer input?
- What network, resiliency, security, and compliance decisions are missing?
- What should the high-level customer story look like?
- What should the logical architecture show?
- What should the deployment diagram show at region, VPC, zone, subnet, and service level?
- How can Bob help polish or adjust the generated Draw.io diagram?

## One-Command Container Run

For an end user who already has a copy of the repo and Docker installed, this is the default
startup path:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:5174
```

The Compose stack uses non-default host ports so it can sit beside your other containerized apps:
UI `5174`, API `8788`, and optional Postgres host access on `55432`. See
[docs/containerization.md](docs/containerization.md) for port overrides and MCP notes.

It produces five architecture pages:

| Page | Audience | Purpose |
|---|---|---|
| **Executive Overview** | Technical sellers, customer executives | One-page story showing business flow, primary/DR posture, and shared foundation |
| **Context** | Sellers, architects | High-level actors, cloud boundary, regions, and major platform services |
| **Logical Architecture** | Architects, technical sellers | Component relationships, connectivity, shared services, and platform dependencies |
| **Deployment** | Architects, implementation teams | Region, VPC, zone, subnet, service placement, PowerVS, connectivity, and evidence services |
| **Assumptions & Decisions** | Sellers, architects | IBM pattern traceability, inferred choices, validation items, question status, and quality status |

---

## Key Capabilities

- **IBM-aligned architecture guidance**
  - Matches customer input against IBM-style architecture patterns.
  - Produces pattern rationale, recommended next seller actions, and open decision areas.

- **Guided intake and design-gap questions**
  - Extracts IBM Cloud components from `.xlsx`, `.csv`, `.tsv`, `.json`, `.md`, and `.txt`.
  - Asks targeted questions for HA, DR, connectivity, security, observability, compliance, and data services.
  - Persists answers into the project `architecture.json`.

- **Professional Draw.io generation**
  - Uses IBM Cloud stencil names and IBM-style node/container patterns.
  - Generates Executive, Context, Logical, Deployment, and Assumptions & Decisions pages.
  - Opens all pages as a real multipage diagrams.net file.

- **Diagram quality analyzer**
  - Scores generated Draw.io XML for label fit, overlap risk, diagram density, and presentation readiness.
  - Checks the design against IBM Think Architecture pattern foundations from
    [IBM Architecture Patterns](https://www.ibm.com/think/architectures/patterns), including VPC landing zone,
    VSI on VPC landing zone, and PowerVS with VPC landing zone patterns.
  - Applies model-safe IBM pattern-foundation fixes directly, then identifies visual layout items that still need Bob/MCP polish.
  - Provides a remediation loop: apply analyzer fixes, regenerate, open in MCP editor, copy a Bob-ready quality fix prompt, edit, and re-analyze.

- **Bob and Draw.io MCP workflow**
  - Pushes diagrams into a live Draw.io MCP editor at `http://127.0.0.1:4000`.
  - Provides an in-app MCP checklist.
  - Provides guided Bob/MCP remediation presets for fixing labels and spacing, cleaning connector routing, polishing the Deployment page, reviewing all five pages, improving IBM pattern alignment, and preparing a customer-ready version.
  - Lets sellers choose the Bob remediation target before copying a prompt: current diagram type, a specific Draw.io page, or all five pages.
  - Verifies live MCP tab names and can rebuild the first five MCP page slots when stale or duplicate tabs are detected.
  - Provides a **Copy + open MCP** action that opens the Draw.io MCP editor, pushes the current five-page diagram into MCP, and places the selected prompt on the clipboard for Bob.
  - Shows a remediation session status after prompt copy so sellers know the copied preset, target page, MCP handoff state, and whether re-analysis is still needed.
  - Explains that Bob still needs the pasted prompt unless IBM Bob exposes a direct prompt-submission API.
  - Adds help bubbles and a recommended-next-prompt cue so sellers know which remediation preset fits the current diagram need.
  - Adds **Draw.io style memory** so preferred customer-ready label, spacing, connector, and page-order guidance can be saved globally for future projects or overridden for a specific customer project.

- **Local-first operation**
  - No cloud API keys required.
  - Optional Ollama mode for local AI-assisted extraction, question generation, and Draw.io render planning against IBM Think Architecture pattern foundations.
  - Docker Compose support with host ports chosen to avoid the existing RVTools stacks.

- **Lightweight project persistence**
  - Keeps customer folders and project subfolders on disk for easy inspection.
  - Projects are now the first workspace view: create a customer folder, add project subfolders, open saved work, move projects between customer folders, or delete with confirmation.
  - Active projects autosave their architecture model as the seller uploads files, answers questions, confirms patterns, and refines requirements.
  - Project Activity shows last save metadata, Postgres connection state, latest diagram quality score, recent project events, and restore points so autosave is visible and recoverable.

- **Finished export package**
  - Downloads a customer-ready ZIP containing the saved architecture model, five-page Draw.io file, architecture summary, IBM pattern alignment report, diagram quality report, assumptions/open questions, project activity, and style memory files.
  - Uses the live Draw.io MCP editor as the `.drawio` source when MCP is running, so manual/Bob edits are preserved in the ZIP.
  - When exported from live MCP, includes rendered PNG and SVG files for all five Draw.io tabs plus `images/manifest.json`.
  - Includes `pdf/network-picasso-diagram-packet.pdf`, a polished packet with cover page, table of contents, page numbers, one diagram per page, and appendices for architecture summary, IBM pattern alignment, diagram quality, and assumptions/open questions.
  - Shows the active export source in the UI so sellers know whether they are packaging the live MCP editor or the generated model.
  - After export, the app can ask whether to remember the current diagram look for future refinement prompts.
  - Restore previews compare the current architecture with the selected restore point before replacing the working model.
  - Restore timeline filters separate milestones, autosaves, intake/imports, design decisions, quality checks, and restores/syncs.
  - Retains milestone restore points while pruning excess routine autosaves per project; the autosave cap is configurable in Settings.
  - Adds optional Postgres persistence for customer/project metadata, architecture JSON restore points, and project events.
  - Docker Compose starts Postgres automatically with a named volume so project data survives restarts.

---

## Quick Start

### Option 1: Local Developer Run

Terminal 1:

```bash
PYTHONPATH=src python3 -B -m network_picasso.server
```

Terminal 2:

```bash
cd ui
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

### Option 2: Docker Compose

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:5174
```

Default container ports:

| Service | Host Port | Container Port |
|---|---:|---:|
| UI | `5174` | `5173` |
| API | `8788` | `8787` |
| Postgres | `55432` | `5432` |

See [docs/containerization.md](docs/containerization.md).

---

## Typical Workflow

1. **Upload customer inputs**
   - BOM exports
   - IBM Cloud Solutioning/pricing workbooks
   - discovery notes
   - architecture requirement text
   - CSV/JSON inventories

2. **Review the extracted architecture model**
   - Confirm regions, VPCs, connectivity, compute, storage, security, observability, and DR services.
   - Accept or reclassify low-confidence items.

3. **Answer design-gap questions**
   - Fill in missing HA, DR, Direct Link, endpoint, compliance, and observability decisions.
   - The answers are persisted into the project model.

4. **Review the Architecture Advisor**
   - Recommended IBM pattern
   - Well-Architected-style pillar review
   - Pattern foundation
   - Seller next actions
   - Logical design guidance

5. **Generate diagrams**
   - Save selected diagram type.
   - Open selected diagram in diagrams.net.
   - Generate all five pages.
   - Push selected or all pages to the Draw.io MCP editor.

6. **Use Bob for targeted editing**
   - Open Bob MCP settings and confirm `drawio` is connected.
   - Open `http://127.0.0.1:4000`.
   - In Network Picasso, use **Option E - Open in MCP editor**.
   - Copy a Bob prompt from the app and ask Bob to polish or adjust the diagram.

---

## Bob / Draw.io MCP

The repo includes [.bob/mcp.json](.bob/mcp.json), which registers `drawio-mcp-server` for IBM Bob.

Use the MCP workflow when you want conversational editing after generation:

```text
Use the ibm-drawio-editing skill. Inspect the open Draw.io MCP document before making changes.
Use IBM Cloud stencil patterns, keep labels non-overlapping, and preserve the existing architecture pages.
```

Then ask for a focused edit:

```text
On the Deployment page, improve label placement and connector routing while preserving the DAL/WDC PowerVS DR topology.
```

Start here for the full walkthrough:

- [docs/drawio-mcp-handbook.md](docs/drawio-mcp-handbook.md)
- [docs/getting-started.md](docs/getting-started.md#using-the-mcp-editor-with-bob)

---

## Project Structure

```text
src/network_picasso/
  advisor.py      Architecture advisor and IBM-pattern recommendation logic
  server.py       Local HTTP API
  intake.py       File parsing, component extraction, requirements enrichment
  questions.py    Rule-based design-gap questions
  drawio.py       Deterministic Draw.io renderer using IBM stencil conventions
  quality.py      Diagram quality and IBM pattern-alignment checks
  mcp_bridge.py   Draw.io MCP server bridge
  persistence.py  Optional Postgres persistence for project metadata
  projects.py     Project and folder management

ui/src/App.tsx    React + Carbon workbench

.bob/
  mcp.json        Bob MCP server registration
  skills/
    ibm-drawio-editing.md

docs/
  getting-started.md
  user-guide.md
  drawio-mcp-handbook.md
  containerization.md
  solutioning-workbook-format.md
  agentic-process.md
```

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | Docker-first quick start, usage flow, and troubleshooting |
| [docs/user-guide.md](docs/user-guide.md) | End-to-end screenshot-ready usage guide for the full tool workflow |
| [docs/images/user-guide/README.md](docs/images/user-guide/README.md) | Screenshot capture checklist and filename conventions |
| [docs/drawio-mcp-handbook.md](docs/drawio-mcp-handbook.md) | Hand-holding guide for Bob, MCP, and Draw.io editing |
| [docs/containerization.md](docs/containerization.md) | Docker Compose setup, ports, volumes, MCP host access |
| [docs/solutioning-workbook-format.md](docs/solutioning-workbook-format.md) | Expected workbook/input structure |
| [docs/agentic-process.md](docs/agentic-process.md) | Agentic process and design intent notes |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

Utility scripts:

- [scripts/capture_user_guide_screenshots.mjs](scripts/capture_user_guide_screenshots.mjs) captures sanitized app screenshots for the user guide when local Chrome is running with remote debugging on port `9223`.

---

## Testing

Backend:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_persistence.py tests/test_quality.py tests/test_advisor.py tests/test_drawio.py tests/test_endpoints.py -q
.venv/bin/python -m pip_audit
```

UI:

```bash
cd ui
npm test -- --run
npm run build
npm audit
```

Note: the UI build may report IBM Plex font resolution warnings from Carbon assets. The build
still completes successfully.

CI runs these backend/UI checks, dependency audits, and a Docker Compose image build on pushes
to `main` and pull requests.

---

## Current Data Persistence

Network Picasso uses a local-first persistence model:

- project metadata and architecture data are saved under `inputs/projects/`
- uploaded/current intake data is saved under `inputs/uploads/`
- generated diagrams are saved under `outputs/`
- settings are saved in `inputs/settings.json`
- optional Postgres persistence stores customer/project metadata, recent events, and architecture restore points

This keeps the tool transparent and easy to version in Git while still allowing recoverable
restore points when the Docker Compose Postgres service is running.

A persistent database is not required for basic single-user file-backed operation. It becomes
valuable for restore points, audit history, search, multi-user access, role-based controls, or
server-side collaboration.

---

## Recommended Next Improvements

1. **Capture and embed guide screenshots**
   - Capture the screenshot slots listed in the user guide and replace each slot with the final image once sanitized screenshots are available.

2. **Richer project metadata search**
   - Extend the new Projects search/filter controls to include industry, selected IBM pattern, quality score, region, and service family.

3. **Restore retention admin action**
   - Add an admin action to prune existing history on demand after changing the retention setting.

4. **Pattern traceability improvements**
   - Make the diagram quality analyzer distinguish explicit, inferred, missing, and recommended IBM pattern elements in the UI.

5. **Bob/MCP prompt execution history**
   - Persist remediation sessions in Project Activity so teams can see which Bob handoff prompts were used over time.

---

## Design Principles

- Deterministic diagram rendering first; AI assists but does not directly draw arbitrary XML.
- IBM Cloud visual conventions by default.
- Local-first and transparent project files.
- Seller-friendly guidance without hiding architectural assumptions.
- Draw.io remains the editable source of truth for final diagram polish.
