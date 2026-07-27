# Changelog

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
