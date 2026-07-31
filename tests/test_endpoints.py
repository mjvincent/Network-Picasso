"""Integration tests for the HTTP endpoints in server.py.

Each test spins up a real ThreadingHTTPServer on a random OS-assigned port,
makes an HTTP request, and asserts on the response.  No mocking — just stdlib
urllib.request so dependencies are kept to zero.
"""
from __future__ import annotations

import json
import io
import pathlib
import struct
import threading
import urllib.request
import zipfile
import zlib

import pytest

# The server's REPO_ROOT is computed from the package location, so we need to
# make sure PYTHONPATH is set correctly when running pytest (PYTHONPATH=src).
from network_picasso.server import (
    NetworkPicassoHandler,
    ThreadingHTTPServer,
    build_project_export_package,
    restore_preview_payload,
    save_project_live_drawio,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

UPS_REQUIREMENTS = (
    "We need to create an infrastructure / network diagram for UPS's VCF ProdNet, VCF TestNet "
    "and ROVS POC environment in IBM Cloud. Today UPS connects to IBM Cloud WDC via a DirectLink "
    "2.0 connection into IBM Cloud Classic. The DirectLink terminates on a Juniper vSRX which "
    "routes traffic between on-prem and IBM Cloud ProdNet and TestNet VCF environments. We are "
    "adding a third environment in IBM Cloud VPC in WDC. This environment will be running a ROVS "
    "cluster for VDI testing. It will be in a single zone in us-east-3. ROVS POC subnet- "
    "10.237.240.0/20 10.237.240.0/22 us-east-1 10.237.244.0/22 us-east-2 10.237.248.0/22 "
    "us-east-3 TestNet Supernet: 10.233.128.0/17 Production Supernet: 10.237.0.0/16 We'll need "
    "to show the DirectLink 2.0 connectivity from on-prem to the vSRX, and to a transit gateway "
    "connection to the ROVS POC environment in IBM Cloud VPC."
)


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


def _get_bytes(base: str, path: str) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(f"{base}{path}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


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


def _post_raw(base: str, path: str, payload: dict) -> tuple[int, bytes, dict[str, str]]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _tiny_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    width, height = 2, 2
    rows = b"".join([b"\x00" + b"\xff\xff\xff" * width for _ in range(height)])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


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
    assert body["autosaveRetentionLimit"] >= 1


def test_save_settings_accepts_autosave_retention_limit(server):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        status, body = _post(server, "/api/settings", {"autosaveRetentionLimit": "7"})

        assert status == 200
        assert body["settings"]["autosaveRetentionLimit"] == 7
        saved = json.loads(settings_path.read_text())
        assert saved["autosaveRetentionLimit"] == 7
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


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


def test_apply_diagram_quality_fixes_endpoint(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Apply quality"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "vpcs": [{"name": "Production VPC"}],
            "compute": [{"name": "VSI workload"}],
        },
    }))
    status, body = _post(server, "/api/diagram-quality/apply-fixes", {
        "architecturePath": str(arch_path),
        "diagramType": "deployment",
        "review": {
            "pattern": "vsi-vpc",
            "ibmPatternChecks": {
                "checks": [
                    {"name": "Private endpoints", "present": False},
                    {"name": "Observability services", "present": False},
                ],
            },
            "findings": [{"area": "Label fit", "recommendation": "Increase shape width."}],
        },
    })

    assert status == 200
    assert body["ok"] is True
    assert body["applied"]
    assert body["deferred"]
    saved = json.loads(arch_path.read_text())
    assert "private_endpoints" in saved["ibm_cloud"]
    assert saved["quality"]["lastRemediation"]["source"] == "quality-analyzer"


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


def test_create_folder_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        status, body = _post(server, "/api/folders", {"customer": "Acme Bank"})
        assert status == 200
        assert body["name"] == "acme-bank"
        assert (root / "acme-bank").is_dir()
        assert not (root / "acme-bank" / "uploads").exists()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


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


