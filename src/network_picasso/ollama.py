"""Thin Ollama HTTP client — uses only urllib.request, no third-party dependencies."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM = """\
You are an IBM Cloud architecture analyst. Extract all IBM Cloud components mentioned in the
provided document text and return them as a JSON array. For each component, identify the most
appropriate ibm_cloud key from this list:

  regions       – IBM Cloud regions (e.g. us-south, eu-de, jp-tok) and availability zones
  vpcs          – Virtual Private Cloud instances and their purposes
  zones         – Availability zones within a region (zone-1, zone-2, zone-3)
  subnets       – Subnets within VPCs (public, private, management, data tiers)
  connectivity  – Connectivity services: Transit Gateway, Direct Link, VPN Gateway, interconnects
  ingress       – Ingress services: IBM Cloud Internet Services, Application Load Balancers, public IPs
  compute       – Compute workloads: VSI, ROKS/OpenShift, Bare Metal, PowerVS, Code Engine
  data          – Data and storage services: Databases for PostgreSQL/MySQL/MongoDB, Object Storage, Block/File Storage
  private_endpoints – VPE gateways and private service access configurations
  dns           – DNS zones, records, resolvers (IBM Cloud DNS Services, private DNS)
  security      – Security controls: IAM, Key Protect/HPCS, Secrets Manager, Security Groups, NACLs, Certificate Manager
  observability – Monitoring, logging, alerting: IBM Cloud Monitoring, Log Analysis, Activity Tracker, flow logs
  backup_dr     – Backup, replication, and disaster recovery services and RPO/RTO targets

Return ONLY a valid JSON array with no markdown fences, no commentary. Each element must have
exactly these fields:
  name           – human-readable component name (string)
  suggested_key  – one of the ibm_cloud keys listed above (string)
  purpose        – one-sentence description of what this component does (string)
  confidence     – float between 0.0 and 1.0 indicating extraction confidence (number)
  notes          – any additional context or caveats (string, may be empty)

Example:
[
  {"name": "us-south", "suggested_key": "regions", "purpose": "Primary deployment region", "confidence": 0.95, "notes": ""},
  {"name": "ROKS cluster", "suggested_key": "compute", "purpose": "Container workload platform", "confidence": 0.82, "notes": "Version not specified"}
]
"""

_EXTRACTION_USER_TMPL = """\
Extract all IBM Cloud components from the following document text:

---
{text}
---

Return only the JSON array.
"""

_GAP_ANALYSIS_SYSTEM = """\
You are an IBM Cloud network architect reviewing an architecture design. You will be given the
current architecture model as JSON. Your task is to identify architectural gaps and design
questions that go BEYOND the standard rule-based checks (regions, vpcs, subnets, connectivity,
ingress, compute, security, private_endpoints, dns, observability, backup_dr).

Focus on nuanced gaps such as:
- Cross-region latency and data residency implications
- Specific security boundary enforcement between tiers
- Missing HA or resilience patterns for detected services
- Incomplete connectivity paths (e.g. PowerVS to VPC, on-premises to IBM Cloud)
- Service-specific private endpoint coverage gaps
- Compliance and audit trail completeness for the detected environment

Return ONLY a valid JSON array with no markdown fences, no commentary. Each element must have:
  area      – short area label (string, e.g. "High availability")
  question  – the design question to ask the architect (string)
  guidance  – best-practice guidance answering the question (string)
  source    – always the string "llm"

Return an empty array [] if you find no additional gaps.
"""

_RENDER_PLAN_SYSTEM = """\
You are an IBM Cloud senior architect. You will be given:
1. An architecture model extracted from customer documents (JSON)
2. The IBM Cloud diagram style guide
3. The IBM Cloud deployment architecture guide

Your task is to produce a JSON "render plan" that tells the diagram renderer exactly what to draw.
Base every decision on the provided architecture model and answered questions — do NOT invent
components that are not in the model.

Reference patterns from ibm.com/think/architectures/patterns:
  • basic-vpc         – single VPC, internet-facing, simple workload
  • mzr               – single VPC spanning all 3 AZs, production HA
  • hub-and-spoke     – Edge VPC + one or more workload VPCs + Transit Gateway
  • three-tier-vpc    – presentation / application / data subnet tiers in one VPC
  • hybrid            – Direct Link or VPN connecting on-premises to IBM Cloud
  • powervs           – PowerVS workspace connected via Transit Gateway
  • fsc               – Financial Services Cloud: no public egress, all VPE, HPCS, SCC

Return ONLY a single JSON object (no markdown, no commentary) with exactly these fields:

{
  "pattern":         string,   // one of the pattern names above, or "custom"
  "pattern_reason":  string,   // one sentence explaining why this pattern was chosen
  "has_on_prem":     bool,     // true if Direct Link or VPN is in connectivity
  "has_tgw":         bool,     // true if Transit Gateway is in connectivity
  "has_powervs":     bool,     // true if PowerVS is in compute
  "has_dr":          bool,     // true if a second region is present
  "az_count":        int,      // 1, 2, or 3 — number of availability zones to draw
  "vpcs": [                    // one entry per VPC to draw (from extracted vpcs list)
    {
      "name":    string,
      "purpose": string,       // e.g. "Edge VPC — internet ingress", "Production VPC"
      "tiers":   [string]      // subnet tiers to show: "Public", "Private", "Management", "Data"
    }
  ],
  "shared_services": [string], // service names to show in the shared services panel
  "connectivity_label": string // label for the connectivity bar (e.g. "Direct Link 2.0")
}
"""

_RENDER_PLAN_USER_TMPL = """\
Architecture model:
{architecture_json}

