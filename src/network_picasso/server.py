from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .drawio import render_drawio
from .intake import build_architecture_from_inputs
from .questions import find_design_gaps


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = "examples/sample-inputs"
DEFAULT_ARCHITECTURE_PATH = "examples/sample/architecture.json"
UPLOAD_INPUT_PATH = "inputs/uploads/current"
UPLOAD_ARCHITECTURE_PATH = "inputs/uploads/current/architecture.json"


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
            self.send_json(
                {
                    "architecture": architecture,
                    "questions": find_design_gaps(architecture),
                    "architecturePath": relative_to_repo(architecture_path),
                }
            )
            return
        self.send_error_json(404, "Route not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/upload-intake":
                self.handle_upload_intake()
                return

            payload = self.read_json()
            if parsed.path == "/api/intake":
                self.handle_intake(payload)
            elif parsed.path == "/api/questions":
                self.handle_questions(payload)
            elif parsed.path == "/api/generate-drawio":
                self.handle_generate_drawio(payload)
            else:
                self.send_error_json(404, "Route not found")
        except Exception as exc:  # Keep the local UI useful during early iteration.
            self.send_error_json(500, str(exc))

    def handle_intake(self, payload: dict) -> None:
        input_path = repo_path(payload.get("inputPath") or DEFAULT_INPUT_PATH)
        project_name = payload.get("projectName") or None
        output_path = repo_path(payload.get("outputPath") or DEFAULT_ARCHITECTURE_PATH)

        architecture, gaps = run_intake(input_path, output_path, project_name=project_name)

        self.send_json(
            {
                "architecture": architecture,
                "questions": gaps,
                "outputPath": relative_to_repo(output_path),
            }
        )

    def handle_upload_intake(self) -> None:
        fields, files = self.read_multipart()
        if not files:
            self.send_error_json(400, "Upload at least one BOM, pricing, spreadsheet, CSV, JSON, Markdown, or text file.")
            return

        upload_dir = repo_path(UPLOAD_INPUT_PATH)
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        for uploaded in files:
            filename = safe_filename(uploaded["filename"])
            target = upload_dir / filename
            target.write_bytes(uploaded["content"])
            saved_files.append(relative_to_repo(target))

        project_name = fields.get("projectName") or "Customer Architecture"
        output_path = repo_path(UPLOAD_ARCHITECTURE_PATH)
        architecture, gaps = run_intake(upload_dir, output_path, project_name=project_name)

        self.send_json(
            {
                "architecture": architecture,
                "questions": gaps,
                "inputPath": relative_to_repo(upload_dir),
                "outputPath": relative_to_repo(output_path),
                "files": saved_files,
            }
        )

    def handle_questions(self, payload: dict) -> None:
        architecture = payload.get("architecture")
        if not architecture:
            architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(architecture_path)
        self.send_json({"questions": find_design_gaps(architecture)})

    def handle_generate_drawio(self, payload: dict) -> None:
        architecture = payload.get("architecture")
        if not architecture:
            architecture_path = repo_path(payload.get("architecturePath") or DEFAULT_ARCHITECTURE_PATH)
            architecture = read_json_file(architecture_path)
        diagram_type = payload.get("diagramType") or "deployment"
        output_path = repo_path(payload.get("outputPath") or f"outputs/network-picasso-{diagram_type}.drawio")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_drawio(architecture, diagram_type=diagram_type), encoding="utf-8")
        self.send_json({"outputPath": relative_to_repo(output_path)})

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
        self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_intake(input_path: Path, output_path: Path, *, project_name: str | None) -> tuple[dict, list[dict[str, str]]]:
    architecture = build_architecture_from_inputs(input_path, project_name=project_name)
    normalize_sources(architecture)
    gaps = find_design_gaps(architecture)
    architecture["questions"]["open"] = [gap["question"] for gap in gaps]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(architecture, indent=2), encoding="utf-8")
    return architecture, gaps


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


def run(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), NetworkPicassoHandler)
    print(f"Network Picasso API listening on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