def test_project_autosave_endpoint(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        architecture = {
            "project": {"name": "Acme Q1"},
            "ibm_cloud": {"regions": [{"name": "us-south"}]},
        }
        status, body = _post(server, "/api/projects/autosave", {
            "path": str(proj_path),
            "architecture": architecture,
        })
        assert status == 200
        assert body["ok"] is True
        saved = json.loads((proj_path / "architecture.json").read_text())
        assert saved["project"]["name"] == "Acme Q1"
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_project_activity_endpoint_returns_file_metadata(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        (proj_path / "architecture.json").write_text(json.dumps({
            "project": {"name": "Acme Q1"},
            "ibm_cloud": {},
        }))
        status, body = _get(server, f"/api/project-activity?path={proj_path}")
        assert status == 200
        assert body["id"] == "acme/q1"
        assert body["file"]["hasArchitecture"] is True
        assert body["file"]["architectureSize"] > 0
        assert "architecture.json" in body["file"]["architecturePath"]
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_project_export_package_endpoint_returns_zip(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q1"})
        proj_path = root / "acme" / "q1"
        (proj_path / "architecture.json").write_text(json.dumps({
            "project": {"name": "Acme Q1", "environment": "Production"},
            "render_plan": {"pattern": "vsi-vpc"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Production VPC"}],
                "compute": [{"name": "VSI workload"}],
            },
            "questions": {"open": ["Confirm RTO?"], "answered": []},
            "assumptions": ["Customer will confirm final region."],
        }))

        status, body, headers = _get_bytes(server, f"/api/project-export-package?path={proj_path}")

        assert status == 200
        assert headers["Content-Type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = archive.namelist()
            assert any(name.endswith("/architecture.json") for name in names)
            assert any(name.endswith("/diagrams/network-picasso-all.drawio") for name in names)
            assert any(name.endswith("/reports/architecture-summary.md") for name in names)
            assert any(name.endswith("/reports/diagram-quality.md") for name in names)
            assert any(name.endswith("/style/style-memory.json") for name in names)
            assert any(name.endswith("/style/style-memory.md") for name in names)
            summary_name = next(name for name in names if name.endswith("/reports/architecture-summary.md"))
            assert "Acme Q1" in archive.read(summary_name).decode()
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_project_export_package_includes_rendered_mcp_assets(tmp_path):
    root = tmp_path / "projects"
    proj_path = root / "acme" / "q1"
    proj_path.mkdir(parents=True)
    (proj_path / "architecture.json").write_text(json.dumps({
        "project": {"name": "Acme Q1", "environment": "Production"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "Production VPC"}],
            "compute": [{"name": "VSI workload"}],
        },
    }))

    body, filename = build_project_export_package(
        proj_path,
        {"projectsRoot": str(root)},
        drawio_xml="<mxfile><diagram name=\"Deployment\" /></mxfile>",
        diagram_source="mcp",
        rendered_assets={
            "assets": [
                {"pageIndex": 0, "pageName": "Executive Overview", "format": "png", "data": _tiny_png()},
                {"pageIndex": 0, "pageName": "Executive Overview", "format": "svg", "data": b"<svg />"},
            ],
        },
    )

    assert filename == "acme-q1-network-picasso.zip"
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = archive.namelist()
        assert any(name.endswith("/images/01-executive-overview.png") for name in names)
        assert any(name.endswith("/images/01-executive-overview.svg") for name in names)
        assert any(name.endswith("/images/manifest.json") for name in names)
        assert any(name.endswith("/pdf/network-picasso-diagram-packet.pdf") for name in names)
        pdf_name = next(name for name in names if name.endswith("/pdf/network-picasso-diagram-packet.pdf"))
        pdf = archive.read(pdf_name)
        assert b"Table of Contents" in pdf
        assert b"Architecture Summary" in pdf
        assert b"IBM Pattern Alignment" in pdf
        assert b"Assumptions And Open Questions" in pdf
        readme_name = next(name for name in names if name.endswith("/README.md"))
        readme = archive.read(readme_name).decode()
        assert "live Draw.io MCP editor" in readme
        assert "pdf/network-picasso-diagram-packet.pdf" in readme


def test_project_export_package_prefers_saved_project_drawio(tmp_path):
    root = tmp_path / "projects"
    proj_path = root / "acme" / "q1"
    proj_path.mkdir(parents=True)
    architecture = {
        "project": {"name": "Acme Q1"},
        "ibm_cloud": {"regions": [{"name": "us-south"}]},
    }
    (proj_path / "architecture.json").write_text(json.dumps(architecture))
    saved_xml = "<mxfile><diagram name=\"Deployment\"><mxGraphModel><root><mxCell id=\"saved\" value=\"Saved Bob layout\" /></root></mxGraphModel></diagram></mxfile>"
    save_project_live_drawio(proj_path, saved_xml, source="test", architecture=architecture)

    body, _filename = build_project_export_package(proj_path, {"projectsRoot": str(root)})

    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        drawio_name = next(name for name in archive.namelist() if name.endswith("/diagrams/network-picasso-all.drawio"))
        assert "Saved Bob layout" in archive.read(drawio_name).decode()


def test_project_diagram_save_endpoint_persists_drawio(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q3"})
        proj_path = root / "acme" / "q3"
        (proj_path / "architecture.json").write_text(json.dumps({
            "project": {"name": "Acme Q3"},
            "ibm_cloud": {},
        }))
        xml = "<mxfile><diagram name=\"Deployment\"><mxGraphModel><root><mxCell id=\"edited\" value=\"Finished edit\" /></root></mxGraphModel></diagram></mxfile>"

        status, body = _post(server, "/api/project-diagram/save", {
            "path": str(proj_path),
            "drawioXml": xml,
            "source": "test",
        })

        assert status == 200
        assert body["ok"] is True
        saved_path = proj_path / "diagrams" / "live-edited.drawio"
        assert "Finished edit" in saved_path.read_text()
        status, activity = _get(server, f"/api/project-activity?path={proj_path}")
        assert status == 200
        assert activity["file"]["hasSavedDrawio"] is True
        assert activity["file"]["savedDrawioSize"] > 0
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_style_memory_save_endpoint_persists_project_style(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q2"})
        proj_path = root / "acme" / "q2"
        (proj_path / "architecture.json").write_text(json.dumps({
            "project": {"name": "Acme Q2", "environment": "Production"},
            "render_plan": {"pattern": "vsi-vpc"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Production VPC"}],
                "compute": [{"name": "VSI workload"}],
            },
        }))

        status, payload = _post(server, "/api/style-memory/save", {
            "path": str(proj_path),
            "name": "Acme preferred Draw.io style",
        })

        assert status == 200
        assert payload["memory"]["name"] == "Acme preferred Draw.io style"
        assert payload["path"].endswith("style-memory.json")
        saved = proj_path / "style-memory.json"
        assert saved.exists()
        assert "promptGuidance" in json.loads(saved.read_text())

        status, payload = _get(server, f"/api/style-memory?path={proj_path}")
        assert status == 200
        assert payload["memory"]["name"] == "Acme preferred Draw.io style"
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_global_style_memory_is_default_until_project_override(server, tmp_path):
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    global_memory_path = REPO_ROOT / "inputs" / "style-memory-default.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original_settings = settings_path.read_text() if settings_path.exists() else None
    original_global = global_memory_path.read_text() if global_memory_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q3"})
        proj_path = root / "acme" / "q3"
        (proj_path / "architecture.json").write_text(json.dumps({
            "project": {"name": "Acme Q3", "environment": "Production"},
            "render_plan": {"pattern": "vsi-vpc"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Production VPC"}],
                "compute": [{"name": "VSI workload"}],
            },
        }))

        status, payload = _post(server, "/api/style-memory/save", {
            "path": str(proj_path),
            "name": "Global preferred Draw.io style",
            "scope": "global",
        })

        assert status == 200
        assert payload["scope"] == "global"
        assert payload["path"].endswith("inputs/style-memory-default.json")

        status, payload = _get(server, f"/api/style-memory?path={proj_path}")
        assert status == 200
        assert payload["scope"] == "global"
        assert payload["memory"]["name"] == "Global preferred Draw.io style"

        status, payload = _post(server, "/api/style-memory/save", {
            "path": str(proj_path),
            "name": "Project override Draw.io style",
            "scope": "project",
        })
        assert status == 200
        assert payload["scope"] == "project"

        status, payload = _get(server, f"/api/style-memory?path={proj_path}")
        assert status == 200
        assert payload["scope"] == "project"
        assert payload["memory"]["name"] == "Project override Draw.io style"
    finally:
        if original_settings is not None:
            settings_path.write_text(original_settings)
        elif settings_path.exists():
            settings_path.unlink()
        if original_global is not None:
            global_memory_path.write_text(original_global)
        elif global_memory_path.exists():
            global_memory_path.unlink()


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


def test_drawio_xml_prefers_architecture_path_over_stale_payload(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "UPS VCF ROVS"},
        "requirements": [{"text": UPS_REQUIREMENTS, "source": "test"}],
        "ibm_cloud": {"regions": [{"name": "us-east"}]},
    }))

    status, raw, _headers = _post_raw(server, "/api/drawio-xml", {
        "architecturePath": str(arch_path),
        "architecture": {
            "project": {"name": "Old Omnicare"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "Medical imaging processing VSIs"}],
            },
        },
        "diagramType": "deployment",
        "mode": "rules",
    })

    xml = raw.decode()
    assert status == 200
    assert "UPS VCF ROVS" in xml
    assert "VCF ProdNet" in xml
    assert "VCF TestNet" in xml
    assert "ROVS POC VPC" in xml
    assert "Juniper vSRX" in xml
    assert "DirectLink 2.0" in xml
    assert "Old Omnicare" not in xml
    assert "Medical imaging processing VSIs" not in xml


