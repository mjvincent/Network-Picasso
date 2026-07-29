# Changelog

## 0.6.13 - 2026-07-29

### Added

- Added deterministic extraction and a dedicated deployment renderer for hybrid IBM Cloud Classic to VPC topologies such as UPS VCF ProdNet/TestNet plus ROVS POC.
- Requirements mentioning DirectLink 2.0, Juniper vSRX, IBM Cloud Classic, VCF ProdNet/TestNet, ROVS, VDI, Transit Gateway, and zone CIDRs now produce explicit topology components instead of a generic VPC shell.

### Fixed

- Prevented quality analyzer remediation from adding a PowerVS workspace unless customer requirements or model components explicitly mention PowerVS or Power Virtual Server.
- ROVS POC CIDR/zone subnet details are preserved as diagram-ready subnet facts.

## 0.6.12 - 2026-07-29

### Changed

- Draw.io XML, preview, diagrams.net open, MCP single-page open, MCP all-pages open, and multipage export now all apply the saved Ollama render-planning mode when enabled, instead of only applying phi4-mini during the basic generate action.
- **Copy + open MCP** now pushes the current five-page Network Picasso diagram into the live MCP editor before handing off the Bob prompt, reducing the chance that a stale Omnicare or sample design remains visible.
- Option C now prefers the active architecture model from the UI when both an active model and a saved path are present.

### Fixed

- Prevented diagrams.net/MCP open actions from silently falling back to rules-only or stale file-path rendering when the user is working from a newly pasted description.

## 0.6.11 - 2026-07-29

### Added

- Added **Design fresh environment** in the requirements step so a pasted customer description can replace the current architecture model instead of merging into stale project state.
- Added backend support for rebuilding a fresh architecture directly from requirements text.

### Fixed

- Prevented new non-healthcare requirements from inheriting prior healthcare/medical-imaging components when the user intends a new environment.
- Generic object storage and DR requirement enrichment now uses neutral labels unless the requirements explicitly mention medical imaging or WDC/us-east.
- Narrative requirements now map common IBM Cloud signals to diagram-ready labels such as Workload VPC, VPC VSI workload tier, Public Load Balancer, Activity Tracker, and VPC Flow Logs instead of sentence fragments.
- Requirements saves now refresh open design questions after enrichment.

## 0.6.10 - 2026-07-29

### Added

- The finished PDF packet now includes a cover page with customer, project, source, export timestamp, and architecture summary fields.
- Added a table of contents, page numbering, one diagram per page, and report appendices for architecture summary, IBM pattern alignment, diagram quality, and assumptions/open questions.

### Changed

- The PDF packet now uses the same Markdown reports that are included in the ZIP, keeping the printable packet aligned with the export package.
- Simplified the PDF cover styling after visual QA so it renders cleanly in macOS Quick Look.

## 0.6.9 - 2026-07-29

### Added

- Live MCP finished exports now include rendered PNG and SVG files for all five Draw.io tabs.
- Finished export packages now include `pdf/network-picasso-diagram-packet.pdf`, assembled from the live Draw.io MCP renders.
- Export packages include `images/manifest.json` and README source notes so sellers can tell whether the package came from the live MCP editor or the generated model.
- The finished package panel now shows the active export source before download.

### Changed

- Live MCP page rendering reuses the connected Draw.io document ID across page exports for a faster package build.

## 0.6.4 - 2026-07-29

### Fixed

- **Copy + open MCP** now opens the Draw.io MCP editor synchronously during the button click before awaiting clipboard access, preventing browser popup blockers from suppressing the editor tab.
- Remediation session status now records whether the MCP editor popup actually opened.

## 0.6.3 - 2026-07-29

### Added

- Remediation target selector for Bob/MCP prompts so sellers can choose Current, a specific Draw.io page, or all five pages before copying a prompt.
- MCP tab verification and rebuild actions in the Bob/MCP remediation panel.
- Bob prompt text now explicitly tells Bob whether to edit only the selected page or all five pages.

## 0.6.2 - 2026-07-28

### Fixed

- MCP all-pages open now replaces and renames existing page slots 0-4 instead of appending behind stale tabs, preventing duplicate Deployment tabs in the live Draw.io MCP editor.
- Single-page MCP opens now rename page 0 to the selected diagram type after replacing content.
- Added MCP bridge tests for stale tab reuse and missing page-slot creation.

## 0.6.1 - 2026-07-28

