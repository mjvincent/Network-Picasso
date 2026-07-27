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

Current version: **0.4.6**

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

It produces four architecture pages:

| Page | Audience | Purpose |
|---|---|---|
| **Executive Overview** | Technical sellers, customer executives | One-page story showing business flow, primary/DR posture, and shared foundation |
| **Context** | Sellers, architects | High-level actors, cloud boundary, regions, and major platform services |
| **Logical Architecture** | Architects, technical sellers | Component relationships, connectivity, shared services, and platform dependencies |
| **Deployment** | Architects, implementation teams | Region, VPC, zone, subnet, service placement, PowerVS, connectivity, and evidence services |

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
  - Generates Executive, Context, Logical, and Deployment pages.
  - Opens all pages as a real multipage diagrams.net file.

- **Diagram quality analyzer**
  - Scores generated Draw.io XML for label fit, overlap risk, diagram density, and presentation readiness.
  - Checks the design against IBM Think Architecture pattern foundations from
    [IBM Architecture Patterns](https://www.ibm.com/think/architectures/patterns), including VPC landing zone,
    VSI on VPC landing zone, and PowerVS with VPC landing zone patterns.
  - Provides a remediation loop: open in MCP editor, copy a Bob-ready quality fix prompt, edit, and re-analyze.

- **Bob and Draw.io MCP workflow**
  - Pushes diagrams into a live Draw.io MCP editor at `http://127.0.0.1:4000`.
  - Provides an in-app MCP checklist.
  - Provides grouped, copy-ready Bob prompts for setup, label cleanup, connector fixes, IBM pattern review, landing-zone polish, executive simplification, security, DR, data flow, and final customer-readiness QA.
  - Adds help bubbles and a recommended-next-prompt cue so sellers know which Bob prompt fits the current diagram need.

- **Local-first operation**
  - No cloud API keys required.
  - Optional Ollama mode for local AI-assisted extraction and question generation.
  - Docker Compose support with host ports chosen to avoid the existing RVTools stacks.

- **Lightweight project persistence**
  - Keeps customer folders and project subfolders on disk for easy inspection.
  - Projects are now the first workspace view: create a customer folder, add project subfolders, open saved work, move projects between customer folders, or delete with confirmation.
  - Active projects autosave their architecture model as the seller uploads files, answers questions, confirms patterns, and refines requirements.
  - Project Activity shows last save metadata, Postgres connection state, latest diagram quality score, recent project events, and restore points so autosave is visible and recoverable.
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
   - Generate all four pages.
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
  drawio-mcp-handbook.md
  containerization.md
  solutioning-workbook-format.md
  agentic-process.md
```

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | Full setup and usage walkthrough |
| [docs/drawio-mcp-handbook.md](docs/drawio-mcp-handbook.md) | Hand-holding guide for Bob, MCP, and Draw.io editing |
| [docs/containerization.md](docs/containerization.md) | Docker Compose setup, ports, volumes, MCP host access |
| [docs/solutioning-workbook-format.md](docs/solutioning-workbook-format.md) | Expected workbook/input structure |
| [docs/agentic-process.md](docs/agentic-process.md) | Agentic process and design intent notes |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Testing

Backend:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_drawio.py tests/test_endpoints.py tests/test_advisor.py -q
```

UI:

```bash
cd ui
npm run build
```

Note: the UI build may report IBM Plex font resolution warnings from Carbon assets. The build
still completes successfully.

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

1. **Screenshot-based user guide**
   - Capture the Bob MCP setup, `localhost:4000` editor, Option E workflow, and Bob prompt flow.

2. **Restore point comparison**
   - Show a side-by-side summary of changed regions, VPCs, services, requirements, and quality score before restoring.

3. **Assumptions and decisions page**
   - Add a fifth generated page summarizing assumptions, unanswered questions, inferred choices, and customer decisions.

4. **Project search and filters**
   - Search customers/projects by name, industry, selected IBM pattern, quality score, region, and service family.

5. **Export package**
   - Generate a customer-ready package with `.drawio`, architecture summary, assumptions, open questions, and implementation notes.

6. **Pattern traceability improvements**
   - Show which IBM pattern elements are explicit, inferred, missing, or recommended.

---

## Design Principles

- Deterministic diagram rendering first; AI assists but does not directly draw arbitrary XML.
- IBM Cloud visual conventions by default.
- Local-first and transparent project files.
- Seller-friendly guidance without hiding architectural assumptions.
- Draw.io remains the editable source of truth for final diagram polish.
