# Getting Started with Network Picasso

Network Picasso is a local-first IBM Cloud architecture advisor and Draw.io workbench for
technical sellers. It turns customer source files, notes, and design answers into IBM-aligned
architecture guidance and editable diagrams.

For most users, the Docker Compose path is the easiest entry point. It starts the UI, API, and
Postgres persistence with one command and avoids local Python/npm setup.

## Fastest Start: Docker Compose

### Prerequisites

| Requirement | Why it is needed | Check |
|---|---|---|
| Docker Desktop or Docker Engine | Runs the app, API, and Postgres | `docker --version` |
| Git or a downloaded repo copy | Gets the project files onto your laptop | `git --version` |
| Browser | Opens the Network Picasso UI and diagrams.net | Any modern browser |
| IBM Bob | Optional, for conversational Draw.io editing | Bob MCP settings |
| Ollama | Optional, for local AI-assisted intake | `ollama --version` |

### 1. Get the repository

```bash
git clone <repo-url>
cd "Network Picasso"
```

If you received a zip file instead, extract it and open a terminal in the extracted
`Network Picasso` folder.

### 2. Start the app

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:5174
```

Leave the terminal running while you use the app. Stop it with `Ctrl+C`.

For background mode:

```bash
docker compose up --build -d
```

Stop background containers:

```bash
docker compose down
```

### 3. Confirm the services

```bash
curl http://127.0.0.1:8788/api/health
curl http://127.0.0.1:8788/api/persistence/status
```

Expected result:

- API returns `"ok": true`
- Persistence returns `"connected": true`
- UI is open at `http://127.0.0.1:5174`

Default container ports:

| Service | Host port | Container port |
|---|---:|---:|
| UI | `5174` | `5173` |
| API | `8788` | `8787` |
| Postgres | `55432` | `5432` |

These ports are intentionally different from the other RVTools container stacks.

## First Use

### 1. Open Projects

Use the **Projects** tab first. Create:

1. A customer folder.
2. A project subfolder inside that customer.

Each project gets its own saved architecture model, uploads, activity history, and restore
points.

### 2. Upload customer inputs

Use the wizard to upload one or more files:

| File type | Good for |
|---|---|
| `.xlsx` | IBM Cloud Solutioning/pricing exports, BOM workbooks |
| `.csv`, `.tsv` | Component inventories or bill of materials |
| `.md`, `.txt` | Discovery notes, requirements, architecture descriptions |
| `.json` | Existing Network Picasso architecture model |

The app extracts IBM Cloud regions, VPCs, compute, storage, security, observability,
connectivity, and data services.

### 3. Review the model

Review extracted components. If Ollama mode is enabled, low-confidence items may appear in a
staging area where you can confirm or discard them.

### 4. Answer design-gap questions

Questions identify missing HA, DR, network, security, compliance, observability, and data
decisions. Answers are written back into the architecture model and autosaved.

### 5. Review Architecture Advisor

Use the advisor output to understand:

- Recommended IBM architecture pattern.
- Pattern rationale.
- Well-Architected-style gaps.
- Seller next actions.
- Logical design guidance.

### 6. Generate diagrams

Network Picasso can generate:

| Page | Purpose |
|---|---|
| Executive Overview | Customer-facing story and business flow |
| Context | External actors, cloud boundary, major services |
| Logical Architecture | Component relationships and dependencies |
| Deployment | Regions, VPCs, zones, subnets, PowerVS, services, and connectivity |

Use **Generate all diagram types** for a four-page Draw.io file. Use **Open in MCP editor**
when you want Bob to edit the diagram conversationally.

### 7. Analyze and refine diagram quality

Use the Diagram Quality Analyzer to check label fit, crowding, connector clarity, and IBM
pattern alignment. If findings appear, use the provided Bob prompt or open the diagram in the
MCP editor, refine it, and re-analyze.

### 8. Use restore points

Project Activity shows:

- Autosave status.
- Architecture file metadata.
- Postgres status.
- Latest quality score.
- Recent events.
- Restore points.

Restore points can be filtered by milestones, autosaves, intake/imports, design decisions,
quality checks, and restores/syncs. Before restoring, the app compares the current architecture
against the selected restore point.

Milestone restore points are retained. Routine autosaves are capped per project to keep the
database from growing indefinitely.

## Full Usage Guide

For a broader walkthrough that can be expanded with screenshots, see:

- [User Guide](user-guide.md)
- [Draw.io MCP Handbook](drawio-mcp-handbook.md)
- [Containerization Guide](containerization.md)

## Bob and Draw.io MCP

Bob/MCP is optional. Use it when you want conversational diagram editing after Network Picasso
has generated the diagram.

The repository includes:

```text
.bob/mcp.json
.bob/skills/ibm-drawio-editing.md
```

Bob should show a `drawio` MCP server in settings. The live MCP editor runs at:

```text
http://127.0.0.1:4000
```

Typical flow:

1. Open the Network Picasso workspace in Bob.
2. Confirm Bob settings show `drawio` connected.
3. Open `http://127.0.0.1:4000`.
4. In Network Picasso, generate a diagram.
5. Click **Open in MCP editor** or **Open all pages in MCP editor**.
6. Ask Bob to inspect the open Draw.io document and make a targeted edit.

Recommended starting prompt:

```text
Use the ibm-drawio-editing skill. Inspect the open Draw.io MCP document before making changes.
Use IBM Cloud stencil patterns, keep labels non-overlapping, and preserve the existing architecture pages.
```

See [Draw.io MCP Handbook](drawio-mcp-handbook.md) for detailed troubleshooting.

## Optional Ollama Mode

The default mode is deterministic rules. Ollama is optional and runs locally if installed on the
host.

1. Start Ollama on the host.
2. Pull a model such as `phi4-mini:latest`.
3. In Network Picasso, open **Settings**.
4. Select Ollama-assisted mode.
5. Test the connection and save settings.

The containerized API can use a host Ollama service when host networking is reachable from
Docker. If your platform handles host networking differently, use the local developer workflow
or adjust the API environment variables.

## Local Developer Run

Use this path only when you are changing code or debugging locally without containers.

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
PYTHONPATH=src python3 -B -m network_picasso.server
```

Backend opens at:

```text
http://127.0.0.1:8787
```

### UI

```bash
cd ui
npm install
npm run dev
```

UI opens at:

```text
http://127.0.0.1:5173
```

## Troubleshooting

| Symptom | What to check |
|---|---|
| UI does not open at `5174` | Confirm `docker compose up --build` is still running and no other app is using port `5174`. |
| API health fails | Run `docker ps` and confirm `network-picasso-api` is healthy. |
| Postgres says disconnected | Confirm `network-picasso-db` is healthy and restart with `docker compose up --build`. |
| Restore points do not appear | Restore points require connected Postgres persistence and at least one autosave/intake/quality/design event. |
| Bob says `drawio` disconnected | Open Bob MCP settings, refresh/reconnect `drawio`, then open `http://127.0.0.1:4000`. |
| Container cannot reach MCP editor | Confirm `NETWORK_PICASSO_MCP_BASE_URL=http://host.docker.internal:4000` in Compose. |
| Only one Draw.io page appears | Use **Generate all diagram types** and confirm diagrams.net shows page tabs. Refresh the app if the browser cached old UI code. |

## Tests

Backend:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_advisor.py tests/test_drawio.py tests/test_endpoints.py -q
```

UI:

```bash
cd ui
npm test -- --run
npm run build
npm audit
```
