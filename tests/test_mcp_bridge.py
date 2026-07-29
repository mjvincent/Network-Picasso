from __future__ import annotations

import json

from network_picasso import mcp_bridge


def _tool_text(result: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps({"success": True, "result": result})}]}


def test_open_diagram_in_editor_renames_target_page(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_call_tool(name: str, args: dict, *, timeout: int = 30) -> dict:
        calls.append((name, args))
        if name == "list-documents":
            return _tool_text([{"id": "doc-1"}])
        return _tool_text({"ok": True})

    monkeypatch.setattr(mcp_bridge, "call_tool", fake_call_tool)

    mcp_bridge.open_diagram_in_editor("<mxfile />", filename="deployment.drawio", page_name="Deployment")

    assert [name for name, _ in calls] == ["list-documents", "import-diagram", "rename-page"]
    assert calls[1][1]["mode"] == "replace"
    assert calls[1][1]["target_page"] == {"index": 0}
    assert calls[2][1]["page"] == {"index": 0}
    assert calls[2][1]["name"] == "Deployment"


def test_open_all_pages_reuses_and_renames_existing_page_slots(monkeypatch):
    calls: list[tuple[str, dict]] = []
    page_count = 5

    def fake_call_tool(name: str, args: dict, *, timeout: int = 30) -> dict:
        nonlocal page_count
        calls.append((name, args))
        if name == "list-documents":
            return _tool_text([{"id": "doc-1"}])
        if name == "list-pages":
            return _tool_text([
                {"index": index, "id": f"page-{index}", "name": "Deployment"}
                for index in range(page_count)
            ])
        if name == "create-page":
            page_count += 1
            return _tool_text({"index": page_count - 1})
        return _tool_text({"ok": True})

    monkeypatch.setattr(mcp_bridge, "call_tool", fake_call_tool)

    mcp_bridge.open_all_pages({
        "executive": "<mxfile />",
        "context": "<mxfile />",
        "logical": "<mxfile />",
        "deployment": "<mxfile />",
        "decisions": "<mxfile />",
    })

    imports = [args for name, args in calls if name == "import-diagram"]
    renames = [args for name, args in calls if name == "rename-page"]

    assert [args["mode"] for args in imports] == ["replace"] * 5
    assert [args["target_page"] for args in imports] == [
        {"index": 0},
        {"index": 1},
        {"index": 2},
        {"index": 3},
        {"index": 4},
    ]
    assert [args["name"] for args in renames] == [
        "Executive Overview",
        "Context",
        "Logical Architecture",
        "Deployment",
        "Assumptions & Decisions",
    ]
    assert not any(name == "create-page" for name, _ in calls)


def test_open_all_pages_creates_missing_page_slots(monkeypatch):
    calls: list[tuple[str, dict]] = []
    page_count = 1

    def fake_call_tool(name: str, args: dict, *, timeout: int = 30) -> dict:
        nonlocal page_count
        calls.append((name, args))
        if name == "list-documents":
            return _tool_text([{"id": "doc-1"}])
        if name == "list-pages":
            return _tool_text([
                {"index": index, "id": f"page-{index}", "name": "Page"}
                for index in range(page_count)
            ])
        if name == "create-page":
            page_count += 1
            return _tool_text({"index": page_count - 1})
        return _tool_text({"ok": True})

    monkeypatch.setattr(mcp_bridge, "call_tool", fake_call_tool)

    mcp_bridge.open_all_pages({
        "executive": "<mxfile />",
        "context": "<mxfile />",
        "logical": "<mxfile />",
        "deployment": "<mxfile />",
        "decisions": "<mxfile />",
    })

    create_calls = [args for name, args in calls if name == "create-page"]
    assert len(create_calls) == 4
    assert create_calls[-1]["name"] == "Network Picasso Page 5"


def test_verify_page_tabs_reports_clean_expected_order(monkeypatch):
    def fake_call_tool(name: str, args: dict, *, timeout: int = 30) -> dict:
        if name == "list-documents":
            return _tool_text([{"id": "doc-1"}])
        if name == "list-pages":
            return _tool_text([
                {"index": 0, "id": "page-0", "name": "Executive Overview"},
                {"index": 1, "id": "page-1", "name": "Context"},
                {"index": 2, "id": "page-2", "name": "Logical Architecture"},
                {"index": 3, "id": "page-3", "name": "Deployment"},
                {"index": 4, "id": "page-4", "name": "Assumptions & Decisions"},
            ])
        return _tool_text({"ok": True})

    monkeypatch.setattr(mcp_bridge, "call_tool", fake_call_tool)

    result = mcp_bridge.verify_page_tabs()

    assert result["ok"] is True
    assert result["duplicates"] == []
    assert result["extra"] == []
    assert result["missing"] == []


def test_verify_page_tabs_reports_duplicate_deployment(monkeypatch):
    def fake_call_tool(name: str, args: dict, *, timeout: int = 30) -> dict:
        if name == "list-documents":
            return _tool_text([{"id": "doc-1"}])
        if name == "list-pages":
            return _tool_text([
                {"index": 0, "id": "page-0", "name": "Deployment"},
                {"index": 1, "id": "page-1", "name": "Context"},
                {"index": 2, "id": "page-2", "name": "Logical Architecture"},
                {"index": 3, "id": "page-3", "name": "Deployment"},
                {"index": 4, "id": "page-4", "name": "Assumptions & Decisions"},
            ])
        return _tool_text({"ok": True})

    monkeypatch.setattr(mcp_bridge, "call_tool", fake_call_tool)

    result = mcp_bridge.verify_page_tabs()

    assert result["ok"] is False
    assert result["missing"] == ["Executive Overview"]
    assert result["duplicates"] == ["Deployment"]
    assert result["actual"][:5] == [
        "Deployment",
        "Context",
        "Logical Architecture",
        "Deployment",
        "Assumptions & Decisions",
    ]
