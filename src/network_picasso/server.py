from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .drawio import (
    render_all_diagrams,
    render_drawio,
    render_ibm_location_snippet,
    render_ibm_node_snippet,
    render_multipage_drawio,
    STENCIL_MAP,
    DEPLOYMENT_GUIDE,
    STYLE_GUIDE,
)
from .intake import (
    backfill_answer_into_model,
    build_architecture_from_inputs,
    classify_file,
    SUPPORTED_EXTENSIONS,
)
from . import mcp_bridge as _mcp
from . import ollama as _ollama
from .patterns import best_pattern, match_patterns
from .projects import (
    create_project,
    delete_folder,
    delete_project,
    duplicate_project,
    list_folders,
    list_projects,
    list_projects_in_folder,
    move_project,
    project_architecture_path,
    project_uploads_path,
    rename_folder,
    rename_project,
    resolve_projects_root,
    safe_slug,
)
from .questions import find_design_gaps


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = "examples/sample-inputs"
DEFAULT_ARCHITECTURE_PATH = "examples/sample/architecture.json"
UPLOAD_INPUT_PATH = "inputs/uploads/current"
UPLOAD_ARCHITECTURE_PATH = "inputs/uploads/current/architecture.json"
SETTINGS_PATH = "inputs/settings.json"
OLLAMA_BASE_URL = "http://localhost:11434"

_SETTINGS_DEFAULTS: dict = {
    "mode": "rules",
    "ollamaModel": "phi4-mini:latest",
    "confidenceThreshold": 0.8,
    "projectsRoot": "inputs/projects",
}


def repo_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def relative_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


