# Changelog

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
