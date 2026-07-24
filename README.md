# Network Picasso

Agentic network diagram creator for IBM Cloud architecture.

Network Picasso is a local-first workflow for turning architecture notes, bills of material, customer spreadsheets, and architect answers into professional Draw.io network diagrams. The initial focus is IBM Cloud on VPC, including VSI, Red Hat OpenShift on IBM Cloud, Bare Metal on VPC, and PowerVS-adjacent architectures.

## Current MVP

- Markdown prompt guidance lives in `LLM Architecture MD Files/`.
- The canonical architecture data model lives in `schemas/architecture.schema.json`.
- IBM Cloud review prompts and best-practice checks live in `rules/`.
- A small Python CLI can ask initial design-gap questions and generate starter `.drawio` XML.

## Try It Locally

```bash
PYTHONPATH=src python3 -B -m network_picasso.cli intake examples/sample-inputs --project-name "Sample Healthcare" --output examples/sample/architecture.json
PYTHONPATH=src python3 -B -m network_picasso.cli ask examples/sample/architecture.json
PYTHONPATH=src python3 -B -m network_picasso.cli generate examples/sample/architecture.json --type deployment --output outputs/network-picasso-deployment.drawio
```

Open the generated `.drawio` file in diagrams.net or the Draw.io desktop app.

## Carbon UI

Start the local API:

```bash
PYTHONPATH=src python3 -B -m network_picasso.server
```

Start the Carbon React UI:

```bash
cd ui
npm install
npm run dev
```

Then open `http://127.0.0.1:5173`.

The first screen guides the user to upload one or more source files:

- BOM exports
- IBM Cloud Solutioning pricing workbooks
- Customer spreadsheets
- Architecture notes
- Markdown, text, CSV, TSV, JSON, and XLSX files

After parsing, the app shows pointed design questions with best-practice coaching and can generate a starter Draw.io diagram from the extracted architecture model.

## Direction

The agentic flow should use AI for intake, extraction, gap analysis, question generation, and review. Diagram rendering should stay deterministic so architects get repeatable, professional diagrams that can be versioned in Git.