def test_drawio_multipage_prefers_architecture_path_over_stale_payload(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    output_path = tmp_path / "all.drawio"
    arch_path.write_text(json.dumps({
        "project": {"name": "UPS VCF ROVS"},
        "requirements": [{"text": UPS_REQUIREMENTS, "source": "test"}],
        "ibm_cloud": {"regions": [{"name": "us-east"}]},
    }))

    status, body = _post(server, "/api/drawio-multipage", {
        "architecturePath": str(arch_path),
        "architecture": {
            "project": {"name": "Old Omnicare"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "Medical imaging processing VSIs"}],
            },
        },
        "mode": "rules",
        "forceRegenerate": True,
        "includeXml": True,
        "outputPath": str(output_path),
    })

    assert status == 200
    assert body["source"] == "generated"
    xml = body["xml"]
    for expected in ("Executive Overview", "VCF ProdNet", "VCF TestNet", "ROVS POC VPC", "Transit Gateway"):
        assert expected in xml
    assert "Old Omnicare" not in xml
    assert "Medical imaging processing VSIs" not in xml


def test_mcp_all_pages_prefers_architecture_path_over_stale_payload(server, tmp_path, monkeypatch):
    from network_picasso import server as server_module

    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "UPS VCF ROVS"},
        "requirements": [{"text": UPS_REQUIREMENTS, "source": "test"}],
        "ibm_cloud": {"regions": [{"name": "us-east"}]},
    }))
    captured = {}
    monkeypatch.setattr(server_module._mcp, "is_running", lambda: True)
    monkeypatch.setattr(server_module._mcp, "open_multipage_diagram_in_editor", lambda xml, **kwargs: captured.update({"xml": xml, "kwargs": kwargs}) or {"ok": True})
    monkeypatch.setattr(server_module._mcp, "open_all_pages", lambda _diagrams: pytest.fail("all pages should open atomically as a multipage Draw.io document"))

    status, body = _post(server, "/api/drawio-mcp-all-pages", {
        "architecturePath": str(arch_path),
        "architecture": {
            "project": {"name": "Old Omnicare"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "Medical imaging processing VSIs"}],
            },
        },
        "mode": "rules",
        "forceRegenerate": True,
    })

    assert status == 200
    assert body["source"] == "generated"
    assert "VCF ProdNet" in captured["xml"]
    assert "ROVS POC VPC" in captured["xml"]
    assert "Old Omnicare" not in captured["xml"]
    assert "Medical imaging processing VSIs" not in captured["xml"]


