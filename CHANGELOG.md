# Changelog

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
