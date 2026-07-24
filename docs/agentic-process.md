# Network Picasso Agentic Process

Network Picasso converts customer materials into professional IBM Cloud architecture diagrams. The first implementation is local-first and deterministic: AI helps extract, reason, ask questions, and review, while code renders the Draw.io XML.

## Workflow

1. Intake source material.
   - Architecture notes
   - Bills of material
   - Customer spreadsheets
   - Existing Markdown prompt guidance
   - Architect-entered answers

2. Normalize inputs into `schemas/architecture.schema.json`.
   - Preserve source facts.
   - Mark assumptions explicitly.
   - Leave unknown values empty so the question engine can ask about them.

3. Ask pointed architecture questions.
   - IBM Cloud regions
   - VPC and subnet tiers
   - Direct Link, VPN, Transit Gateway, and internet ingress
   - ROKS, VSI, Bare Metal on VPC, PowerVS, and data services
   - IAM, secrets, keys, logging, monitoring, audit, backup, and DR

4. Review against rule packs.
   - `rules/ibm-cloud-vpc-networking.yaml`
   - `rules/ibm-cloud-powervs.yaml`
   - `rules/security-observability.yaml`

5. Generate Draw.io.
   - Context diagram for executive audiences
   - Logical architecture diagram for architects
   - Deployment architecture diagram for implementation teams

6. Review and refine.
   - Validate boundaries, labels, traffic flow, and visual clutter.
   - Keep architecture changes separate from visual polish.

## Local Runtime Direction

The MVP can run entirely on a Mac with Python and Ollama. Recommended model roles:

- Larger local model for extraction, reasoning, and critique.
- Smaller local model for summaries and cleanup.
- Deterministic Python renderer for Draw.io output.

Future iterations can add a lightweight web UI, spreadsheet upload, RAG over IBM Cloud design guidance, and optional remote model support for teams that allow it.