def test_drawio_xml_uses_active_architecture_payload_without_path(server):
    status, raw, _headers = _post_raw(server, "/api/drawio-xml", {
        "architecture": {
            "project": {"name": "Retail Analytics"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Workload VPC"}],
                "compute": [{"name": "VPC VSI workload tier"}],
                "data": [{"name": "Cloud Object Storage archive"}],
                "ingress": [{"name": "Public Load Balancer"}],
            },
        },
        "diagramType": "deployment",
        "mode": "rules",
    })

    xml = raw.decode()
    assert status == 200
    assert "Retail Analytics" in xml
    assert "VPC VSI workload tier" in xml
    assert "Medical imaging processing VSIs" not in xml


def test_set_pattern_override_is_preserved_during_project_render(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "UPS VCF ROVS"},
        "render_plan": {
            "pattern": "mzr",
            "pattern_name": "Multi-Zone VPC (MZR)",
            "pattern_source": "architect",
        },
        "requirements": [{"text": UPS_REQUIREMENTS, "source": "test"}],
        "ibm_cloud": {
            "regions": [{"name": "us-east"}],
        },
    }))

    status, raw, _headers = _post_raw(server, "/api/drawio-xml", {
        "architecturePath": str(arch_path),
        "diagramType": "deployment",
        "mode": "rules",
    })

    assert status == 200
    on_disk = json.loads(arch_path.read_text())
    assert on_disk["render_plan"]["pattern"] == "mzr"
    assert on_disk["render_plan"]["pattern_source"] == "architect"
    assert "VCF ProdNet" in raw.decode()