### Fixed

- Single-page Draw.io exports now set diagram-specific page names, so MCP imports no longer reuse a stale Deployment tab name for the Executive Overview page.
- The MCP all-pages importer now uses the renderer's shared page-name map to keep page labels consistent across saved files and live MCP pushes.
- Corrected the all-pages UI status message from four-page to five-page output.

## 0.6.0 - 2026-07-28

### Added

- Remediation session feedback in the diagram step after a Bob/MCP preset is copied.
- Session status now shows copied preset, target page, MCP state at copy time, whether MCP was opened, and whether the diagram has been re-analyzed afterward.

### Changed

- Bob/MCP preset metadata now records target-page intent for clearer seller handoff.

## 0.5.9 - 2026-07-28

### Changed

- Consolidated Bob diagram editing into one primary Bob/MCP remediation area to remove overlap between guided presets and the older editing prompt library.
- Guided remediation cards now offer **Copy prompt** and **Copy + open MCP** actions.
- Clarified that Network Picasso can open the Draw.io MCP editor and copy the prompt, but cannot submit a prompt directly into IBM Bob without a Bob-provided API or deep link.
- Updated documentation to explain the simplified Bob/MCP handoff.

## 0.5.8 - 2026-07-28

### Added

- Guided Bob/MCP remediation presets for label spacing, connector routing, Deployment-page polish, all-five-page review, IBM pattern alignment, and customer-ready preparation.
- Preset prompts now include current quality analyzer findings, IBM pattern checks, five-page diagram structure, and topology-preservation guardrails.

### Changed

- The new Assumptions & Decisions page is recognized by Bob prompt helpers instead of being treated as Deployment.
- README roadmap now treats guided remediation presets as shipped and moves the next opportunity to prompt execution feedback.

## 0.5.7 - 2026-07-28

### Added

- Five-page Draw.io output with a new Assumptions & Decisions page covering IBM pattern traceability, seller validation items, question status, and diagram quality status.
- MCP all-pages push now includes the Assumptions & Decisions page.
- Diagram quality remediations now persist IBM pattern traceability and presentation-review actions into the architecture model.

### Changed

- Updated app and documentation copy from four-page to five-page diagram output.

## 0.5.6 - 2026-07-28

### Added

- Embedded sanitized Network Picasso app screenshots in the user guide for Projects, upload, review, questions, advisor, diagram generation, quality analyzer, Project Activity, restore preview, and export package.
- Local Chrome capture script for refreshing user guide screenshots from the Docker Compose app.

## 0.5.5 - 2026-07-28

### Added

- Screenshot-ready end-to-end user guide covering Docker startup, Projects, intake, advisor, questions, diagrams, quality analysis, restore points, exports, Bob/MCP setup, and troubleshooting.
- User guide screenshot checklist with expected filenames, capture guidance, and sanitization notes.

## 0.5.4 - 2026-07-28

### Added

- Project browser search, status filtering, and sorting controls for customer folders and project workspaces.

## 0.5.3 - 2026-07-28

### Added

- GitHub Actions CI workflow for backend tests, Python dependency audit, UI tests, TypeScript build, npm audit, and Docker Compose image builds.

## 0.5.2 - 2026-07-28

### Added

- Customer-ready project export package with architecture JSON, four-page Draw.io file, architecture summary, IBM pattern alignment report, diagram quality report, assumptions/open questions, and project activity metadata.

## 0.5.1 - 2026-07-28

### Added

- Settings control for autosave restore-point retention, with milestone restore points still retained.
- Apply analyzer fixes action that adds traceable IBM pattern-foundation model updates from quality findings and records deferred Bob/MCP layout work.

## 0.5.0 - 2026-07-28

### Added

- Restore-point retention policy that keeps milestone restore points while pruning excess routine autosaves per project.
- Project Activity now displays the active restore retention policy.
- `NETWORK_PICASSO_AUTOSAVE_RETENTION` environment variable to tune autosave restore-point retention; default is `25`.

## 0.4.9 - 2026-07-28

### Added

- End-to-end user guide covering Docker startup, project workflow, intake, questions, advisor, diagrams, quality analysis, restore points, Bob/MCP, exports, and troubleshooting.
- Screenshot checklist for building a full illustrated usage guide.

### Changed

- Getting Started is now Docker-first and presents the containerized app as the recommended end-user entry point.
- Containerization docs now explicitly call Docker Compose the recommended end-user startup path.

