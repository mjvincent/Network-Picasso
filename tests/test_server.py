from __future__ import annotations

import json
import pathlib

import pytest

from network_picasso.intake import backfill_answer_into_model
from network_picasso.server import (
    atomic_write_json,
    normalize_sources,
    run_intake,
    safe_filename,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _make_csv(directory: pathlib.Path, name: str = "bom.csv") -> pathlib.Path:
    p = directory / name
    p.write_text(
        "Component,Category,Region,Notes\n"
        "Red Hat OpenShift on IBM Cloud,Compute,us-south,Runtime\n"
        "IBM Cloud Databases for PostgreSQL,Data,us-south,Database\n"
    )
    return p


def test_run_intake_writes_file(tmp_path):
    """run_intake() writes a valid architecture.json to the output path."""
    _make_csv(tmp_path)
    out = tmp_path / "architecture.json"
    arch, gaps, pending = run_intake(tmp_path, out, project_name="Test")
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert "project" in on_disk
    assert on_disk["project"]["name"] == "Test"
    assert "ibm_cloud" in on_disk


def test_run_intake_preserves_answers(tmp_path):
    """Answers in a pre-existing architecture file survive a re-run of run_intake()."""
    _make_csv(tmp_path)
    out = tmp_path / "architecture.json"
    # First run
    arch, _, _ = run_intake(tmp_path, out, project_name="Test")
    # Inject a fake answered entry
    arch["questions"]["answered"].append({
        "area": "Subnet design",
        "question": "Which subnets?",
        "answer": "Three tiers.",
        "source": "architect",
        "timestamp": "2024-01-01T00:00:00Z",
    })
    out.write_text(json.dumps(arch))
    # Second run — answered entry must survive
    arch2, _, _ = run_intake(tmp_path, out, project_name="Test")
    answered = arch2["questions"]["answered"]
    assert len(answered) >= 1
    assert answered[0]["area"] == "Subnet design"


def test_backfill_subnets():
    """backfill_answer_into_model with 'subnet' in answer adds to ibm_cloud.subnets."""
    arch: dict = {"ibm_cloud": {}, "questions": {"answered": [], "open": []}}
    # Use a short name-like answer so concise_name produces a usable component name
    backfill_answer_into_model(arch, "Subnet design", "public subnet tier")
    assert len(arch["ibm_cloud"].get("subnets", [])) >= 1


def test_backfill_regions():
    """backfill_answer_into_model with 'us-south' in answer adds to ibm_cloud.regions."""
    arch: dict = {"ibm_cloud": {}, "questions": {"answered": [], "open": []}}
    backfill_answer_into_model(arch, "Regions and availability", "Primary region is us-south, DR in us-east.")
    regions = [r["name"] for r in arch["ibm_cloud"].get("regions", [])]
    assert "us-south" in regions


def test_normalize_sources():
    """normalize_sources makes file paths relative to the repo root."""
    arch = {
        "sources": [{"file": str(REPO_ROOT / "examples/sample/architecture.json"), "type": "json", "records": 1}]
    }
    normalize_sources(arch)
    assert not pathlib.Path(arch["sources"][0]["file"]).is_absolute()
    assert arch["sources"][0]["file"].startswith("examples")


def test_safe_filename():
    """safe_filename strips path components and sanitizes unsafe chars."""
    result = safe_filename("../../etc/passwd")
    assert "/" not in result
    assert ".." not in result
    assert result  # Not empty


def test_atomic_write_json(tmp_path):
    """atomic_write_json writes valid JSON and leaves no .tmp file."""
    out = tmp_path / "test.json"
    data = {"key": "value", "number": 42}
    atomic_write_json(out, data)
    assert out.exists()
    assert not (tmp_path / "test.tmp").exists()
    on_disk = json.loads(out.read_text())
    assert on_disk == data