def test_set_pattern_enriches_hybrid_classic_requirements(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "UPS VCF ROVS"},
        "requirements": [{"text": UPS_REQUIREMENTS, "source": "test"}],
        "ibm_cloud": {},
    }))

    status, body = _post(server, "/api/set-pattern", {
        "architecturePath": str(arch_path),
        "patternId": "hybrid-classic-vpc",
        "patternName": "Hybrid Classic to VPC Transit Gateway",
    })

    assert status == 200
    assert body["renderPlan"]["pattern"] == "hybrid-classic-vpc"
    assert body["renderPlan"]["pattern_source"] == "architect"
    assert body["renderPlan"]["topology_variant"] == "classic-vcf-rovs"
    on_disk = json.loads(arch_path.read_text())
    names = {
        item["name"]
        for values in on_disk["ibm_cloud"].values()
        if isinstance(values, list)
        for item in values
        if isinstance(item, dict)
    }
    assert "VCF ProdNet" in names
    assert "Juniper vSRX" in names
    assert "Transit Gateway" in names


def test_drawio_xml_applies_ollama_render_plan(server, monkeypatch):
    from network_picasso import server as server_module

    calls = []

    def fake_plan_render(architecture, model, base_url, deployment_guide="", style_guide=""):
        calls.append((architecture["project"]["name"], model, bool(deployment_guide), bool(style_guide)))
        return {
            "pattern": "hub-and-spoke",
            "pattern_reason": "Retail workload needs separated edge and workload VPCs.",
            "has_on_prem": False,
            "has_tgw": True,
            "has_powervs": False,
            "has_dr": False,
            "az_count": 3,
            "vpcs": [
                {"name": "Edge VPC", "purpose": "Internet ingress", "tiers": ["Public", "Management"]},
                {"name": "Workload VPC", "purpose": "Private application and data tiers", "tiers": ["Private", "Data"]},
            ],
            "shared_services": ["Activity Tracker", "VPC Flow Logs"],
            "connectivity_label": "",
        }

    monkeypatch.setattr(server_module._ollama, "plan_render", fake_plan_render)

    status, raw, _headers = _post_raw(server, "/api/drawio-xml", {
        "architecture": {
            "project": {"name": "Retail Analytics"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Workload VPC"}],
                "compute": [{"name": "VPC VSI workload tier"}],
                "ingress": [{"name": "Public Load Balancer"}],
            },
        },
        "diagramType": "deployment",
        "mode": "ollama",
        "ollamaModel": "phi4-mini:latest",
    })

    xml = raw.decode()
    assert status == 200
    assert calls == [("Retail Analytics", "phi4-mini:latest", True, True)]
    assert "Edge VPC" in xml
    assert "Transit Gateway" in xml


