from __future__ import annotations

import pathlib

import pytest

from network_picasso.projects import (
    create_project,
    list_projects,
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