## 0.4.8 - 2026-07-28

### Added

- Restore-point timeline filter in Project Activity for milestones, autosaves, intake/imports, design decisions, quality checks, and restores/syncs.
- Restore-point category tags and visible filtered/total counts so routine autosaves do not hide important checkpoints.

## 0.4.7 - 2026-07-27

### Added

- Restore-point preview endpoint that compares the current project architecture against a selected restore point.
- Restore confirmation modal now shows changed project metadata, IBM pattern, regions, VPCs, core service groups, question counts, requirements, quality score, and added/removed services before restore.

## 0.4.6 - 2026-07-27

### Added

- Recoverable project restore points backed by optional Postgres persistence.
- Project Activity restore-point list with timestamp, optional quality score, and a confirmation-based restore action.
- Restore endpoint that writes the selected architecture snapshot back to the active project's `architecture.json`.

### Changed

- Autosave snapshots are throttled so frequent editing does not flood the project history.
- README persistence guidance now distinguishes file-backed local storage from optional Postgres restore history.

## 0.4.5 - 2026-07-27

### Added

- Bob prompt sections now include informational help bubbles explaining when each prompt group is relevant.
- Bob prompt panel now recommends a next prompt based on the current diagram quality analysis.

## 0.4.4 - 2026-07-27

### Added

- Expanded Bob editing prompt library with grouped prompts for setup, layout, IBM pattern review, seller review, security, resiliency, data flow, and final QA.

## 0.4.3 - 2026-07-27

### Added

- Project Activity panel with autosave status, architecture file metadata, Postgres status, latest quality score, recent events, and export/refresh actions.
- Project activity API endpoint with file metadata fallback and optional Postgres event history.

### Changed

- Diagram quality analysis now records the latest quality score in the active project's architecture metadata.

## 0.4.2 - 2026-07-27

### Added

- Projects navigation now leads the workspace so users start from customer/project organization.
- Customer folders can be created independently from project subfolders.
- Active projects autosave their architecture model to `architecture.json` and optional Postgres persistence.
- Opening a saved project now restores its architecture model and answered/open questions.

### Changed

- Rename, move, and delete actions keep the active workspace state aligned with the underlying project path.

## 0.4.1 - 2026-07-27

### Changed

- Diagram Quality Analyzer now provides a remediation loop with MCP open, Bob quality-fix prompt generation, and re-analysis actions.

## 0.4.0 - 2026-07-27

### Added

- Optional Postgres persistence for customer folders, project subfolders, architecture JSON snapshots, and project events.
- Docker Compose Postgres service with a named volume and non-conflicting optional host port `55432`.
- Persistence status and manual sync API endpoints.

### Changed

- New project creation now uses a customer folder plus required project subfolder.
- Project import/export and destructive project operations now validate paths against the configured projects root.

## 0.3.0 - 2026-07-27

### Added

- Diagram Quality Analyzer endpoint and UI panel.
- Deterministic Draw.io XML checks for label fit, overlap risk, density, and customer-readiness.
- IBM Think Architecture pattern-alignment checks for VPC landing zone, VSI on VPC landing zone, and PowerVS with VPC landing zone foundations.
- Prominent README one-command Docker Compose startup path for end users.

## 0.2.0 - 2026-07-27

### Added

- Architecture Advisor with IBM-pattern recommendation, pillar review, seller next actions, and logical design guidance.
- Four-page Draw.io generation: Executive Overview, Context, Logical Architecture, and Deployment.
- Multipage diagrams.net opening with preserved page tabs.
- Draw.io MCP checklist and copy-ready Bob editing prompts in the UI.
- Dedicated Draw.io MCP handbook for Bob setup and conversational diagram editing.
- Docker Compose deployment with non-conflicting default ports.
- Container-aware MCP bridge configuration through `NETWORK_PICASSO_MCP_BASE_URL`.

### Changed

- Improved hybrid PowerVS DR rendering for DAL/WDC architectures.
- Improved VSI labeling so one extracted profile does not imply one machine or a single allowed VSI profile.
- Updated README and getting-started documentation around the current workflow.

### Fixed

- Stale hub/spoke render-plan data no longer overrides customer-specific hybrid DR designs.
- Docker API image now handles the `LLM Architecture MD Files` path correctly.
- Containerized Network Picasso can detect a host-local Draw.io MCP server.

## 0.1.0

- Initial local-first Network Picasso prototype.
