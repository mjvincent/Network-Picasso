"""Thin bridge to the drawio-mcp-server HTTP/MCP endpoint.

When the MCP server is running with ``--transport http`` (and optionally
``--editor``), it exposes:

  GET  http://localhost:4000/health        → {"status": "ok"}
  POST http://localhost:4000/mcp           → MCP JSON-RPC (Streamable HTTP)

This module provides helpers that let the Network Picasso Python server call
MCP tools over HTTP — without any third-party dependencies (stdlib only).

drawio-mcp-server 2.2.0 behaviour:
  • Stateless — no session-id handshake required.
  • All responses use SSE format: ``event: message\\ndata: {...}``
  • Notifications (initialize) return 202 with empty body — ignore them.
  • ``import-diagram`` requires a ``target_document`` with the document ID
    obtained from ``list-documents``.

Reference: Model Context Protocol Streamable HTTP transport spec.
"""
from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

MCP_BASE_URL = "http://127.0.0.1:4000"
_HEALTH_URL   = f"{MCP_BASE_URL}/health"
_MCP_URL      = f"{MCP_BASE_URL}/mcp"
_EDITOR_URL   = MCP_BASE_URL

_REQ_ID = 0


def _next_id() -> int:
    global _REQ_ID
    _REQ_ID += 1
    return _REQ_ID


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def is_running(timeout: int = 3) -> bool:
    """Return True if the drawio-mcp-server is reachable at localhost:4000."""
    try:
        with urllib.request.urlopen(_HEALTH_URL, timeout=timeout) as r:
            body = json.loads(r.read().decode())
            return body.get("status") == "ok"
    except (URLError, OSError, json.JSONDecodeError):
        return False


# ---------------------------------------------------------------------------
# MCP Streamable HTTP helpers
# ---------------------------------------------------------------------------

def _mcp_post(payload: dict, *, timeout: int = 30) -> dict | None:
    """POST *payload* to /mcp.

    Returns the parsed JSON-RPC result dict, or None for notifications
    (202 No Content).  Raises ``ConnectionError`` on network failure.
    """
    data = json.dumps(payload).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type":         "application/json",
        "Accept":               "application/json, text/event-stream",
        "mcp-protocol-version": "2025-03-26",
    }
    req = urllib.request.Request(_MCP_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8").strip()
            if not raw:
                # 202 No Content — notification acknowledged, no body expected
                return None
            # SSE envelope: extract the JSON from the ``data:`` line
            if raw.startswith("event:") or raw.startswith("data:"):
                for line in raw.splitlines():
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        break
            return json.loads(raw)
    except (URLError, OSError) as exc:
        raise ConnectionError(f"drawio-mcp-server unreachable: {exc}") from exc


def call_tool(tool_name: str, arguments: dict, *, timeout: int = 30) -> dict:
    """Call a named MCP tool and return its result dict.

    drawio-mcp-server 2.2.0 is stateless — no initialize handshake needed.

    Raises ``ConnectionError`` if the server is not reachable.
    Raises ``RuntimeError`` if the tool returns an error response.
    """
    payload = {
        "jsonrpc": "2.0",
        "id":      _next_id(),
        "method":  "tools/call",
        "params":  {"name": tool_name, "arguments": arguments},
    }
    resp = _mcp_post(payload, timeout=timeout)
    if resp is None:
        raise RuntimeError(f"MCP tool '{tool_name}' returned no response")
    if "error" in resp:
        raise RuntimeError(f"MCP tool error: {resp['error']}")
    return resp.get("result", {})


# ---------------------------------------------------------------------------
# Document discovery
# ---------------------------------------------------------------------------

def _get_document_id() -> str:
    """Return the ID of the first connected Draw.io document.

    Raises ``RuntimeError`` if no browser tab has the editor open.
    """
    resp = call_tool("list-documents", {}, timeout=10)
    # result.content[0].text is a JSON string with {"success": true, "result": [...]}
    content = resp.get("content", [])
    if content:
        inner_text = content[0].get("text", "")
        try:
            inner = json.loads(inner_text)
            docs = inner.get("result", [])
            if docs:
                return docs[0]["id"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
    raise RuntimeError(
        "No connected Draw.io documents. "
        "Open http://localhost:4000 in your browser first."
    )


# ---------------------------------------------------------------------------
# High-level helpers used by server.py
# ---------------------------------------------------------------------------

def open_diagram_in_editor(xml: str, *, filename: str = "diagram.drawio") -> dict:
    """Push *xml* into the live Draw.io editor via ``import-diagram`` (replace mode).

    The editor must be open at http://localhost:4000 and have an active document.
    Targets page index 0 (current page).

    Returns the MCP tool result dict.
    """
    doc_id = _get_document_id()
    return call_tool("import-diagram", {
        "data":            xml,
        "format":          "xml",
        "mode":            "replace",
        "filename":        filename,
        "target_page":     {"index": 0},
        "target_document": {"id": doc_id},
    }, timeout=15)


def add_xml_to_diagram(xml: str, *, target_page: dict | None = None) -> dict:
    """Merge *xml* cells into the current diagram page (``add`` mode).

    Use this to inject IBM-styled snippet XML without clearing the existing
    diagram.  Pass ``target_page`` as ``{"index": 0}`` or ``{"id": "page-id"}``
    to control which page receives the cells.

    Returns the MCP tool result dict.
    """
    doc_id = _get_document_id()
    tp = target_page or {"index": 0}
    return call_tool("import-diagram", {
        "data":            xml,
        "format":          "xml",
        "mode":            "add",
        "target_page":     tp,
        "target_document": {"id": doc_id},
    }, timeout=15)


def open_all_pages(diagrams: dict[str, str]) -> list[dict]:
    """Push all three diagram types as separate pages into the MCP editor.

    *diagrams* should be the output of ``render_all_diagrams()``::

        {"context": xml, "logical": xml, "deployment": xml}

    First page replaces page 0; subsequent pages are added as new pages.
    Returns a list of MCP result dicts.
    """
    doc_id = _get_document_id()
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
            result = call_tool("import-diagram", {
                "data":            xml,
                "format":          "xml",
                "mode":            "replace",
                "filename":        f"{page_name}.drawio",
                "target_page":     {"index": 0},
                "target_document": {"id": doc_id},
            }, timeout=30)
            first = False
        else:
            result = call_tool("import-diagram", {
                "data":            xml,
                "format":          "xml",
                "mode":            "new-page",
                "filename":        f"{page_name}.drawio",
                "target_document": {"id": doc_id},
            }, timeout=30)
        results.append(result)
    return results
