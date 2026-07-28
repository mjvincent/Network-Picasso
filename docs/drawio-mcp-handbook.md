# Draw.io MCP Handbook

This guide explains how Network Picasso, diagrams.net, and the Draw.io MCP server fit together.
It is written for day-to-day use, not MCP authors.

For the full end-to-end tool walkthrough, including screenshot slots for Projects, intake,
diagram quality, restore points, exports, Bob settings, and the MCP editor, see
[the Network Picasso User Guide](user-guide.md).

## The Short Version

You can use Network Picasso without MCP.

- **Generate all diagram types** opens one diagrams.net window with five pages: Executive Overview, Context, Logical Architecture, Deployment, and Assumptions & Decisions.
- **Option C - Open in diagrams.net** opens the selected single diagram type.
- **Option E - Open in MCP editor** is only for conversational editing through an MCP-aware assistant such as IBM Bob.

Use MCP when you want to say things like:

```text
Add a bastion host to the management subnet.
Move the compliance services into a shared services foundation.
Connect the DAL VPC to the WDC recovery VPC and label it regional DR.
```

## Bob vs VS Code

The repository is currently configured for **IBM Bob** through [.bob/mcp.json](../.bob/mcp.json).
When Bob opens this workspace, it can start `drawio-mcp-server` and expose Draw.io tools to the
assistant.

VS Code can also use MCP only if your VS Code agent/client supports MCP servers and is configured
to run the same command. This repository does not currently include a VS Code-specific MCP config.
The equivalent server command is:

```bash
npx -y drawio-mcp-server --editor --transport stdio,http --host 127.0.0.1 --http-port 4000
```

If your VS Code MCP client asks for a server definition, use the command above and expose the HTTP
editor at `http://127.0.0.1:4000`.

## Mental Model

There are three moving parts:

```text
Network Picasso app      Draw.io MCP server          Bob or MCP-aware agent
http://127.0.0.1:5173    http://127.0.0.1:4000      MCP tools
        |                         ^                    |
        | generates .drawio XML   | edits live tab      |
        +-------------------------+--------------------+
```

Network Picasso generates the diagram. The MCP server hosts a live Draw.io editor tab. Bob uses
MCP tools to inspect and edit that live tab.

## First-Time Setup With Bob

1. Open the `Network Picasso` folder in Bob.
2. Open Bob's MCP panel.
3. Confirm a server named `drawio` appears.
4. Wait if this is the first launch. `npx -y drawio-mcp-server` may take 30 seconds or more the
   first time because it downloads the package.
5. Open `http://127.0.0.1:4000` in your browser if Bob did not open it automatically.
6. In Network Picasso, go to **Step 4 - Generate diagram**.
7. Click **Check** in **Option E - Open in MCP editor**.
8. When the tag says **MCP editor running**, click **Open in MCP editor**.
9. Ask Bob to edit the diagram.

## Recommended Bob Prompt

Use this before asking for edits:

```text
Use the ibm-drawio-editing skill. Inspect the open Draw.io MCP document before making changes.
Use IBM Cloud stencil patterns, keep labels non-overlapping, and preserve the existing architecture pages.
```

Then ask for a specific edit:

```text
On the Deployment page, add a bastion host to the management subnet and connect it to the VSI tier with an SSH label.
```

## Network Picasso Buttons

| Button | What it does | MCP required |
|---|---|---|
| Save Draw.io file | Writes the selected diagram to `outputs/` | No |
| Copy XML | Copies selected diagram XML | No |
| Open in diagrams.net | Opens selected single-page diagram | No |
| Load preview | Shows selected single-page diagram inline | No |
| Open in MCP editor | Pushes selected diagram into `localhost:4000` for Bob edits | Yes |
| Generate all diagram types | Opens one five-page diagrams.net file and saves it to `outputs/network-picasso-all.drawio` | No |
| Open all pages in MCP editor | Pushes all five pages into the MCP editor | Yes |

## In-App MCP Checklist And Bob Prompts

Step 4 includes an MCP checklist under **Option E - Open in MCP editor**:

- Bob MCP server connected
- Draw.io MCP editor tab open
- Diagram loaded into MCP editor
- Prompt Bob for targeted editing

Use **Check** first, then **Open MCP editor tab**, then **Open in MCP editor** or
**Open all pages in MCP editor**. After the diagram is loaded, use the **Bob editing prompts**
buttons to copy a known-good prompt. Start with **Setup Bob**, then use **Clean Labels** or
**Architecture Polish** for a focused edit pass.

## What You Should See

For **Generate all diagram types**, diagrams.net should show one drawing with five page tabs:

- Executive Overview
- Context
- Logical Architecture
- Deployment

For **Option E**, `http://127.0.0.1:4000` should show the diagram that Bob can edit. Bob edits that
live MCP editor tab, not the ordinary `app.diagrams.net` tab opened by the non-MCP workflow.

## Troubleshooting

| Symptom | What to do |
|---|---|
| Option E is disabled | Click **Check** in the MCP card. If it still fails, open Bob's MCP panel and confirm `drawio` is running. |
| `drawio` is missing in Bob | Confirm [.bob/mcp.json](../.bob/mcp.json) exists and reopen the workspace in Bob. |
| Bob shows `drawio` as disconnected but `http://127.0.0.1:4000/health` returns `{"status":"ok"}` | The editor server is running, but Bob has not connected its MCP client. In Bob, stop/start or reconnect the `drawio` MCP server, then reload the workspace if it remains disconnected. |
| Containerized Network Picasso says MCP is not running while the browser tab is open | The API container must reach the host via `NETWORK_PICASSO_MCP_BASE_URL=http://host.docker.internal:4000`; this is set in `docker-compose.yml`. Rebuild/restart the stack after changing it. |
| First MCP startup is slow | Wait for `npx` to finish downloading `drawio-mcp-server`. |
| `No connected Draw.io documents` | Open `http://127.0.0.1:4000` in a browser tab, then retry **Open in MCP editor**. |
| Only one page opens from Generate all diagram types | Refresh the Network Picasso app and click the button again. The current app uses a compressed multipage draw.io URL so the five tabs should appear. |
| Bob edits the wrong page | Ask Bob to list the pages first and target the page by name, for example "Deployment page". |
| Labels overlap after Bob edits | Ask Bob to run a layout cleanup pass and preserve IBM container boundaries. |

## Safe Workflow

1. Generate all pages from Network Picasso.
2. Review the five-page file in diagrams.net, including the Assumptions & Decisions traceability page.
3. Use MCP only for targeted edits.
4. Save the edited `.drawio` file from diagrams.net.
5. Keep generated outputs or customer deliverables out of Git unless intentionally needed.