def test_drawio_xml_applies_ollama_render_plan_to_executive_tab(server, monkeypatch):
    from network_picasso import server as server_module

    calls = []

    def fake_plan_render(architecture, model, base_url, deployment_guide="", style_guide=""):
        calls.append((architecture["project"]["name"], model, bool(deployment_guide), bool(style_guide)))
        return {
            "pattern": "hub-and-spoke",
            "pattern_reason": "Retail workload needs separated edge and workload VPCs.",
            "topology_variant": "",
            "has_on_prem": False,
            "has_tgw": True,
            "has_powervs": False,
            "has_dr": False,
            "az_count": 3,
            "vpcs": [
                {"name": "Edge VPC", "purpose": "Internet ingress", "tiers": ["Public", "Management"]},
                {"name": "Workload VPC", "purpose": "Private application and data tiers", "tiers": ["Private", "Data"]},
            ],
            "shared_services": ["Activity Tracker", "VPC Flow Logs"],
            "connectivity_label": "",
        }

    monkeypatch.setattr(server_module._ollama, "plan_render", fake_plan_render)

    status, raw, _headers = _post_raw(server, "/api/drawio-xml", {
        "architecture": {
            "project": {"name": "Retail Analytics"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Workload VPC"}],
                "compute": [{"name": "VPC VSI workload tier"}],
            },
        },
        "diagramType": "executive",
        "mode": "ollama",
        "ollamaModel": "phi4-mini:latest",
    })

    xml = raw.decode()
    assert status == 200
    assert calls == [("Retail Analytics", "phi4-mini:latest", True, True)]
    assert "Edge VPC" in xml
    assert "Workload VPC" in xml
    assert "medical imaging" not in xml


