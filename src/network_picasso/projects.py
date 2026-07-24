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

        # Collect sub-project directories (exclude the uploads/ leaf dir).
        sub_dirs = [d for d in sorted(customer_dir.iterdir()) if d.is_dir() and d.name != "uploads"]

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


def list_folders(root: Path) -> list[dict]:
    """Return top-level customer folders under *root*.

    Each entry::

        {
            "name":          str,   # directory name (customer slug)
            "path":          str,   # relative path
            "projectCount":  int,   # direct children that are projects
            "childCount":    int,   # sub-folders (engagement folders)
        }
    """
    repo_root = Path(__file__).resolve().parents[2]

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except ValueError:
            return str(p)

    if not root.exists():
        return []

    folders: list[dict] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        sub_dirs = [s for s in d.iterdir() if s.is_dir() and s.name != "uploads"]
        # A directory with sub-dirs contains project sub-folders.
        # A directory without sub-dirs IS itself a project.
        child_count   = len(sub_dirs)
        project_count = child_count if child_count else 1
        folders.append({
            "name":         d.name,
            "path":         _rel(d),
            "projectCount": project_count,
            "childCount":   child_count,
        })
    return folders


def list_projects_in_folder(folder_path: Path) -> list[dict]:
    """Return projects inside a specific customer folder.

    If the folder has sub-directories those are the projects; otherwise the
    folder itself is the project.
    """
    repo_root = Path(__file__).resolve().parents[2]

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except ValueError:
            return str(p)

    if not folder_path.exists():
        return []

    sub_dirs = [d for d in sorted(folder_path.iterdir()) if d.is_dir() and d.name != "uploads"]
    if sub_dirs:
        return [
            {
                "customer": folder_path.name,
                "project":  d.name,
                "path":     _rel(d),
                "hasArchitecture": (d / "architecture.json").exists(),
                "isLegacy": False,
            }
            for d in sub_dirs
        ]
    # Folder itself is the project.
    return [
        {
            "customer": folder_path.name,
            "project":  "",
            "path":     _rel(folder_path),
            "hasArchitecture": (folder_path / "architecture.json").exists(),
            "isLegacy": False,
        }
    ]


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

# ---------------------------------------------------------------------------
# Folder management
# ---------------------------------------------------------------------------


def rename_folder(folder_path: Path, new_name: str) -> Path:
    """Rename a customer (or engagement) folder to *new_name*.

    Returns the new path.  Raises ``ValueError`` if the new name is empty or if
    a directory with that slug already exists at the same level.
    """
    new_slug = safe_slug(new_name)
    if not new_slug:
        raise ValueError("Folder name cannot be empty")
    new_path = folder_path.parent / new_slug
    if new_path.exists() and new_path != folder_path:
        raise ValueError(f"A folder named '{new_slug}' already exists")
    folder_path.rename(new_path)
    return new_path


def delete_folder(folder_path: Path) -> None:
    """Delete a customer folder and everything inside it."""
    import shutil
    if folder_path.exists():
        shutil.rmtree(folder_path)


# ---------------------------------------------------------------------------
# Project management
# ---------------------------------------------------------------------------


def rename_project(project_path: Path, new_name: str) -> Path:
    """Rename a project directory to *new_name* slug.

    Returns the new path.  Raises ``ValueError`` on conflict.
    """
    new_slug = safe_slug(new_name)
    if not new_slug:
        raise ValueError("Project name cannot be empty")
    new_path = project_path.parent / new_slug
    if new_path.exists() and new_path != project_path:
        raise ValueError(f"A project named '{new_slug}' already exists")
    project_path.rename(new_path)
    return new_path


def delete_project(project_path: Path) -> None:
    """Delete a project directory and everything inside it."""
    import shutil
    if project_path.exists():
        shutil.rmtree(project_path)


def duplicate_project(source_path: Path, new_name: str) -> Path:
    """Copy *source_path* to a sibling directory named after *new_name*.

    Copies architecture.json only (not uploads — those can be re-uploaded).
    Returns the new project path.
    """
    import shutil, json
    new_slug = safe_slug(new_name)
    if not new_slug:
        raise ValueError("Project name cannot be empty")
    dest_path = source_path.parent / new_slug
    if dest_path.exists():
        raise ValueError(f"A project named '{new_slug}' already exists")
    dest_path.mkdir(parents=True)
    (dest_path / "uploads").mkdir()
    # Copy architecture.json if present, updating project name
    src_arch = source_path / "architecture.json"
    if src_arch.exists():
        arch = json.loads(src_arch.read_text(encoding="utf-8"))
        if "project" in arch:
            arch["project"]["name"] = new_name
        (dest_path / "architecture.json").write_text(
            json.dumps(arch, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return dest_path


def move_project(project_path: Path, dest_folder_path: Path) -> Path:
    """Move *project_path* into *dest_folder_path*.

    The project keeps its directory name (slug).  Raises ``ValueError`` if a
    project with that name already exists in the destination.
    Returns the new project path.
    """
    dest_path = dest_folder_path / project_path.name
    if dest_path.exists():
        raise ValueError(
            f"A project named '{project_path.name}' already exists in '{dest_folder_path.name}'"
        )
    dest_folder_path.mkdir(parents=True, exist_ok=True)
    project_path.rename(dest_path)
    return dest_path

