from __future__ import annotations

import json
import pathlib

import pytest

from network_picasso.projects import (
    create_project,
    delete_folder,
    delete_project,
    duplicate_project,
    ensure_within_root,
    list_folders,
    list_projects,
    list_projects_in_folder,
    move_project,
    rename_folder,
    rename_project,
    resolve_projects_root,
    safe_slug,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_safe_slug_basic():
    assert safe_slug("Acme Bank") == "acme-bank"


def test_safe_slug_special_chars():
    result = safe_slug("Acme Bank — Healthcare")
    assert result == "acme-bank-healthcare"


def test_safe_slug_empty():
    assert safe_slug("---") == "project"
    assert safe_slug("") == "project"


def test_create_project_customer_only(tmp_path):
    """Customer-only project creates a folder with an uploads/ subfolder."""
    root = tmp_path / "projects"
    p = create_project(root, "Acme Bank")
    assert p.exists()
    assert p.name == "acme-bank"
    assert (p / "uploads").is_dir()


def test_create_project_with_sub(tmp_path):
    """Customer + project creates customer/project/uploads/ hierarchy."""
    root = tmp_path / "projects"
    p = create_project(root, "Acme Bank", "Q1 Modernisation")
    assert p.exists()
    assert p.name == "q1-modernisation"
    assert p.parent.name == "acme-bank"
    assert (p / "uploads").is_dir()


def test_list_projects_empty_root(tmp_path):
    """Non-existent root returns at most the legacy entry (no crash)."""
    root = tmp_path / "does-not-exist"
    result = list_projects(root)
    # May contain the legacy uploads/current entry if it exists on disk, but must not raise
    assert isinstance(result, list)


def test_list_projects_with_data(tmp_path):
    """After creating a project, list_projects returns it."""
    root = tmp_path / "projects"
    create_project(root, "Contoso", "Cloud Migration")
    projects = list_projects(root)
    paths = [p["path"] for p in projects]
    assert any("contoso" in path for path in paths)
    assert any("cloud-migration" in path for path in paths)


def test_resolve_projects_root_default():
    """Empty settings dict resolves to a path ending in inputs/projects."""
    root = resolve_projects_root({})
    assert str(root).endswith("inputs/projects")


def test_resolve_projects_root_custom(tmp_path):
    """Custom projectsRoot in settings is resolved correctly."""
    custom = tmp_path / "my-projects"
    root = resolve_projects_root({"projectsRoot": str(custom)})
    assert root == custom.resolve()


def test_ensure_within_root_allows_child(tmp_path):
    root = tmp_path / "projects"
    child = root / "acme" / "q1"
    child.mkdir(parents=True)
    assert ensure_within_root(child, root) == child.resolve()


def test_ensure_within_root_rejects_escape(tmp_path):
    root = tmp_path / "projects"
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="outside"):
        ensure_within_root(outside, root)


# ---------------------------------------------------------------------------
# list_folders / list_projects_in_folder
# ---------------------------------------------------------------------------

def test_list_folders_empty_root(tmp_path):
    """Non-existent root returns an empty list."""
    result = list_folders(tmp_path / "does-not-exist")
    assert result == []


def test_list_folders_returns_counts(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "contoso")
    folders = list_folders(root)
    names = {f["name"] for f in folders}
    assert "acme" in names
    assert "contoso" in names
    acme = next(f for f in folders if f["name"] == "acme")
    assert acme["projectCount"] == 1  # one sub-project
    assert acme["childCount"] == 1


def test_list_projects_in_folder_with_subprojects(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "acme", "q2")
    result = list_projects_in_folder(root / "acme")
    assert len(result) == 2
    project_names = {r["project"] for r in result}
    assert "q1" in project_names and "q2" in project_names


def test_list_projects_in_folder_single(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "contoso")
    result = list_projects_in_folder(root / "contoso")
    assert len(result) == 1
    assert result[0]["project"] == ""


# ---------------------------------------------------------------------------
# rename_folder / delete_folder
# ---------------------------------------------------------------------------

def test_rename_folder(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme")
    new_path = rename_folder(root / "acme", "acme-new")
    assert new_path.exists()
    assert new_path.name == "acme-new"
    assert not (root / "acme").exists()


def test_rename_folder_conflict(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme")
    create_project(root, "contoso")
    with pytest.raises(ValueError, match="already exists"):
        rename_folder(root / "acme", "contoso")


def test_delete_folder(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    delete_folder(root / "acme")
    assert not (root / "acme").exists()


def test_delete_folder_nonexistent_is_noop(tmp_path):
    """Deleting a non-existent folder should not raise."""
    delete_folder(tmp_path / "does-not-exist")


# ---------------------------------------------------------------------------
# rename_project / delete_project
# ---------------------------------------------------------------------------

def test_rename_project(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    new_path = rename_project(root / "acme" / "q1", "q1-renamed")
    assert new_path.exists()
    assert new_path.name == "q1-renamed"


def test_rename_project_conflict(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "acme", "q2")
    with pytest.raises(ValueError, match="already exists"):
        rename_project(root / "acme" / "q1", "q2")


def test_delete_project(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    delete_project(root / "acme" / "q1")
    assert not (root / "acme" / "q1").exists()


# ---------------------------------------------------------------------------
# duplicate_project
# ---------------------------------------------------------------------------

def test_duplicate_project_no_arch(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    dest = duplicate_project(root / "acme" / "q1", "q1-copy")
    assert dest.exists()
    assert (dest / "uploads").is_dir()
    assert not (dest / "architecture.json").exists()


def test_duplicate_project_with_arch(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    arch = {"project": {"name": "q1"}, "ibm_cloud": {}}
    (root / "acme" / "q1" / "architecture.json").write_text(
        json.dumps(arch), encoding="utf-8"
    )
    dest = duplicate_project(root / "acme" / "q1", "q1-copy")
    copied = json.loads((dest / "architecture.json").read_text())
    assert copied["project"]["name"] == "q1-copy"


def test_duplicate_project_conflict(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "acme", "q1-copy")
    with pytest.raises(ValueError, match="already exists"):
        duplicate_project(root / "acme" / "q1", "q1-copy")


# ---------------------------------------------------------------------------
# move_project
# ---------------------------------------------------------------------------

def test_move_project(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "contoso")
    dest = move_project(root / "acme" / "q1", root / "contoso")
    assert dest.exists()
    assert dest.parent == root / "contoso"
    assert not (root / "acme" / "q1").exists()


def test_move_project_conflict(tmp_path):
    root = tmp_path / "projects"
    create_project(root, "acme", "q1")
    create_project(root, "contoso", "q1")
    with pytest.raises(ValueError, match="already exists"):
        move_project(root / "acme" / "q1", root / "contoso")
