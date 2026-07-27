"""Integration tests for the HTTP endpoints in server.py.

Each test spins up a real ThreadingHTTPServer on a random OS-assigned port,
makes an HTTP request, and asserts on the response.  No mocking — just stdlib
urllib.request so dependencies are kept to zero.
"""
from __future__ import annotations

import json
import pathlib
import threading
import urllib.request

import pytest

# The server's REPO_ROOT is computed from the package location, so we need to
# make sure PYTHONPATH is set correctly when running pytest (PYTHONPATH=src).
from network_picasso.server import NetworkPicassoHandler, ThreadingHTTPServer

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixture: live server
# ---------------------------------------------------------------------------

@pytest.fixture()
def server():
    """Start a ThreadingHTTPServer on a random port and yield its base URL."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), NetworkPicassoHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(base: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}{path}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _post(base: str, path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

def test_health(server):
    status, body = _get(server, "/api/health")
    assert status == 200
    assert body["ok"] is True
    assert "repoRoot" in body


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------

def test_get_settings(server):
    status, body = _get(server, "/api/settings")
    assert status == 200
    assert "mode" in body
    assert "ollamaModel" in body


def test_persistence_status_endpoint(server, monkeypatch):
    monkeypatch.delenv("NETWORK_PICASSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    status, body = _get(server, "/api/persistence/status")
    assert status == 200
    assert body["enabled"] is False
    assert body["connected"] is False


# ---------------------------------------------------------------------------
# GET /api/example
# ---------------------------------------------------------------------------

def test_get_example(server):
    status, body = _get(server, "/api/example")
    assert status == 200
    assert "architecture" in body
    assert "questions" in body
    assert isinstance(body["questions"], list)


def test_architecture_review_endpoint(server):
    status, body = _post(server, "/api/architecture-review", {
        "architecture": {
            "project": {"name": "Endpoint review"},
            "ibm_cloud": {
                "vpcs": [{"name": "Production VPC"}],
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "ROKS cluster"}],
                "ingress": [{"name": "Application Load Balancer"}],
            },
        },
        "requirements": "Production workload in IBM Cloud.",
    })
    assert status == 200
    assert "recommendedPattern" in body
    assert "wellArchitected" in body
    assert len(body["wellArchitected"]) == 6
    assert "sellerNextActions" in body


def test_diagram_quality_endpoint(server):
    status, body = _post(server, "/api/diagram-quality", {
        "architecture": {
            "project": {"name": "Endpoint quality"},
            "render_plan": {"pattern": "vsi-vpc"},
            "ibm_cloud": {
                "vpcs": [{"name": "Production VPC"}],
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "VSI workload"}],
            },
        },
        "diagramType": "deployment",
    })
    assert status == 200
    assert "score" in body
    assert "findings" in body
    assert body["ibmPatternChecks"]["name"] == "VSI on VPC landing zone - Standard"


# ---------------------------------------------------------------------------
# GET /api/folders
# ---------------------------------------------------------------------------

def test_get_folders_empty(server, tmp_path, monkeypatch):
    """GET /api/folders on an empty/non-existent root returns an empty list."""
    # Point projectsRoot at a temp dir that has no folders.
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        settings_path.write_text(json.dumps({"projectsRoot": str(tmp_path / "nowhere")}))
        status, body = _get(server, "/api/folders")
        assert status == 200
        assert "folders" in body
        assert isinstance(body["folders"], list)
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/projects  (create project)
# ---------------------------------------------------------------------------

def test_create_project(server, tmp_path, monkeypatch):
    """POST /api/projects creates a project and returns its path."""
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        settings_path.write_text(json.dumps({"projectsRoot": str(tmp_path / "projects")}))
        status, body = _post(server, "/api/projects", {"customer": "Acme Bank", "project": "Q1"})
        assert status == 200
        assert "path" in body
        assert "acme-bank" in body["path"]
        assert "q1" in body["path"]
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_create_project_missing_customer(server):
    """POST /api/projects without customer returns 400."""
    status, body = _post(server, "/api/projects", {"project": "Q1"})
    assert status == 400
    assert "error" in body or "message" in body


# ---------------------------------------------------------------------------
# POST /api/folders/rename
# ---------------------------------------------------------------------------

def test_rename_folder_endpoint(server, tmp_path, monkeypatch):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        # Create the folder first via the API
        _post(server, "/api/projects", {"customer": "acme"})
        # Rename it
        folder_path = f"{root}/acme"
        status, body = _post(server, "/api/folders/rename", {
            "path": str(folder_path), "name": "acme-renamed",
        })
        assert status == 200
        assert body["name"] == "acme-renamed"
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_rename_folder_missing_params(server):
    status, body = _post(server, "/api/folders/rename", {})
    assert status == 400


# ---------------------------------------------------------------------------
# POST /api/folders/delete
# ---------------------------------------------------------------------------

def test_delete_folder_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "to-delete"})
        folder_path = root / "to-delete"
        assert folder_path.exists()
        status, body = _post(server, "/api/folders/delete", {"path": str(folder_path)})
        assert status == 200
        assert body.get("ok") is True
        assert not folder_path.exists()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/projects/rename
# ---------------------------------------------------------------------------

def test_rename_project_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        status, body = _post(server, "/api/projects/rename", {
            "path": str(proj_path), "name": "q1-renamed",
        })
        assert status == 200
        assert body["name"] == "q1-renamed"
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/projects/delete
# ---------------------------------------------------------------------------

def test_delete_project_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        assert proj_path.exists()
        status, body = _post(server, "/api/projects/delete", {"path": str(proj_path)})
        assert status == 200
        assert body.get("ok") is True
        assert not proj_path.exists()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/projects/duplicate
# ---------------------------------------------------------------------------

def test_duplicate_project_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        status, body = _post(server, "/api/projects/duplicate", {
            "path": str(proj_path), "name": "q1-copy",
        })
        assert status == 200
        assert "path" in body
        assert (root / "acme" / "q1-copy").exists()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/projects/move
# ---------------------------------------------------------------------------

def test_move_project_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        _post(server, "/api/projects", {"customer": "contoso"})
        proj_path = root / "acme" / "q1"
        dest_folder = root / "contoso"
        status, body = _post(server, "/api/projects/move", {
            "path": str(proj_path),
            "destFolder": str(dest_folder),
        })
        assert status == 200
        assert "path" in body
        assert (root / "contoso" / "q1").exists()
        assert not (root / "acme" / "q1").exists()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


# ---------------------------------------------------------------------------
# POST /api/answer
# ---------------------------------------------------------------------------

def test_answer_endpoint(server, tmp_path):
    """POST /api/answer persists an answer to the architecture file."""
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Test"},
        "ibm_cloud": {},
        "questions": {"answered": [], "open": ["Which subnets?"]},
        "sources": [],
        "assumptions": [],
        "requirements": [],
    }))
    status, body = _post(server, "/api/answer", {
        "architecturePath": str(arch_path),
        "area": "Subnet design",
        "question": "Which subnets?",
        "answer": "Three tiers: public, private, data.",
        "source": "architect",
    })
    assert status == 200
    assert body.get("ok") is True
    assert "architecture" in body
    on_disk = json.loads(arch_path.read_text())
    answered = on_disk["questions"]["answered"]
    assert len(answered) == 1
    assert answered[0]["answer"] == "Three tiers: public, private, data."
    # Should no longer be in open list
    assert "Which subnets?" not in on_disk["questions"]["open"]
    assert body["architecture"]["questions"]["answered"][0]["answer"] == "Three tiers: public, private, data."


def test_answer_architecture_pattern_updates_render_plan(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Pattern Answer"},
        "ibm_cloud": {},
        "questions": {"answered": [], "open": ["Which pattern?"]},
    }))
    status, body = _post(server, "/api/answer", {
        "architecturePath": str(arch_path),
        "area": "Architecture pattern",
        "question": "Which pattern?",
        "answer": "Use the IBM Hub-and-Spoke Edge VPC pattern.",
        "source": "architect",
    })
    assert status == 200
    assert body["architecture"]["render_plan"]["pattern"] == "hub-and-spoke"
    on_disk = json.loads(arch_path.read_text())
    assert on_disk["render_plan"]["pattern"] == "hub-and-spoke"


def test_generate_drawio_prefers_architecture_path_over_stale_payload(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    output_path = tmp_path / "out.drawio"
    arch_path.write_text(json.dumps({
        "project": {"name": "Fresh"},
        "render_plan": {"pattern": "hub-and-spoke"},
        "ibm_cloud": {"regions": [{"name": "us-south"}]},
    }))
    status, body = _post(server, "/api/generate-drawio", {
        "architecturePath": str(arch_path),
        "architecture": {
            "project": {"name": "Stale"},
            "ibm_cloud": {},
        },
        "diagramType": "deployment",
        "mode": "rules",
        "outputPath": str(output_path),
    })
    assert status == 200
    xml = output_path.read_text()
    assert "Fresh" in xml
    assert "Edge VPC" in xml
    assert "Stale" not in xml


def test_requirements_endpoint_enriches_architecture_model(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "OmniCare"},
        "ibm_cloud": {"regions": [{"name": "us-south"}]},
        "questions": {"answered": [], "open": []},
    }))
    status, body = _post(server, "/api/requirements", {
        "architecturePath": str(arch_path),
        "requirements": "HIPAA medical imaging with PowerVS servers, HA Direct Link, COS archive, NFS storage, and WDC DR site.",
        "source": "text",
    })
    assert status == 200
    arch = body["architecture"]
    assert any("PowerVS" in c["name"] for c in arch["ibm_cloud"]["compute"])
    assert any("Security and Compliance Center" in c["name"] for c in arch["ibm_cloud"]["security"])
    assert any("Direct Link" in c["name"] for c in arch["ibm_cloud"]["connectivity"])
    assert arch["render_plan"]["has_powervs"] is True
    assert arch["render_plan"]["has_dr"] is True


def test_answer_missing_params(server):
    status, body = _post(server, "/api/answer", {"area": "Subnet design"})
    assert status == 400