def test_mcp_all_pages_applies_ollama_render_plan(server, monkeypatch):
    from network_picasso import server as server_module

    def fake_plan_render(*_args, **_kwargs):
        return {
            "pattern": "hub-and-spoke",
            "pattern_reason": "Separated edge/workload VPCs.",
            "has_on_prem": False,
            "has_tgw": True,
            "has_powervs": False,
            "has_dr": False,
            "az_count": 3,
            "vpcs": [
                {"name": "Edge VPC", "purpose": "Internet ingress", "tiers": ["Public"]},
                {"name": "Workload VPC", "purpose": "Private application tier", "tiers": ["Private", "Data"]},
            ],
            "shared_services": ["Activity Tracker"],
            "connectivity_label": "",
        }

    captured = {}

    def fake_open_multipage(xml, **kwargs):
        captured["xml"] = xml
        captured["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr(server_module._ollama, "plan_render", fake_plan_render)
    monkeypatch.setattr(server_module._mcp, "is_running", lambda: True)
    monkeypatch.setattr(server_module._mcp, "open_multipage_diagram_in_editor", fake_open_multipage)
    monkeypatch.setattr(server_module._mcp, "open_all_pages", lambda _diagrams: pytest.fail("generated pages should open atomically as a multipage Draw.io document"))

    status, body = _post(server, "/api/drawio-mcp-all-pages", {
        "architecture": {
            "project": {"name": "Retail Analytics"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "vpcs": [{"name": "Workload VPC"}],
                "compute": [{"name": "VPC VSI workload tier"}],
            },
        },
        "mode": "ollama",
        "ollamaModel": "phi4-mini:latest",
    })

    assert status == 200
    assert body["pages"] == 5
    assert "Edge VPC" in captured["xml"]
    assert "Workload VPC" in captured["xml"]


def test_mcp_all_pages_prefers_saved_project_drawio(server, tmp_path, monkeypatch):
    from network_picasso import server as server_module

    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "acme", "project": "q4"})
        proj_path = root / "acme" / "q4"
        arch_path = proj_path / "architecture.json"
        architecture = {
            "project": {"name": "Acme Q4"},
            "ibm_cloud": {"regions": [{"name": "us-south"}]},
        }
        arch_path.write_text(json.dumps(architecture))
        saved_xml = "<mxfile><diagram name=\"Deployment\"><mxGraphModel><root><mxCell id=\"saved\" value=\"Saved MCP edits\" /></root></mxGraphModel></diagram></mxfile>"
        save_project_live_drawio(proj_path, saved_xml, source="test", architecture=architecture)

        captured = {}
        monkeypatch.setattr(server_module._mcp, "is_running", lambda: True)
        monkeypatch.setattr(server_module._mcp, "open_multipage_diagram_in_editor", lambda xml, **kwargs: captured.update({"xml": xml, "kwargs": kwargs}) or {"ok": True})
        monkeypatch.setattr(server_module._mcp, "open_all_pages", lambda _diagrams: pytest.fail("saved Draw.io should be opened instead of generated pages"))

        status, body = _post(server, "/api/drawio-mcp-all-pages", {
            "architecturePath": str(arch_path),
        })

        assert status == 200
        assert body["source"] == "saved"
        assert "Saved MCP edits" in captured["xml"]
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_mcp_all_pages_ignores_stale_saved_project_drawio(server, tmp_path, monkeypatch):
    from network_picasso import server as server_module

    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _post(server, "/api/projects", {"customer": "tmobile", "project": "dlm"})
        proj_path = root / "tmobile" / "dlm"
        arch_path = proj_path / "architecture.json"
        old_architecture = {
            "project": {"name": "UPS"},
            "ibm_cloud": {"compute": [{"name": "ROVS POC"}]},
        }
        new_architecture = {
            "project": {"name": "T-Mobile DLM"},
            "ibm_cloud": {
                "regions": [{"name": "us-south"}],
                "compute": [{"name": "Red Hat OpenShift on IBM Cloud"}],
            },
        }
        arch_path.write_text(json.dumps(new_architecture))
        saved_xml = "<mxfile><diagram name=\"Deployment\"><mxGraphModel><root><mxCell id=\"saved\" value=\"UPS ROVS old design\" /></root></mxGraphModel></diagram></mxfile>"
        save_project_live_drawio(proj_path, saved_xml, source="test", architecture=old_architecture)

        captured = {}
        monkeypatch.setattr(server_module._mcp, "is_running", lambda: True)
        monkeypatch.setattr(server_module._mcp, "open_multipage_diagram_in_editor", lambda xml, **kwargs: captured.update({"xml": xml, "kwargs": kwargs}) or {"ok": True})
        monkeypatch.setattr(server_module._mcp, "open_all_pages", lambda _diagrams: pytest.fail("all pages should open atomically"))

        status, body = _post(server, "/api/drawio-mcp-all-pages", {
            "architecturePath": str(arch_path),
        })

        assert status == 200
        assert body["source"] == "generated"
        assert "T-Mobile DLM" in captured["xml"]
        assert "UPS ROVS old design" not in captured["xml"]
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


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


def test_requirements_endpoint_can_replace_stale_architecture(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Old Healthcare", "environment": "Production"},
        "ibm_cloud": {
            "compute": [{"name": "Medical imaging processing VSIs"}],
            "data": [{"name": "Cloud Object Storage for medical imaging archive"}],
            "security": [{"name": "Security and Compliance Center"}],
        },
        "questions": {"answered": [], "open": []},
    }))

    status, body = _post(server, "/api/requirements", {
        "architecturePath": str(arch_path),
        "requirements": "Retail analytics platform in us-south using VSI on VPC, Cloud Object Storage archive, Activity Tracker, and no PowerVS workload.",
        "replaceArchitecture": True,
        "projectName": "Retail Analytics",
    })

    assert status == 200
    architecture = body["architecture"]
    assert architecture["project"]["name"] == "Retail Analytics"
    component_names = json.dumps([
        item.get("name", "")
        for values in architecture["ibm_cloud"].values()
        if isinstance(values, list)
        for item in values
        if isinstance(item, dict)
    ]).lower()
    names = json.dumps(architecture["ibm_cloud"]).lower()
    assert "cloud object storage archive" in names
    assert "powervs" not in component_names
    assert "medical imaging processing vsis" not in component_names
    assert "cloud object storage for medical imaging archive" not in component_names


