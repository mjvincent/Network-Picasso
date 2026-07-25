# Draw.io MCP Server Integration Plan

## Overview

Integrate [`lgazo/drawio-mcp-server`](https://github.com/lgazo/drawio-mcp-server) (v2.1.0) into
Network Picasso to enable **conversational post-generation diagram editing**. After the deterministic
renderer produces a diagram, Bob (as an MCP client) can accept requests like
*"add a Bastion host to the Management subnet in zone-1"* and execute them live in a running
Draw.io editor tab.

**Non-goals:**
- Do not replace `drawio.py` — the deterministic IBM-style renderer stays as the primary
  generation path.
- Do not use raw `add-cell-of-shape` for edits — this produces non-IBM-styled nodes. All new
  elements must go through the IBM prescribed node pattern.

---

## Critical Architectural Constraint

The MCP server does **not** operate on `.drawio` files on disk. It communicates with a **live
Draw.io browser tab** via WebSocket bridge. No open tab → all live tools fail with
`"No connected Draw.io documents"`.

The recommended deployment mode is `--editor`, which hosts Draw.io itself at
`http://localhost:4000` — no browser extension required. Network Picasso pushes the generated XML
into that tab via `import-diagram` (MCP tool), and Bob then edits it conversationally.

---

## MCP Tool Surface (relevant subset)

| Tool | Purpose |
|---|---|
| `import-diagram` | Load XML/SVG/PNG into the live editor (`replace` or `add` mode) |
| `list-paged-model` | Read all cells to understand current diagram structure |
| `add-cell-of-shape` | Add a raw stencil shape by name (use only for non-IBM shapes) |
| `add-rectangle` | Add a container/label (used for subnet bands, text overlays) |
| `add-edge` | Connect two cells with a labeled, routed edge |
| `edit-cell` | Update position/size/label/style of an existing cell by ID |
| `delete-cell-by-id` | Remove a node or edge |
| `set-cell-parent` | Nest a cell inside a container (AZ column, subnet band) |
| `get-shape-by-name` | Look up IBM stencil shape style strings by name |
| `export-diagram` | Export the final diagram back to XML/SVG/PNG |
| `create-page` / `copy-page` | Add diagram pages (context + logical + deployment as tabs) |
| `import-mermaid` | Convert LLM-generated Mermaid source to Draw.io cells |

---

## Sub-Tasks

---

### T1 — Register the MCP Server in Bob

**Intent:** Make the `drawio-mcp-server` MCP tools available to Bob in this workspace by adding a
workspace-scoped MCP config entry.

**Expected Outcomes:**
- Bob's MCP panel shows `drawio` as a connected server.
- Bob can call `import-diagram`, `list-paged-model`, and other draw.io tools in conversation.
- Server starts with `--editor` flag so Draw.io is hosted at `http://localhost:4000`.
- Server binds to `127.0.0.1` to avoid IPv6/IPv4 mismatch on macOS.

**Todo List:**
- [ ] Verify Node.js ≥ v22 is installed (`node --version`)
- [ ] Create `.bob/mcp.json` in the repo root with the `drawio` server entry
- [ ] Confirm Bob's MCP panel shows the server as connected
- [ ] Verify Draw.io editor loads at `http://localhost:4000`

**Config to write (`.bob/mcp.json`):**
```json
{
  "mcpServers": {
    "drawio": {
      "command": "npx",
      "args": ["-y", "drawio-mcp-server", "--editor", "--host", "127.0.0.1"],
      "timeout": 30000
    }
  }
}
```

**Relevant Context:**
- MCP skill instructions: `.bob/skills/configure-mcp.md`
- Bob workspace MCP config location: `.bob/mcp.json`

**Status:** `[x] done`

---

### T2 — Add "Open in Editor" Button to the Diagram Step

**Intent:** Add a fifth diagram export option in the Network Picasso UI that opens the generated
diagram in the MCP-hosted Draw.io editor at `localhost:4000`. This replaces the current manual
workflow of: save file → open Draw.io desktop → open file.

**Expected Outcomes:**
- A new "Option E — Open in MCP editor" button appears in the diagram step alongside Options A–D.
- Clicking it fetches the current diagram XML via `/api/drawio-xml` and POSTs it to the MCP
  server's `import-diagram` tool (via a new `/api/drawio-mcp-open` server endpoint).
- The MCP editor tab at `http://localhost:4000` is opened (or focused) automatically.
- If the MCP server is not running, an inline error notification is shown.

**Todo List:**
- [ ] Add `/api/drawio-mcp-open` POST endpoint to `server.py`
  - Accepts `{ architecturePath, diagramType }`
  - Generates XML via `render_drawio()`
  - POSTs to MCP server HTTP endpoint or calls `import-diagram` tool via MCP protocol
  - Returns `{ ok: true, editorUrl: "http://localhost:4000" }`
- [ ] Add Option E button to `ui/src/App.tsx` diagram step
  - Shows only when MCP server health check passes (probe `localhost:4000`)
  - On click: calls `/api/drawio-mcp-open`, then opens `http://localhost:4000` in new tab
  - Shows `InlineNotification` with error if MCP server unreachable
- [ ] Add `mcp_open_diagram()` helper to a new `src/network_picasso/mcp_bridge.py`
  - Uses `urllib.request` (no new deps) to call the MCP server's HTTP API
  - Handles connection errors gracefully (returns error string)
- [ ] Add MCP server health check to the Settings page (`GET http://localhost:4000` or equivalent)

**Relevant Context:**
- Diagram step UI: `ui/src/App.tsx` lines 1395–1490 (Options A–D section)
- Server endpoints: `src/network_picasso/server.py` (follow existing `handle_*` pattern)
- Ollama client pattern (stdlib urllib.request): `src/network_picasso/ollama.py`

**Status:** `[x] done`

---

### T3 — Expose IBM-Node XML Snippet API from drawio.py

**Intent:** Allow Bob to generate a single IBM-styled node as Draw.io XML (the colored-square +
white-icon child pattern) without regenerating the full diagram. Bob uses this snippet and injects
it via `import-diagram` in `add` mode — preserving visual consistency with the generated diagram.

**Expected Outcomes:**
- `drawio.py` exports a `render_ibm_node_snippet(name, shape, category, x, y)` function that
  returns minimal valid Draw.io XML for one IBM-prescribed node.
- A new `/api/drawio-snippet` POST endpoint accepts
  `{ name, shape, category, x, y, parentId }` and returns the XML snippet.
- Bob can call this endpoint to get IBM-styled XML before calling the MCP `import-diagram` tool.

**Todo List:**
- [ ] Add `render_ibm_node_snippet(name, shape, category, x, y, parent_id="1")` to `drawio.py`
  - Uses the same `ibm_node()` builder method as the full renderer
  - Wraps output in a minimal `<mxGraphModel>` root so it is valid standalone XML
- [ ] Add `render_ibm_location_snippet(name, shape_type, stroke_color, x, y, w, h)` for
  containers (subnet bands, AZ columns, VPC boundaries)
- [ ] Add `/api/drawio-snippet` POST endpoint to `server.py`
- [ ] Add tests for both snippet functions in `tests/test_drawio.py`

**Relevant Context:**
- IBM node builder: `src/network_picasso/drawio.py` — `DrawioBuilder.ibm_node()` (line 328)
- IBM location builder: `src/network_picasso/drawio.py` — `DrawioBuilder.ibm_location()` (line 430)
- STENCIL_SHAPES dict: `src/network_picasso/drawio.py` (line ~200) — maps service names to stencil IDs
- STENCIL_COLOR dict: `src/network_picasso/drawio.py` — maps categories to IBM brand colors

**Status:** `[x] done`

---

### T4 — Write a Bob Skill for IBM Cloud Diagram Editing

**Intent:** Give Bob a persistent skill document that explains the IBM Cloud diagram conventions,
the MCP tool workflow, and the parent cell ID structure of a Network Picasso generated diagram —
so Bob can answer conversational editing requests accurately without hallucinating stencil names
or breaking the IBM visual language.

**Expected Outcomes:**
- A skill file exists at `.bob/skills/ibm-drawio-editing.md`.
- When activated, the skill tells Bob:
  - The IBM prescribed node pattern (colored square bg + white icon child)
  - IBM brand color palette (Compute green, Network cyan, Security red, Data blue, etc.)
  - How to use `list-paged-model` to find parent cell IDs for AZ columns and subnet bands
  - How to call `/api/drawio-snippet` to get IBM-styled XML, then `import-diagram` in `add` mode
  - The STENCIL_SHAPES naming convention (e.g. `ibm--power-vs`, `ibm-cloud--vpc`)
  - Common conversational patterns: "add X to subnet Y in zone Z"

**Todo List:**
- [ ] Write `.bob/skills/ibm-drawio-editing.md` following the Bob skill schema (frontmatter +
  instructions)
- [ ] Include the IBM color palette table
- [ ] Include the step-by-step tool call sequence for "add a node to a subnet band"
- [ ] Include the step-by-step sequence for "add a connector between two existing nodes"
- [ ] Include the step-by-step sequence for "delete a node"
- [ ] Test the skill by activating it and asking Bob a diagram editing question

**Relevant Context:**
- Skill schema and frontmatter rules: use the `create-skill` Bob skill for guidance
- STENCIL_SHAPES: `src/network_picasso/drawio.py` lines ~200–300
- STENCIL_COLOR: `src/network_picasso/drawio.py` lines ~100–125
- IBM prescribed node pattern: `src/network_picasso/drawio.py` `ibm_node()` method (line 328)

**Status:** `[x] done`

---

### T5 — Multi-Page Generation (context + logical + deployment as tabs)

**Intent:** Use the MCP `create-page` and `import-diagram` tools to push all three diagram types
(context, logical, deployment) as separate pages into a single Draw.io document in the MCP editor.
This replaces the current single-type export with a professional three-tab deliverable.

**Expected Outcomes:**
- A new "Generate all pages" button in the diagram step.
- Clicking it generates all three diagram types and imports them as named pages in the MCP editor.
- Page names: "Context", "Logical Architecture", "Deployment".
- If the MCP editor is not running, falls back to downloading a multi-page XML file.

**Todo List:**
- [ ] Add `render_all_diagrams(architecture)` helper to `drawio.py` that returns a dict of
  `{ "context": xml, "logical": xml, "deployment": xml }`
- [ ] Extend `mcp_bridge.py` with `open_all_pages(architecture_path)` that calls `import-diagram`
  for each type using page management tools
- [ ] Add `/api/drawio-mcp-all-pages` endpoint to `server.py`
- [ ] Add "Generate all pages" button to `ui/src/App.tsx` diagram step
- [ ] Add a fallback: when MCP server unreachable, merge all three diagrams into a single
  multi-page `.drawio` XML file for download

**Relevant Context:**
- `render_drawio()` in `src/network_picasso/drawio.py` (line 1127) — accepts `diagram_type` param
- MCP tools: `create-page`, `import-diagram` (mode: `new-page`)
- Current diagram type dropdown: `ui/src/App.tsx` line ~1412

**Status:** `[x] done`

---

## Implementation Order

Run sub-tasks in this order. Each is independent enough to commit separately:

```
T1 (MCP registration) → T2 (Open in Editor button) → T3 (Snippet API) → T4 (Skill) → T5 (Multi-page)
```

T3 must complete before T4, since the skill references the snippet API. T2 can start after T1.
T5 depends on T2 and T3 being complete.

---

## Notes for Implementer

- The MCP server uses `npx -y drawio-mcp-server` — first run downloads the package (~30s). After
  that, npx uses the cached version.
- Node.js v22+ is required. Check with `node --version` before writing the MCP config.
- The built-in editor at `localhost:4000` exposes an HTTP API for importing diagrams. The exact
  endpoint is discovered from the server's own docs/source — check
  `/tmp/drawio-mcp-server/packages/drawio-mcp-server/` for the HTTP handler.
- IBM Cloud stencil shapes in the editor are only auto-discovered if the IBM stencil library is
  loaded. Prefer generating IBM-styled XML via `drawio.py` (T3) and injecting with
  `import-diagram` rather than relying on `add-cell-of-shape` with IBM shape names.
- The MCP server supports `--transport stdio,http` — use `http` or `stdio` (default). For Bob's
  MCP client, `stdio` is the correct transport (Bob spawns the process).
- Vault Radar false positive: avoid `"key": "#color"` patterns in any new Python dicts. Use
  descriptive key names (e.g. `"icon-color"` not `"key-color"`).
