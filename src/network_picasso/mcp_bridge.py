"""Thin bridge to the drawio-mcp-server HTTP/MCP endpoint.

When the MCP server is running with ``--transport http`` (and optionally
``--editor``), it exposes:

  GET  http://localhost:3000/health        → {"status": "ok"}
  POST http://localhost:3000/mcp           → MCP JSON-RPC (Streamable HTTP)

This module provides helpers that let the Network Picasso Python server call
MCP tools over HTTP — without any third-party dependencies (stdlib only).

MCP tool calls use a minimal two-request sequence:
  1. POST /mcp with ``initialize``   → server returns session-id header
  2. POST /mcp with ``tools/call``   → returns tool result

Reference: Model Context Protocol Streamable HTTP transport spec.
"""
from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

MCP_BASE_URL = "http://127.0.0.1:3000"
_HEALTH_URL   = f"{MCP_BASE_URL}/health"
_MCP_URL      = f"{MCP_BASE_URL}/mcp"
_EDITOR_URL   = MCP_BASE_URL


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def is_running(timeout: int = 3) -> bool:
    """Return True if the drawio-mcp-server is reachable at localhost:3000."""
    try:
        with urllib.request.urlopen(_HEALTH_URL, timeout=timeout) as r:
            body = json.loads(r.read().decode())
            return body.get("status") == "ok"
    except (URLError, OSError, json.JSONDecodeError):
        return False


# ---------------------------------------------------------------------------
# MCP Streamable HTTP helpers
# ---------------------------------------------------------------------------

def _mcp_post(payload: dict, *, session_id: str | None = None, timeout: int = 30) -> tuple[dict, str | None]:
    """POST *payload* to /mcp.  Returns (parsed_response, session_id)."""
    data = json.dumps(payload).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type":    "application/json",
        "Accept":          "application/json, text/event-stream",
        "mcp-protocol-version": "2025-03-26",
    }
    if session_id:
        headers["mcp-session-id"] = session_id

    req = urllib.request.Request(_MCP_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            new_sid = resp.headers.get("mcp-session-id") or session_id
            raw = resp.read().decode("utf-8").strip()
            # Streamable HTTP may return SSE lines; extract the JSON data line.
            if raw.startswith("data:"):
                for line in raw.splitlines():
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        break
            return json.loads(raw), new_sid
    except (URLError, OSError) as exc:
        raise ConnectionError(f"drawio-mcp-server unreachable: {exc}") from exc


def _initialize() -> str:
    """Send MCP initialize handshake.  Returns the session ID."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "network-picasso", "version": "0.1"},
            "capabilities": {},
        },
    }
    _resp, sid = _mcp_post(payload)
    if not sid:
        raise ConnectionError("MCP server did not return a session ID")
    # Send initialized notification
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    _mcp_post(notif, session_id=sid, timeout=5)
    return sid


def call_tool(tool_name: str, arguments: dict, *, timeout: int = 30) -> dict:
    """Call a named MCP tool and return its result dict.

    Raises ``ConnectionError`` if the server is not reachable.
    Raises ``RuntimeError`` if the tool returns an error response.
    """
    sid = _initialize()
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp, _ = _mcp_post(payload, session_id=sid, timeout=timeout)
    if "error" in resp:
        raise RuntimeError(f"MCP tool error: {resp['error']}")
    return resp.get("result", {})


# ---------------------------------------------------------------------------
# High-level helpers used by server.py
# ---------------------------------------------------------------------------

def open_diagram_in_editor(xml: str, *, filename: str = "diagram.drawio") -> dict:
    """Push *xml* into the live Draw.io editor via ``import-diagram`` (replace mode).

    The editor must be open at http://localhost:3000 and have an active document.
    If only one document is connected the server auto-targets it.

    Returns the MCP tool result dict.
    """
    return call_tool("import-diagram", {
        "data":   xml,
        "format": "xml",
        "mode":   "replace",
        "filename": filename,
    }, timeout=15)


def add_xml_to_diagram(xml: str, *, target_page: dict | None = None) -> dict:
    """Merge *xml* cells into the current diagram page (``add`` mode).

    Use this to inject IBM-styled snippet XML without clearing the existing
    diagram.  Pass ``target_page`` as ``{"index": 0}`` or ``{"id": "page-id"}``
    to control which page receives the cells.

    Returns the MCP tool result dict.
    """
    args: dict = {
        "data":   xml,
        "format": "xml",
        "mode":   "add",
    }
    if target_page:
        args["target_page"] = target_page
    return call_tool("import-diagram", args, timeout=15)


def open_all_pages(diagrams: dict[str, str]) -> list[dict]:
    """Push all three diagram types as separate pages into the MCP editor.

    *diagrams* should be the output of ``render_all_diagrams()``::

        {"context": xml, "logical": xml, "deployment": xml}

    First page replaces the current document; subsequent pages are added as
    new pages.  Returns a list of MCP result dicts.
    """
    page_names = {
        "context":    "Context",
        "logical":    "Logical Architecture",
        "deployment": "Deployment",
    }
    results: list[dict] = []
    first = True
    for dtype, page_name in page_names.items():
        xml = diagrams.get(dtype, "")
        if not xml:
            continue
        if first:
            # Replace any existing content with the first page
            result = call_tool("import-diagram", {
                "data": xml, "format": "xml", "mode": "replace",
                "filename": f"{page_name}.drawio",
            }, timeout=30)
            first = False
        else:
            # Add subsequent diagrams as new pages
            result = call_tool("import-diagram", {
                "data": xml, "format": "xml", "mode": "new-page",
                "filename": f"{page_name}.drawio",
            }, timeout=30)
        results.append(result)
    return results