IBM Cloud deployment architecture guide:
{deployment_guide}

IBM Cloud style guide:
{style_guide}

Based on the architecture model above, produce the render plan JSON object.
Only include what is present in the model. Do not invent components.
"""

_GAP_ANALYSIS_USER_TMPL = """\
Review this IBM Cloud architecture model and identify design gaps beyond the standard checks:

{architecture_json}

Return only the JSON array.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict, timeout: int) -> dict:
    """POST JSON to *url* with *timeout* seconds. Returns parsed response dict."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str, timeout: int) -> dict:
    """GET *url* with *timeout* seconds. Returns parsed response dict."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_json_response(raw: str, context: str) -> list:
    """Parse a JSON array from raw LLM response text. Returns empty list on failure."""
    raw = raw.strip()
    # Strip markdown code fences if the model added them anyway.
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        print(f"[ollama] {context}: expected JSON array, got {type(result).__name__}")
        return []
    except json.JSONDecodeError as exc:
        print(f"[ollama] {context}: malformed JSON — {exc}")
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_models(base_url: str) -> list[str]:
    """Return model names available at *base_url*. Returns [] if unreachable."""
    try:
        data = _get(f"{base_url}/api/tags", timeout=10)
        return [m["name"] for m in data.get("models", []) if "name" in m]
    except (URLError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"[ollama] list_models: {exc}")
        return []


def test_connection(base_url: str) -> bool:
    """Return True if Ollama is reachable at *base_url*, False otherwise."""
    try:
        _get(f"{base_url}/api/tags", timeout=10)
        return True
    except (URLError, OSError):
        return False


def extract_components(text: str, model: str, base_url: str) -> list[dict]:
    """
    Ask the LLM to extract IBM Cloud components from *text*.

    Returns a list of dicts with keys: name, suggested_key, purpose, confidence, notes.
    Returns [] if Ollama is unreachable or returns malformed JSON.
    """
    prompt = (
        f"System:\n{_EXTRACTION_SYSTEM}\n\n"
        f"User:\n{_EXTRACTION_USER_TMPL.format(text=text[:12000])}"
    )
    try:
        data = _post(
            f"{base_url}/api/generate",
            {"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        raw = data.get("response", "")
        return _parse_json_response(raw, "extract_components")
    except (URLError, OSError, json.JSONDecodeError) as exc:
        print(f"[ollama] extract_components: {exc}")
        return []


def plan_render(architecture: dict, model: str, base_url: str,
                deployment_guide: str = "", style_guide: str = "") -> dict:
    """Ask the LLM to decide the reference architecture pattern and render plan.

    Reads the extracted architecture model + IBM MD guide files and returns a
    structured render plan dict.  The renderer uses this instead of its own
    heuristics when in Ollama mode.

    Returns a render plan dict, or {} if Ollama is unreachable / returns bad JSON.
    Keys: pattern, pattern_reason, has_on_prem, has_tgw, has_powervs, has_dr,
          az_count, vpcs, shared_services, connectivity_label.
    """
    compact = {k: v for k, v in architecture.items() if k != "sources"}
    arch_json = json.dumps(compact, indent=2)[:6000]
    prompt = (
        f"System:\n{_RENDER_PLAN_SYSTEM}\n\n"
        f"User:\n{_RENDER_PLAN_USER_TMPL.format(
            architecture_json=arch_json,
            deployment_guide=deployment_guide[:2000],
            style_guide=style_guide[:1000],
        )}"
    )
    try:
        data = _post(
            f"{base_url}/api/generate",
            {"model": model, "prompt": prompt, "stream": False},
            timeout=90,
        )
        raw = data.get("response", "").strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(ln for ln in lines if not ln.startswith("```")).strip()
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        print(f"[ollama] plan_render: expected JSON object, got {type(result).__name__}")
        return {}
    except (URLError, OSError, json.JSONDecodeError) as exc:
        print(f"[ollama] plan_render: {exc}")
        return {}


def generate_questions(architecture: dict, model: str, base_url: str) -> list[dict]:
    """
    Ask the LLM to identify additional design gaps in *architecture*.

    Returns a list of dicts with keys: area, question, guidance, source ("llm").
    Returns [] if Ollama is unreachable or returns malformed JSON.
    """
    # Omit sources list to keep the prompt compact.
    compact = {k: v for k, v in architecture.items() if k != "sources"}
    arch_json = json.dumps(compact, indent=2)[:8000]
    prompt = (
        f"System:\n{_GAP_ANALYSIS_SYSTEM}\n\n"
        f"User:\n{_GAP_ANALYSIS_USER_TMPL.format(architecture_json=arch_json)}"
    )
    try:
        data = _post(
            f"{base_url}/api/generate",
            {"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        raw = data.get("response", "")
        items = _parse_json_response(raw, "generate_questions")
        # Ensure every item has source: "llm".
        for item in items:
            item["source"] = "llm"
        return items
    except (URLError, OSError, json.JSONDecodeError) as exc:
        print(f"[ollama] generate_questions: {exc}")
        return []