class NetworkPicassoHandler(BaseHTTPRequestHandler):
    server_version = "NetworkPicasso/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "repoRoot": str(REPO_ROOT)})
            return
        if parsed.path == "/api/example":
            architecture_path = REPO_ROOT / DEFAULT_ARCHITECTURE_PATH
            architecture = read_json_file(architecture_path)
            answered = architecture.get("questions", {}).get("answered", [])
            self.send_json(
                {
                    "architecture": architecture,
                    "questions": find_design_gaps(architecture),
                    "architecturePath": relative_to_repo(architecture_path),
                    "answeredQuestions": answered,
                }
            )
            return
        if parsed.path == "/api/ollama/models":
            models = _ollama.list_models(OLLAMA_BASE_URL)
            self.send_json({"models": models})
            return
        if parsed.path == "/api/settings":
            self.send_json(load_settings())
            return
        if parsed.path == "/api/drawio-xml":
            qs = parse_qs(parsed.query or "")
            architecture_path = repo_path(
                (qs.get("architecturePath") or [DEFAULT_ARCHITECTURE_PATH])[0]
            )
            diagram_type = (qs.get("diagramType") or ["deployment"])[0]
            architecture = read_json_file(architecture_path)
            self.send_xml(render_drawio(architecture, diagram_type=diagram_type))
            return
        if parsed.path == "/api/drawio-mcp/health":
            running = _mcp.is_running()
            self.send_json({"running": running, "editorUrl": _mcp.MCP_BASE_URL if running else None})
            return
        if parsed.path == "/api/drawio-mcp/stencils":
            self.send_json({"stencils": STENCIL_MAP})
            return
        if parsed.path == "/api/projects":
            settings = load_settings()
            root = resolve_projects_root(settings)
            self.send_json({"projects": list_projects(root)})
            return
        if parsed.path == "/api/folders":
            settings = load_settings()
            root = resolve_projects_root(settings)
            qs = parse_qs(parsed.query or "")
            folder_name = (qs.get("folder") or [None])[0]
            if folder_name:
                folder_path = root / folder_name
                self.send_json({"projects": list_projects_in_folder(folder_path)})
            else:
                self.send_json({"folders": list_folders(root)})
            return
        if parsed.path == "/api/project-export":
            qs = parse_qs(parsed.query or "")
            project_path = repo_path((qs.get("path") or [""])[0])
            arch_path = project_architecture_path(project_path)
            if not arch_path.exists():
                self.send_error_json(404, "No architecture.json found for this project")
                return
            body = arch_path.read_bytes()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="architecture.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error_json(404, "Route not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/upload-intake":
                self.handle_upload_intake()
                return
            if parsed.path == "/api/project-import":
                self.handle_project_import()
                return

            payload = self.read_json()
            if parsed.path == "/api/intake":
                self.handle_intake(payload)
            elif parsed.path == "/api/pattern-match":
                self.handle_pattern_match(payload)
            elif parsed.path == "/api/set-pattern":
                self.handle_set_pattern(payload)
            elif parsed.path == "/api/questions":
                self.handle_questions(payload)
            elif parsed.path == "/api/generate-drawio":
                self.handle_generate_drawio(payload)
            elif parsed.path == "/api/drawio-xml":
                self.handle_drawio_xml(payload)
            elif parsed.path == "/api/answer":
                self.handle_answer(payload)
            elif parsed.path == "/api/requirements":
                self.handle_requirements(payload)
            elif parsed.path == "/api/confirm-components":
                self.handle_confirm_components(payload)
            elif parsed.path == "/api/settings":
                self.handle_save_settings(payload)
            elif parsed.path == "/api/projects":
                self.handle_create_project(payload)
            elif parsed.path == "/api/folders/rename":
                self.handle_rename_folder(payload)
            elif parsed.path == "/api/folders/delete":
                self.handle_delete_folder(payload)
            elif parsed.path == "/api/projects/rename":
                self.handle_rename_project(payload)
            elif parsed.path == "/api/projects/delete":
                self.handle_delete_project(payload)
            elif parsed.path == "/api/projects/duplicate":
                self.handle_duplicate_project(payload)
            elif parsed.path == "/api/projects/move":
                self.handle_move_project(payload)
            elif parsed.path == "/api/drawio-snippet":
                self.handle_drawio_snippet(payload)
            elif parsed.path == "/api/drawio-mcp-open":
                self.handle_drawio_mcp_open(payload)
            elif parsed.path == "/api/drawio-mcp-all-pages":
                self.handle_drawio_mcp_all_pages(payload)
            elif parsed.path == "/api/drawio-multipage":
                self.handle_drawio_multipage(payload)
            else:
                self.send_error_json(404, "Route not found")
        except Exception as exc:  # Keep the local UI useful during early iteration.
            self.send_error_json(500, str(exc))

    def handle_intake(self, payload: dict) -> None:
        # Support project-routed paths
        settings = load_settings()
        customer = payload.get("customer")
        project = payload.get("project")
        if customer:
            proj_root = resolve_projects_root(settings)
            proj_path = create_project(proj_root, customer, project or None)
            input_path = project_uploads_path(proj_path)
            output_path = project_architecture_path(proj_path)
        else:
            input_path = repo_path(payload.get("inputPath") or DEFAULT_INPUT_PATH)
            output_path = repo_path(payload.get("outputPath") or DEFAULT_ARCHITECTURE_PATH)

        project_name = payload.get("projectName") or None
        mode = str(payload.get("mode") or "rules")
        ollama_model = str(payload.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"])

        architecture, gaps, pending = run_intake(
            input_path, output_path, project_name=project_name,
            mode=mode, ollama_model=ollama_model,
        )

        answered = architecture.get("questions", {}).get("answered", [])
        self.send_json(
            {
                "architecture": architecture,
                "questions": gaps,
                "outputPath": relative_to_repo(output_path),
                "answeredQuestions": answered,
                "pendingComponents": pending,
            }
        )

    def handle_upload_intake(self) -> None:
        fields, files = self.read_multipart()
        if not files:
            self.send_error_json(400, "Upload at least one BOM, pricing, spreadsheet, CSV, JSON, Markdown, or text file.")
            return

        # Route to project folder when customer/project provided
        settings = load_settings()
        customer = fields.get("customer")
        project = fields.get("project")
        if customer:
            proj_root = resolve_projects_root(settings)
            proj_path = create_project(proj_root, customer, project or None)
            upload_dir = project_uploads_path(proj_path)
            output_path = project_architecture_path(proj_path)
        else:
            upload_dir = repo_path(UPLOAD_INPUT_PATH)
            output_path = repo_path(UPLOAD_ARCHITECTURE_PATH)

        # Clear stale files from a previous intake run before writing new
        # uploads.  This prevents old demo/sample data from polluting the
        # model when the user starts a fresh upload session.
        _clear_upload_dir(upload_dir)

        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        file_roles: list[dict] = []
        for uploaded in files:
            filename = safe_filename(uploaded["filename"])
            target = upload_dir / filename
            target.write_bytes(uploaded["content"])
            saved_files.append(relative_to_repo(target))
            role = classify_file(target)
            file_roles.append({"file": filename, "role": role})

        project_name = fields.get("projectName") or "Customer Architecture"
        mode = fields.get("mode") or "rules"
        ollama_model = fields.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"]
        architecture, gaps, pending = run_intake(
            upload_dir, output_path, project_name=project_name,
            mode=mode, ollama_model=ollama_model,
        )

        answered = architecture.get("questions", {}).get("answered", [])
        self.send_json(
            {
                "architecture": architecture,
                "questions": gaps,
                "inputPath": relative_to_repo(upload_dir),
                "outputPath": relative_to_repo(output_path),
                "files": saved_files,
                "fileRoles": file_roles,
                "answeredQuestions": answered,
                "pendingComponents": pending,
            }
        )

    def handle_create_project(self, payload: dict) -> None:
        customer = str(payload.get("customer") or "").strip()
        project = str(payload.get("project") or "").strip() or None
        if not customer:
            self.send_error_json(400, "customer is required")
            return
        settings = load_settings()
        proj_root = resolve_projects_root(settings)
        proj_path = create_project(proj_root, customer, project)
        self.send_json({
            "path": relative_to_repo(proj_path),
            "customer": safe_slug(customer),
            "project": safe_slug(project) if project else "",
        })

    def handle_rename_folder(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        new_name = str(payload.get("name") or "").strip()
        if not path_str or not new_name:
            self.send_error_json(400, "path and name are required")
            return
        folder_path = repo_path(path_str)
        try:
            new_path = rename_folder(folder_path, new_name)
        except ValueError as exc:
            self.send_error_json(409, str(exc))
            return
        self.send_json({"path": relative_to_repo(new_path), "name": new_path.name})

    def handle_delete_folder(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        if not path_str:
            self.send_error_json(400, "path is required")
            return
        folder_path = repo_path(path_str)
        delete_folder(folder_path)
        self.send_json({"ok": True})

    def handle_rename_project(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        new_name = str(payload.get("name") or "").strip()
        if not path_str or not new_name:
            self.send_error_json(400, "path and name are required")
            return
        project_path = repo_path(path_str)
        try:
            new_path = rename_project(project_path, new_name)
        except ValueError as exc:
            self.send_error_json(409, str(exc))
            return
        self.send_json({"path": relative_to_repo(new_path), "name": new_path.name})

    def handle_delete_project(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        if not path_str:
            self.send_error_json(400, "path is required")
            return
        project_path = repo_path(path_str)
        delete_project(project_path)
        self.send_json({"ok": True})

    def handle_duplicate_project(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        new_name = str(payload.get("name") or "").strip()
        if not path_str or not new_name:
            self.send_error_json(400, "path and name are required")
            return
        project_path = repo_path(path_str)
        try:
            new_path = duplicate_project(project_path, new_name)
        except ValueError as exc:
            self.send_error_json(409, str(exc))
            return
        settings = load_settings()
        root = resolve_projects_root(settings)
        self.send_json({
            "path": relative_to_repo(new_path),
            "customer": new_path.parent.name,
            "project": new_path.name,
            "hasArchitecture": (new_path / "architecture.json").exists(),
            "isLegacy": False,
        })

    def handle_move_project(self, payload: dict) -> None:
        path_str = str(payload.get("path") or "").strip()
        dest_str = str(payload.get("destFolder") or "").strip()
        if not path_str or not dest_str:
            self.send_error_json(400, "path and destFolder are required")
            return
        project_path = repo_path(path_str)
        dest_folder = repo_path(dest_str)
        try:
            new_path = move_project(project_path, dest_folder)
        except ValueError as exc:
            self.send_error_json(409, str(exc))
            return
        self.send_json({
            "path": relative_to_repo(new_path),
            "customer": new_path.parent.name,
            "project": new_path.name,
            "hasArchitecture": (new_path / "architecture.json").exists(),
            "isLegacy": False,
        })

    def handle_project_import(self) -> None:
        fields, files = self.read_multipart()
        project_path_str = fields.get("path")
        if not project_path_str:
            self.send_error_json(400, "path field is required")
            return
        arch_files = [f for f in files if f.get("filename", "").endswith(".json")]
        if not arch_files:
            self.send_error_json(400, "Upload a .json architecture file")
            return
        proj_path = repo_path(project_path_str)
        arch_path = project_architecture_path(proj_path)
        arch_path.parent.mkdir(parents=True, exist_ok=True)
        arch_path.write_bytes(arch_files[0]["content"])
        self.send_json({"ok": True, "outputPath": relative_to_repo(arch_path)})

    def handle_answer(self, payload: dict) -> None:
        architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
        area = str(payload.get("area") or "")
        question = str(payload.get("question") or "")
        answer = str(payload.get("answer") or "").strip()
        source = str(payload.get("source") or "architect")

        if not area or not question or not answer:
            self.send_error_json(400, "area, question, and answer are required")
            return

        architecture = read_json_file(architecture_path)
        questions_block = architecture.setdefault("questions", {"answered": [], "open": []})

        # Append structured answered entry.
        entry = {
            "area": area,
            "question": question,
            "answer": answer,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        questions_block.setdefault("answered", []).append(entry)

        # Remove from open list (string comparison against question text).
        questions_block["open"] = [q for q in questions_block.get("open", []) if q != question]

        # Back-fill answer text into the ibm_cloud model.
        backfill_answer_into_model(architecture, area, answer)

        atomic_write_json(architecture_path, architecture)
        self.send_json({"ok": True, "entry": entry})

    def handle_requirements(self, payload: dict) -> None:
        """Persist customer requirements text into the architecture JSON."""
        architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
        requirements = str(payload.get("requirements") or "").strip()
        source = str(payload.get("source") or "text")  # "text" or "file"
        filename = str(payload.get("filename") or "")

        if not requirements:
            self.send_error_json(400, "requirements text is required")
            return

        architecture = read_json_file(architecture_path)
        reqs_block = architecture.setdefault("requirements", [])
        entry = {
            "text": requirements,
            "source": source,
            "filename": filename,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        reqs_block.append(entry)
        atomic_write_json(architecture_path, architecture)
        self.send_json({"ok": True, "entry": entry})

    def handle_confirm_components(self, payload: dict) -> None:
        architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
        confirmed: list[dict] = payload.get("confirmed") or []
        # discarded items are simply not written — no action needed on server.

        architecture = read_json_file(architecture_path)
        ibm_cloud = architecture.setdefault("ibm_cloud", {})

        for component in confirmed:
            key = str(component.get("key") or "")
            if not key:
                continue
            entry = {
                "name": str(component.get("name") or ""),
                "type": key,
                "purpose": str(component.get("purpose") or ""),
                "notes": str(component.get("notes") or ""),
                "source": "confirm-components",
            }
            ibm_cloud.setdefault(key, []).append(entry)

        atomic_write_json(architecture_path, architecture)
        self.send_json({"ok": True, "confirmed": len(confirmed)})

    def handle_questions(self, payload: dict) -> None:
        architecture = payload.get("architecture")
        if not architecture:
            architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(architecture_path)
        gaps = find_design_gaps(architecture)
        # Augment with LLM gaps when mode is ollama (from payload or saved settings).
        settings = load_settings()
        mode = str(payload.get("mode") or settings.get("mode") or "rules")
        if mode == "ollama":
            model = str(payload.get("ollamaModel") or settings.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"])
            llm_gaps = _ollama.generate_questions(architecture, model, OLLAMA_BASE_URL)
            existing_texts = {g["question"] for g in gaps}
            for g in llm_gaps:
                if g.get("question") and g["question"] not in existing_texts:
                    gaps.append(g)
                    existing_texts.add(g["question"])
        self.send_json({"questions": gaps})

    def handle_pattern_match(self, payload: dict) -> None:
        """Score IBM Think Architecture patterns against the provided architecture.

        Accepts::

            {
              "architecture":     dict (optional if architecturePath provided),
              "architecturePath": str  (optional),
              "requirements":     str  (optional extra free-text requirements),
              "topN":             int  (optional, default all patterns)
            }

        Returns::

            { "patterns": [ {id, name, description, url, score, matched, missing}, ... ] }
        """
        architecture = payload.get("architecture")
        if not architecture:
            arch_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(arch_path)
        requirements = str(payload.get("requirements") or "")
        top_n = payload.get("topN")
        if top_n is not None:
            top_n = int(top_n)
        patterns = match_patterns(architecture, requirements_text=requirements, top_n=top_n)
        # Also include the best pattern as a convenience field
        best = patterns[0] if patterns else None
        self.send_json({"patterns": patterns, "best": best})

    def handle_set_pattern(self, payload: dict) -> None:
        """Persist the architect's chosen IBM Think Architecture pattern.

        Accepts::

            {
              "architecturePath": str,
              "patternId":        str  (e.g. "mzr", "hub-and-spoke"),
              "patternName":      str,
              "score":            float (optional)
            }

        Writes to architecture["render_plan"]["pattern"] and
        architecture["render_plan"]["pattern_source"] = "architect".
        """
        architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
        pattern_id   = str(payload.get("patternId") or "").strip()
        pattern_name = str(payload.get("patternName") or "").strip()
        score        = payload.get("score")

        if not pattern_id:
            self.send_error_json(400, "patternId is required")
            return

        architecture = read_json_file(architecture_path)
        render_plan = architecture.setdefault("render_plan", {})
        render_plan["pattern"]        = pattern_id
        render_plan["pattern_name"]   = pattern_name
        render_plan["pattern_source"] = "architect"
        if score is not None:
            render_plan["pattern_score"] = float(score)

        atomic_write_json(architecture_path, architecture)
        self.send_json({"ok": True, "patternId": pattern_id, "renderPlan": render_plan})

    def handle_save_settings(self, payload: dict) -> None:
        settings = load_settings()
        for key in ("mode", "ollamaModel", "confidenceThreshold", "projectsRoot"):
            if key in payload:
                settings[key] = payload[key]
        settings_path = repo_path(SETTINGS_PATH)
        atomic_write_json(settings_path, settings)
        self.send_json({"ok": True, "settings": settings})

    def handle_drawio_snippet(self, payload: dict) -> None:
        """Return IBM-styled XML for a single node or location container.

        Accepts::

            {
              "kind":       "node" | "location",
              "name":       str,
              "shape":      str,                  # IBM stencil name
              "strokeColor": str,                 # location only
              "x": int, "y": int,
              "width": int, "height": int,        # location only
              "size": int,                        # node only (default 48)
              "parentId": str                     # Draw.io parent cell ID
            }
        """
        kind   = str(payload.get("kind") or "node")
        name   = str(payload.get("name") or "Component")
        shape  = str(payload.get("shape") or "")
        parent = str(payload.get("parentId") or "1")
        x      = int(payload.get("x") or 100)
        y      = int(payload.get("y") or 100)

        if not shape:
            # Try to infer from name
            from .drawio import _stencil_shape
            shape = _stencil_shape(name) or "ibm-cloud--virtual-server-vpc"

        if kind == "location":
            stroke = str(payload.get("strokeColor") or "#1192E8")
            w      = int(payload.get("width")  or 300)
            h      = int(payload.get("height") or 200)
            xml    = render_ibm_location_snippet(
                name, shape, stroke,
                x=x, y=y, w=w, h=h, parent_id=parent,
            )
        else:
            d   = int(payload.get("size") or 48)
            xml = render_ibm_node_snippet(name, shape, x=x, y=y, d=d, parent_id=parent)

        self.send_xml(xml)

    def handle_drawio_mcp_open(self, payload: dict) -> None:
        """Generate diagram XML and push it to the MCP editor (replace mode).

        Accepts::

            { "architecturePath": str, "diagramType": str }

        Returns::

            { "ok": true, "editorUrl": "http://127.0.0.1:4000" }
        """
        architecture = payload.get("architecture")
        if not architecture:
            arch_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(arch_path)
        diagram_type = str(payload.get("diagramType") or "deployment")
        xml = render_drawio(architecture, diagram_type=diagram_type)

        if not _mcp.is_running():
            self.send_error_json(503, "drawio-mcp-server is not running at localhost:4000. Start it via the MCP panel in Bob.")
            return
        try:
            _mcp.open_diagram_in_editor(xml, filename=f"network-picasso-{diagram_type}.drawio")
        except (ConnectionError, RuntimeError) as exc:
            self.send_error_json(503, str(exc))
            return
        self.send_json({"ok": True, "editorUrl": _mcp.MCP_BASE_URL})

    def handle_drawio_mcp_all_pages(self, payload: dict) -> None:
        """Generate all three diagram types and push them as pages to the MCP editor.

        Accepts::

            { "architecturePath": str }

        Returns::

            { "ok": true, "editorUrl": "http://127.0.0.1:4000", "pages": [...] }
        """
        architecture = payload.get("architecture")
        if not architecture:
            arch_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(arch_path)

        if not _mcp.is_running():
            self.send_error_json(503, "drawio-mcp-server is not running at localhost:4000. Start it via the MCP panel in Bob.")
            return
        try:
            diagrams = render_all_diagrams(architecture)
            results  = _mcp.open_all_pages(diagrams)
        except (ConnectionError, RuntimeError) as exc:
            self.send_error_json(503, str(exc))
            return
        self.send_json({"ok": True, "editorUrl": _mcp.MCP_BASE_URL, "pages": len(results)})

    def handle_drawio_multipage(self, payload: dict) -> None:
        """Generate a multi-page .drawio file (no MCP required) and save to disk.

        Accepts::

            { "architecturePath": str, "outputPath": str (optional) }

        Returns::

            { "outputPath": str }
        """
        architecture = payload.get("architecture")
        if not architecture:
            arch_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(arch_path)
        output_path = repo_path(
            payload.get("outputPath") or "outputs/network-picasso-all.drawio"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        xml = render_multipage_drawio(architecture)
        output_path.write_text(xml, encoding="utf-8")
        self.send_json({"outputPath": relative_to_repo(output_path)})

    def handle_drawio_xml(self, payload: dict) -> None:
        architecture = payload.get("architecture")
        if not architecture:
            architecture_path_str = payload.get("architecturePath")
            if not architecture_path_str:
                self.send_error_json(400, "architecture or architecturePath is required")
                return
            architecture = read_json_file(repo_path(architecture_path_str))
        diagram_type = str(payload.get("diagramType") or "deployment")
        self.send_xml(render_drawio(architecture, diagram_type=diagram_type))

    def handle_generate_drawio(self, payload: dict) -> None:
        architecture = payload.get("architecture")
        if not architecture:
            architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(architecture_path)
        diagram_type = payload.get("diagramType") or "deployment"
        output_path = repo_path(payload.get("outputPath") or f"outputs/network-picasso-{diagram_type}.drawio")

        # Ollama mode: ask the LLM to choose the reference pattern and enrich
        # the architecture with a render plan before generating the diagram.
        settings = load_settings()
        mode = str(payload.get("mode") or settings.get("mode") or "rules")
        if mode == "ollama" and diagram_type == "deployment":
            model = str(payload.get("ollamaModel") or settings.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"])
            render_plan = _ollama.plan_render(
                architecture, model, OLLAMA_BASE_URL,
                deployment_guide=DEPLOYMENT_GUIDE,
                style_guide=STYLE_GUIDE,
            )
            if render_plan:
                # Persist LLM pattern decision into architecture for logging / later use
                architecture.setdefault("render_plan", {}).update(render_plan)
                print(f"[generate] LLM render plan: {render_plan.get('pattern')} — {render_plan.get('pattern_reason', '')}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_drawio(architecture, diagram_type=diagram_type), encoding="utf-8")
        self.send_json({
            "outputPath": relative_to_repo(output_path),
            "renderPlan": architecture.get("render_plan"),
        })

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def read_multipart(self) -> tuple[dict[str, str], list[dict[str, bytes | str]]]:
        content_type = self.headers.get("Content-Type", "")
        match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
        if not match:
            raise ValueError("Missing multipart boundary")
        boundary = match.group("boundary").strip('"').encode("utf-8")
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length)
        fields: dict[str, str] = {}
        files: list[dict[str, bytes | str]] = []

        for part in body.split(b"--" + boundary):
            part = part.strip()
            if not part or part == b"--":
                continue
            if part.endswith(b"--"):
                part = part[:-2].strip()
            header_blob, _, content = part.partition(b"\r\n\r\n")
            if not header_blob:
                continue
            headers = header_blob.decode("utf-8", errors="replace")
            disposition = next(
                (line for line in headers.split("\r\n") if line.lower().startswith("content-disposition:")),
                "",
            )
            name = multipart_attribute(disposition, "name")
            filename = multipart_attribute(disposition, "filename")
            content = content.rstrip(b"\r\n")
            if filename:
                files.append({"name": name, "filename": filename, "content": content})
            elif name:
                fields[name] = content.decode("utf-8", errors="replace")
        return fields, files

    def send_xml(self, xml: str, *, status: int = 200) -> None:
        body = xml.encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, *, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status=status)

    def send_cors_headers(self) -> None:
        allowed = {"http://localhost:5173", "http://127.0.0.1:5173"}
        origin = self.headers.get("Origin", "")
        if origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path* atomically (tmp file + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def load_settings() -> dict:
    """Return current settings, falling back to defaults for any missing key."""
    settings = dict(_SETTINGS_DEFAULTS)
    settings_path = repo_path(SETTINGS_PATH)
    if settings_path.exists():
        try:
            on_disk = json.loads(settings_path.read_text(encoding="utf-8"))
            settings.update(on_disk)
        except Exception:
            pass
    return settings


def run_intake(
    input_path: Path,
    output_path: Path,
    *,
    project_name: str | None,
    mode: str = "rules",
    ollama_model: str | None = None,
) -> tuple[dict, list[dict], list[dict]]:
    """
    Run the intake pipeline.

    Returns (architecture, gaps, pending_components).
    pending_components is a list of low-confidence LLM extractions (empty in rules-only mode).
    """
    settings = load_settings()
    threshold: float = float(settings.get("confidenceThreshold", 0.8))

    architecture = build_architecture_from_inputs(input_path, project_name=project_name)
    normalize_sources(architecture)

    pending_components: list[dict] = []

    if mode == "ollama":
        model = ollama_model or settings.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"]
        # Concatenate all uploaded text files for LLM extraction.
        text_parts: list[str] = []
        iter_files = list(input_path.iterdir()) if input_path.is_dir() else [input_path]
        for p in iter_files:
            if p.suffix.lower() in {".txt", ".md", ".csv", ".tsv", ".json"}:
                try:
                    text_parts.append(p.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
        combined_text = "\n\n".join(text_parts)
        if combined_text.strip():
            extracted = _ollama.extract_components(combined_text, model, OLLAMA_BASE_URL)
            ibm_cloud = architecture.setdefault("ibm_cloud", {})
            for item in extracted:
                confidence = float(item.get("confidence", 0.0))
                key = str(item.get("suggested_key") or "")
                if not key:
                    continue
                component = {
                    "name": str(item.get("name") or ""),
                    "type": key,
                    "purpose": str(item.get("purpose") or ""),
                    "notes": str(item.get("notes") or ""),
                    "source": "llm",
                }
                if confidence >= threshold:
                    ibm_cloud.setdefault(key, []).append(component)
                else:
                    pending_components.append({
                        "id": f"llm-{len(pending_components)}",
                        "name": component["name"],
                        "suggestedKey": key,
                        "confidence": confidence,
                        "notes": component["notes"],
                    })

    # Preserve answered entries from any pre-existing architecture file so
    # re-running intake does not lose architect answers.
    if output_path.exists():
        try:
            existing = read_json_file(output_path)
            prior_answered = existing.get("questions", {}).get("answered", [])
            if prior_answered:
                architecture["questions"]["answered"] = prior_answered
        except Exception:
            pass  # Corrupt or missing file — proceed with empty answered list.

    gaps = find_design_gaps(architecture)

    # In Ollama mode, append LLM-generated gap questions (dedup by question text).
    if mode == "ollama":
        model = ollama_model or settings.get("ollamaModel") or _SETTINGS_DEFAULTS["ollamaModel"]
        llm_gaps = _ollama.generate_questions(architecture, model, OLLAMA_BASE_URL)
        existing_texts = {g["question"] for g in gaps}
        for g in llm_gaps:
            if g.get("question") and g["question"] not in existing_texts:
                gaps.append(g)
                existing_texts.add(g["question"])

    # Exclude questions already answered when building the open list.
    answered_questions = {entry["question"] for entry in architecture["questions"].get("answered", []) if isinstance(entry, dict)}
    open_gaps = [gap for gap in gaps if gap["question"] not in answered_questions]
    architecture["questions"]["open"] = [gap["question"] for gap in open_gaps]

    atomic_write_json(output_path, architecture)
    # Return only open (unanswered) gaps so the UI doesn't re-filter them.
    return architecture, open_gaps, pending_components


def normalize_sources(architecture: dict) -> None:
    for source in architecture.get("sources", []):
        if "file" in source:
            source["file"] = relative_to_repo(Path(source["file"]).resolve())


def multipart_attribute(disposition: str, name: str) -> str:
    match = re.search(rf'{name}="([^"]*)"', disposition)
    return match.group(1) if match else ""


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name) or "uploaded-file"


def _clear_upload_dir(upload_dir: Path) -> None:
    """Remove all supported input files from *upload_dir*.

    Preserves sub-directories and the directory itself.  Only files with
    extensions in :data:`SUPPORTED_EXTENSIONS` are removed so that any
    non-input artifacts (e.g. ``.gitkeep``) are left untouched.
    """
    if not upload_dir.exists():
        return
    for child in upload_dir.iterdir():
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                child.unlink()
            except OSError:
                pass


def run(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), NetworkPicassoHandler)
    print(f"Network Picasso API listening on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