def test_requirements_endpoint_uses_generic_cos_label_for_non_healthcare(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Generic Object Storage", "environment": "Production"},
        "ibm_cloud": {},
        "questions": {"answered": [], "open": []},
    }))

    status, body = _post(server, "/api/requirements", {
        "architecturePath": str(arch_path),
        "requirements": "Object storage archive for application logs in us-south with Activity Tracker.",
        "replaceArchitecture": True,
    })

    assert status == 200
    names = json.dumps(body["architecture"]["ibm_cloud"]).lower()
    assert "cloud object storage archive" in names
    assert "medical imaging" not in names


def test_answer_missing_params(server):
    status, body = _post(server, "/api/answer", {"area": "Subnet design"})
    assert status == 400


def test_diagram_quality_persists_last_review(server, tmp_path):
    arch_path = tmp_path / "architecture.json"
    arch_path.write_text(json.dumps({
        "project": {"name": "Quality Save"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "vpcs": [{"name": "Production VPC"}],
            "regions": [{"name": "us-south"}],
            "compute": [{"name": "VSI workload"}],
        },
    }))
    status, body = _post(server, "/api/diagram-quality", {
        "architecturePath": str(arch_path),
        "diagramType": "deployment",
    })
    assert status == 200
    saved = json.loads(arch_path.read_text())
    assert saved["quality"]["lastReview"]["score"] == body["score"]
    assert saved["quality"]["lastReview"]["diagramType"] == "deployment"


def test_restore_project_requires_postgres(server, tmp_path, monkeypatch):
    monkeypatch.delenv("NETWORK_PICASSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings_path = REPO_ROOT / "inputs" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text() if settings_path.exists() else None
    try:
        root = tmp_path / "projects"
        settings_path.write_text(json.dumps({"projectsRoot": str(root)}))
        _, created = _post(server, "/api/projects", {"customer": "Acme Bank", "project": "Q1"})
        status, body = _post(server, "/api/projects/restore", {
            "path": created["path"],
            "snapshotId": 1,
        })
        assert status == 503
        assert "Postgres" in body["error"]
    finally:
        if original is not None:
            settings_path.write_text(original)
        elif settings_path.exists():
            settings_path.unlink()


def test_restore_preview_payload_summarizes_architecture_changes():
    current = {
        "project": {"name": "Current", "environment": "dev"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "Current VPC"}],
            "compute": [{"name": "Current VSI"}],
            "security": [{"name": "Secrets Manager"}],
        },
        "questions": {"answered": [{"question": "RPO?", "answer": "4h"}], "open": []},
    }
    restore = {
        "project": {"name": "Target", "environment": "prod"},
        "render_plan": {"pattern_name": "PowerVS with VPC landing zone"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}, {"name": "us-east"}],
            "vpcs": [{"name": "Workload VPC"}],
            "compute": [{"name": "PowerVS servers"}],
            "security": [{"name": "Key Protect or HPCS"}],
        },
        "questions": {
            "answered": [{"question": "RPO?", "answer": "1h"}, {"question": "DR?", "answer": "WDC"}],
            "open": ["Confirm Direct Link diversity"],
        },
        "quality": {"lastReview": {"score": 88, "status": "Ready with minor refinements"}},
    }
    preview = restore_preview_payload(current, restore)
    labels = {change["label"] for change in preview["changes"]}
    assert "Project name" in labels
    assert "IBM pattern" in labels
    assert "Regions" in labels
    assert "Latest quality score" in labels
    assert "PowerVS servers" in preview["addedServices"]
    assert "Current VSI" in preview["removedServices"]
