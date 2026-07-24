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
PYTHONPATH=src python3 -B -m network_picasso.cli ask examples/omnicare/architecture.json
PYTHONPATH=src python3 -B -m network_picasso.cli generate examples/omnicare/architecture.json --type deployment --output outputs/omnicare-deployment.drawio
```

Open the generated `.drawio` file in diagrams.net or the Draw.io desktop app.

## Direction

The agentic flow should use AI for intake, extraction, gap analysis, question generation, and review. Diagram rendering should stay deterministic so architects get repeatable, professional diagrams that can be versioned in Git.
