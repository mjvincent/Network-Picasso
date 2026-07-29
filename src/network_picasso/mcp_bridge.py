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
import os
import urllib.request
from urllib.error import URLError

from .drawio import DIAGRAM_PAGE_NAMES

MCP_BASE_URL = os.environ.get("NETWORK_PICASSO_MCP_BASE_URL", "http://127.0.0.1:4000")
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
    """Return True if the drawio-mcp-server is reachable."""
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


def _decode_tool_text(resp: dict) -> dict:
    """Decode the drawio-mcp-server JSON payload nested inside text content."""
    content = resp.get("content", [])
    if not content:
        return {}
    text = str(content[0].get("text", "")).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _list_pages(doc_id: str) -> list[dict]:
    resp = call_tool("list-pages", {
        "target_document": {"id": doc_id},
    }, timeout=10)
    inner = _decode_tool_text(resp)
    pages = inner.get("result", [])
    return pages if isinstance(pages, list) else []


def _rename_page(doc_id: str, index: int, name: str) -> dict:
    return call_tool("rename-page", {
        "page":            {"index": index},
        "name":            name,
        "target_document": {"id": doc_id},
    }, timeout=10)


def _ensure_page_count(doc_id: str, count: int) -> None:
    pages = _list_pages(doc_id)
    while len(pages) < count:
        call_tool("create-page", {
            "name":            f"Network Picasso Page {len(pages) + 1}",
            "target_document": {"id": doc_id},
        }, timeout=10)
        pages = _list_pages(doc_id)


def verify_page_tabs() -> dict:
    """Inspect the live MCP document and report whether expected tabs are present.

    The MCP server can rename and create pages but does not expose page deletion,
    so this check reports extra or duplicate tabs and lets the UI guide the user
    toward rebuilding the first five Network Picasso page slots.
    """
    doc_id = _get_document_id()
    pages = _list_pages(doc_id)
    expected = list(DIAGRAM_PAGE_NAMES.values())
    actual = [str(page.get("name") or "") for page in pages]
    first_five = actual[:len(expected)]
    missing = [name for name in expected if name not in actual]
    duplicate_names = sorted({name for name in actual if name and actual.count(name) > 1})
    extra = actual[len(expected):]
    ok = first_five == expected and not duplicate_names and not extra
    return {
        "ok": ok,
        "expected": expected,
        "actual": actual,
        "missing": missing,
        "duplicates": duplicate_names,
        "extra": extra,
        "pages": pages,
    }


# ---------------------------------------------------------------------------
# High-level helpers used by server.py
# ---------------------------------------------------------------------------

def open_diagram_in_editor(
    xml: str,
    *,
    filename: str = "diagram.drawio",
    page_name: str | None = None,
) -> dict:
    """Push *xml* into the live Draw.io editor via ``import-diagram`` (replace mode).

    The editor must be open at http://localhost:4000 and have an active document.
    Targets page index 0 (current page).

    Returns the MCP tool result dict.
    """
    doc_id = _get_document_id()
    result = call_tool("import-diagram", {
        "data":            xml,
        "format":          "xml",
        "mode":            "replace",
        "filename":        filename,
        "target_page":     {"index": 0},
        "target_document": {"id": doc_id},
    }, timeout=15)
    if page_name:
        _rename_page(doc_id, 0, page_name)
    return result


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
    """Push all diagram types as separate pages into the MCP editor.

    *diagrams* should be the output of ``render_all_diagrams()``::

        {"executive": xml, "context": xml, "logical": xml, "deployment": xml, "decisions": xml}

    Page slots 0-4 are reused and renamed so stale tabs from previous imports
    do not survive as duplicate Deployment pages. New blank pages are created
    only when the live editor has fewer pages than Network Picasso needs.
    Returns a list of MCP result dicts.
    """
    doc_id = _get_document_id()
    page_items = [(dtype, page_name) for dtype, page_name in DIAGRAM_PAGE_NAMES.items() if diagrams.get(dtype, "")]
    _ensure_page_count(doc_id, len(page_items))
    results: list[dict] = []
    for index, (dtype, page_name) in enumerate(page_items):
        xml = diagrams[dtype]
        result = call_tool("import-diagram", {
            "data":            xml,
            "format":          "xml",
            "mode":            "replace",
            "filename":        f"{page_name}.drawio",
            "target_page":     {"index": index},
            "target_document": {"id": doc_id},
        }, timeout=30)
        _rename_page(doc_id, index, page_name)
        results.append(result)
    return results
