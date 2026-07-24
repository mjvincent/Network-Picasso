"""Project / workspace management helpers.

Folder layout
-------------
<projectsRoot>/
  <customer-slug>/
    <project-slug>/
      uploads/            ← source files
      architecture.json   ← canonical model
  <customer-slug>/
    architecture.json     ← single-project customer (no sub-project folder)

The legacy ``inputs/uploads/current/`` workspace is surfaced as a virtual
"Unsaved workspace" entry so the sidebar shows it alongside named projects.
"""
from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LEGACY_PATH = "inputs/uploads/current"
_DEFAULT_PROJECTS_ROOT = "inputs/projects"

# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------


def safe_slug(name: str) -> str:
    """Return a filesystem-safe, lowercase slug for *name*.

    Rules:
    - Lower-case.
    - Any run of non-alphanumeric characters (spaces, dashes, em-dashes,
      special chars, …) is collapsed to a single hyphen.
    - Leading / trailing hyphens are stripped.
    - Falls back to ``"project"`` if the sanitised result would be empty.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "project"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def project_uploads_path(project_path: Path) -> Path:
    """Return the uploads sub-directory for *project_path*."""
    return project_path / "uploads"


def project_architecture_path(project_path: Path) -> Path:
    """Return the canonical architecture JSON path for *project_path*."""
    return project_path / "architecture.json"


def resolve_projects_root(settings: dict) -> Path:
    """Resolve the projects root from *settings*, expanding ``~`` if needed.

    Falls back to ``REPO_ROOT / inputs/projects`` when the key is absent.
    ``REPO_ROOT`` is inferred at runtime so this module stays dep-free.
    """
    repo_root = Path(__file__).resolve().parents[2]
    raw: str = settings.get("projectsRoot") or _DEFAULT_PROJECTS_ROOT
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


# ---------------------------------------------------------------------------
# Project discovery
# ---------------------------------------------------------------------------


def list_projects(root: Path) -> list[dict]:
    """Scan *root* for customer/project folders.

    Returns a list of dicts::

        {
            "customer": str,   # customer slug (directory name)
            "project":  str,   # project slug (sub-directory name) or ""
            "path":     str,   # path relative to repo root (as string)
            "hasArchitecture": bool,
            "isLegacy": bool,
        }

    Also prepends the legacy ``inputs/uploads/current/`` entry when that
    directory exists, so the sidebar always shows the unsaved workspace.

    Safe to call when *root* does not exist — returns ``[]`` (plus legacy if
    applicable) without raising.
    """
    repo_root = Path(__file__).resolve().parents[2]

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except ValueError:
            return str(p)

    results: list[dict] = []

    # Legacy workspace entry.
    legacy_path = repo_root / _LEGACY_PATH
    if legacy_path.exists():
        results.append({
            "customer": "Unsaved workspace",
            "project": "",
            "path": _rel(legacy_path),
            "hasArchitecture": (legacy_path / "architecture.json").exists(),
            "isLegacy": True,
        })

    if not root.exists():
        return results

    for customer_dir in sorted(root.iterdir()):
        if not customer_dir.is_dir():
            continue
        customer = customer_dir.name

        # Collect sub-project directories.
        sub_dirs = [d for d in sorted(customer_dir.iterdir()) if d.is_dir()]

        if sub_dirs:
            # Customer has one or more project sub-folders.
            for proj_dir in sub_dirs:
                results.append({
                    "customer": customer,
                    "project": proj_dir.name,
                    "path": _rel(proj_dir),
                    "hasArchitecture": (proj_dir / "architecture.json").exists(),
                    "isLegacy": False,
                })
        else:
            # Single-project customer — architecture lives directly in customer_dir.
            results.append({
                "customer": customer,
                "project": "",
                "path": _rel(customer_dir),
                "hasArchitecture": (customer_dir / "architecture.json").exists(),
                "isLegacy": False,
            })

    return results


# ---------------------------------------------------------------------------
# Project creation
# ---------------------------------------------------------------------------


def create_project(root: Path, customer: str, project: str | None = None) -> Path:
    """Create the folder(s) for a customer/project and return the project path.

    - ``root / safe_slug(customer)`` is created when *project* is ``None`` or
      empty (single-project customer layout).
    - ``root / safe_slug(customer) / safe_slug(project)`` is created when
      *project* is provided.

    The ``uploads/`` sub-directory is created inside the project path so it
    is ready to receive files immediately.

    Idempotent — calling it a second time with the same names is a no-op.
    """
    customer_slug = safe_slug(customer)
    proj_path: Path

    if project:
        project_slug = safe_slug(project)
        proj_path = root / customer_slug / project_slug
    else:
        proj_path = root / customer_slug

    # Create the uploads sub-directory (parents implicitly created).
    (proj_path / "uploads").mkdir(parents=True, exist_ok=True)

    return proj_path
