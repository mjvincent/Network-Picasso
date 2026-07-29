# User Guide Screenshot Checklist

Store screenshots for [the user guide](../../user-guide.md) in this folder.

Recommended capture size: browser window around `1440x1000` or larger. Use the Docker Compose
app at `http://127.0.0.1:5174` so screenshots match the end-user path.

| File | Capture |
|---|---|
| `01-docker-compose-start.png` | Terminal after `docker compose up --build` shows UI, API, and Postgres running |
| `02-projects-workspace.png` | Captured: Projects tab with folder actions, search, status filter, and sort controls |
| `03-upload-source-files.png` | Captured: Upload step with accepted file types and active project visible |
| `04-review-model.png` | Captured: Review model step with extracted IBM Cloud service categories |
| `05-design-questions.png` | Captured: Questions step with design-gap prompts and answer fields |
| `06-architecture-advisor.png` | Captured: Advisor section with recommended IBM pattern, rationale, logical design, and seller next actions |
| `07-generate-diagrams.png` | Captured: Diagram generation step with all diagram/MCP actions visible |
| `08-quality-analyzer.png` | Captured: Diagram quality analyzer score, findings, IBM pattern checks, and remediation buttons |
| `09-project-activity.png` | Captured: Project Activity showing autosave, Postgres status, events, restore filters, and quality score |
| `10-restore-preview.png` | Captured: Restore preview modal comparing current and selected restore-point values |
| `11-export-package.png` | Captured: Finished export package card showing export source, style memory state, and package action after a generated/analyzed project is active |
| `12-bob-mcp-settings.png` | IBM Bob settings showing MCP server `drawio` connected |
| `13-drawio-mcp-editor.png` | Draw.io MCP editor at `http://127.0.0.1:4000` with a diagram loaded |

Captured app screenshots use the sanitized `sample-healthcare / medical-imaging-dr` demo project.

The app screenshots can be refreshed with:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-sandbox --remote-debugging-port=9223 --user-data-dir=/tmp/network-picasso-chrome --window-size=1440,1000 about:blank
node scripts/capture_user_guide_screenshots.mjs
```

The Docker terminal, Bob MCP settings, and loaded MCP editor screenshots still require manual
capture because they depend on the user's desktop/Bob state.

Capture tips:

- Use a sample or sanitized customer project.
- Avoid showing confidential customer names, pricing, credentials, or private host paths.
- Keep browser zoom near `100%`.
- Prefer the Carbon UI content area over full desktop screenshots unless documenting Docker or Bob settings.
- Re-capture screenshots after major UI changes so the guide stays trustworthy.
