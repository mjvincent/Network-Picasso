from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .projects import safe_slug


SCHEMA_VERSION = 1
SNAPSHOT_EVENT_TYPES = {
    "autosave",
    "upload-intake",
    "intake",
    "answer-saved",
    "requirements-saved",
    "components-confirmed",
    "pattern-set",
    "diagram-quality",
    "project-imported",
    "project-duplicated",
    "manual-sync",
    "restore-point",
}
AUTOSAVE_RETENTION_LIMIT = 25


def _retention_limit_from_env() -> int:
    raw_limit = os.environ.get("NETWORK_PICASSO_AUTOSAVE_RETENTION", str(AUTOSAVE_RETENTION_LIMIT))
    try:
        return max(1, int(raw_limit))
    except ValueError:
        return AUTOSAVE_RETENTION_LIMIT


AUTOSAVE_RETENTION_LIMIT = _retention_limit_from_env()


@dataclass(frozen=True)
class PersistenceStatus:
    enabled: bool
    connected: bool
    schemaVersion: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "schemaVersion": self.schemaVersion,
            "message": self.message,
        }


def database_url() -> str:
    return os.environ.get("NETWORK_PICASSO_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""


def is_enabled() -> bool:
    return bool(database_url())


def status() -> PersistenceStatus:
    if not is_enabled():
        return PersistenceStatus(False, False, SCHEMA_VERSION, "Postgres persistence is disabled")
    try:
        with _connect() as conn:
            conn.execute("select 1")
        return PersistenceStatus(True, True, SCHEMA_VERSION, "Postgres persistence is connected")
    except Exception as exc:
        return PersistenceStatus(True, False, SCHEMA_VERSION, f"Postgres persistence unavailable: {exc}")


def init_schema() -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        conn.execute(
            """
            create table if not exists np_customers (
              slug text primary key,
              display_name text not null,
              path text not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )
        conn.execute(
            """
            create table if not exists np_projects (
              id text primary key,
              customer_slug text not null references np_customers(slug) on update cascade on delete cascade,
              project_slug text not null,
              display_name text not null,
              path text not null unique,
              has_architecture boolean not null default false,
              architecture jsonb,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now(),
              unique(customer_slug, project_slug)
            )
            """
        )
        conn.execute(
            """
            create table if not exists np_project_events (
              id bigserial primary key,
              project_id text references np_projects(id) on delete cascade,
              event_type text not null,
              detail jsonb not null default '{}'::jsonb,
              created_at timestamptz not null default now()
            )
            """
        )
        conn.execute(
            """
            create table if not exists np_project_snapshots (
              id bigserial primary key,
              project_id text references np_projects(id) on delete cascade,
              label text not null,
              event_type text not null,
              architecture jsonb not null,
              created_at timestamptz not null default now()
            )
            """
        )
        conn.execute("create index if not exists ix_np_projects_customer on np_projects(customer_slug)")
        conn.execute("create index if not exists ix_np_project_events_project on np_project_events(project_id)")
        conn.execute("create index if not exists ix_np_project_snapshots_project on np_project_snapshots(project_id)")


def upsert_project(
    *,
    customer: str,
    project: str,
    path: str,
    architecture: dict | None,
    event_type: str | None = None,
    detail: dict | None = None,
) -> None:
    if not is_enabled():
        return
    customer_slug = safe_slug(customer)
    project_slug = safe_slug(project or "default")
    display_name = project or project_slug
    project_id = f"{customer_slug}/{project_slug}"
    has_architecture = architecture is not None
    with _connect() as conn:
        conn.execute(
            """
            insert into np_customers(slug, display_name, path, updated_at)
            values (%s, %s, %s, now())
            on conflict(slug) do update set
              display_name = excluded.display_name,
              path = excluded.path,
              updated_at = now()
            """,
            (customer_slug, customer, str(Path(path).parent),),
        )
        conn.execute(
            """
            insert into np_projects(
              id, customer_slug, project_slug, display_name, path, has_architecture, architecture, updated_at
            )
            values (%s, %s, %s, %s, %s, %s, %s::jsonb, now())
            on conflict(id) do update set
              customer_slug = excluded.customer_slug,
              project_slug = excluded.project_slug,
              display_name = excluded.display_name,
              path = excluded.path,
              has_architecture = excluded.has_architecture,
              architecture = coalesce(excluded.architecture, np_projects.architecture),
              updated_at = now()
            """,
            (
                project_id,
                customer_slug,
                project_slug,
                display_name,
                path,
                has_architecture,
                json.dumps(architecture) if architecture is not None else None,
            ),
        )
        if event_type:
            conn.execute(
                """
                insert into np_project_events(project_id, event_type, detail)
                values (%s, %s, %s::jsonb)
                """,
                (project_id, event_type, json.dumps(detail or {})),
            )
        if architecture is not None and (event_type or "") in SNAPSHOT_EVENT_TYPES:
            if _should_snapshot(conn, project_id, event_type or "project-snapshot"):
                conn.execute(
                    """
                    insert into np_project_snapshots(project_id, label, event_type, architecture)
                    values (%s, %s, %s, %s::jsonb)
                    """,
                    (
                        project_id,
                        _snapshot_label(event_type or "project-snapshot", architecture),
                        event_type or "project-snapshot",
                        json.dumps(architecture),
                    ),
                )
                _prune_autosave_snapshots(conn, project_id)


def rename_customer(*, old_slug: str, new_slug: str, new_display_name: str, new_path: str) -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        conn.execute(
            """
            update np_customers
            set slug = %s, display_name = %s, path = %s, updated_at = now()
            where slug = %s
            """,
            (new_slug, new_display_name, new_path, old_slug),
        )
        rows = conn.execute(
            "select project_slug, path from np_projects where customer_slug = %s",
            (new_slug,),
        ).fetchall()
        for row in rows:
            project_slug, project_path = row
            conn.execute(
                """
                update np_projects
                set id = %s, path = %s, updated_at = now()
                where customer_slug = %s and project_slug = %s
                """,
                (f"{new_slug}/{project_slug}", project_path.replace(old_slug, new_slug, 1), new_slug, project_slug),
            )


def rename_project_record(*, old_id: str, customer_slug: str, new_project_slug: str, new_display_name: str, new_path: str) -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        conn.execute(
            """
            update np_projects
            set id = %s, project_slug = %s, display_name = %s, path = %s, updated_at = now()
            where id = %s
            """,
            (f"{customer_slug}/{new_project_slug}", new_project_slug, new_display_name, new_path, old_id),
        )


def delete_customer(customer_slug: str) -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        conn.execute("delete from np_customers where slug = %s", (customer_slug,))


def delete_project_record(project_id: str) -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        conn.execute("delete from np_projects where id = %s", (project_id,))


def project_activity(project_id: str, *, limit: int = 12) -> dict[str, Any] | None:
    """Return persisted project metadata and recent events for *project_id*."""
    if not is_enabled():
        return None
    with _connect() as conn:
        project = conn.execute(
            """
            select id, customer_slug, project_slug, display_name, path,
                   has_architecture, created_at::text, updated_at::text
            from np_projects
            where id = %s
            """,
            (project_id,),
        ).fetchone()
        if not project:
            return None
        events = conn.execute(
            """
            select event_type, detail, created_at::text
            from np_project_events
            where project_id = %s
            order by created_at desc, id desc
            limit %s
            """,
            (project_id, limit),
        ).fetchall()
        snapshots = _project_snapshots(conn, project_id, limit=limit)
        retention_counts = _snapshot_counts(conn, project_id)
    return {
        "id": project[0],
        "customer": project[1],
        "project": project[2],
        "displayName": project[3],
        "path": project[4],
        "hasArchitecture": project[5],
        "createdAt": project[6],
        "updatedAt": project[7],
        "events": [
            {
                "eventType": row[0],
                "detail": row[1] if isinstance(row[1], dict) else {},
                "createdAt": row[2],
            }
            for row in events
        ],
        "snapshots": snapshots,
        "retention": {**retention_policy(), **retention_counts},
    }


def retention_policy() -> dict[str, Any]:
    return {
        "autosaveLimit": AUTOSAVE_RETENTION_LIMIT,
        "milestonesRetained": True,
        "description": (
            f"Routine autosave restore points are capped at {AUTOSAVE_RETENTION_LIMIT} per project; "
            "milestone restore points are retained."
        ),
    }


def project_snapshot(project_id: str, snapshot_id: int) -> dict[str, Any] | None:
    """Return one persisted restore point for *project_id*."""
    if not is_enabled():
        return None
    with _connect() as conn:
        row = conn.execute(
            """
            select id, label, event_type, architecture, created_at::text
            from np_project_snapshots
            where project_id = %s and id = %s
            """,
            (project_id, snapshot_id),
        ).fetchone()
    if not row:
        return None
    architecture = row[3]
    if isinstance(architecture, str):
        architecture = json.loads(architecture)
    return {
        "id": row[0],
        "label": row[1],
        "eventType": row[2],
        "architecture": architecture,
        "createdAt": row[4],
    }


def project_identity(project_path: Path, projects_root: Path) -> tuple[str, str]:
    rel = project_path.resolve().relative_to(projects_root.resolve())
    parts = rel.parts
    customer = parts[0] if parts else "customer"
    project = parts[1] if len(parts) > 1 else "default"
    return customer, project


def sync_project_path(project_path: Path, projects_root: Path, *, event_type: str | None = None) -> None:
    if not is_enabled() or not project_path.exists():
        return
    customer, project = project_identity(project_path, projects_root)
    arch_path = project_path / "architecture.json"
    architecture = None
    if arch_path.exists():
        architecture = json.loads(arch_path.read_text(encoding="utf-8"))
    upsert_project(
        customer=customer,
        project=project,
        path=str(project_path),
        architecture=architecture,
        event_type=event_type,
        detail={"syncedAt": datetime.now(timezone.utc).isoformat()},
    )


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install psycopg[binary] to enable Postgres persistence") from exc
    return psycopg.connect(database_url(), connect_timeout=3)


def _should_snapshot(conn, project_id: str, event_type: str) -> bool:
    if event_type != "autosave":
        return True
    row = conn.execute(
        """
        select created_at
        from np_project_snapshots
        where project_id = %s and event_type = 'autosave'
        order by created_at desc, id desc
        limit 1
        """,
        (project_id,),
    ).fetchone()
    if not row:
        return True
    latest = row[0]
    if isinstance(latest, str):
        latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - latest).total_seconds() >= 120


def _snapshot_label(event_type: str, architecture: dict) -> str:
    project_name = architecture.get("project", {}).get("name") or "Architecture"
    if event_type == "diagram-quality":
        review = architecture.get("quality", {}).get("lastReview", {})
        score = review.get("score")
        if score is not None:
            return f"Quality {score}/100 - {project_name}"
    return f"{event_type.replace('-', ' ').title()} - {project_name}"


def _project_snapshots(conn, project_id: str, *, limit: int = 12) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select id, label, event_type,
               architecture #>> '{quality,lastReview,score}' as quality_score,
               created_at::text
        from np_project_snapshots
        where project_id = %s
        order by created_at desc, id desc
        limit %s
        """,
        (project_id, limit),
    ).fetchall()
    return [
        {
            "id": row[0],
            "label": row[1],
            "eventType": row[2],
            "qualityScore": _coerce_float(row[3]),
            "createdAt": row[4],
        }
        for row in rows
    ]


def _snapshot_counts(conn, project_id: str) -> dict[str, int]:
    rows = conn.execute(
        """
        select
          count(*) filter (where event_type = 'autosave') as autosaves,
          count(*) filter (where event_type <> 'autosave') as milestones,
          count(*) as total
        from np_project_snapshots
        where project_id = %s
        """,
        (project_id,),
    ).fetchone()
    return {
        "autosaveCount": int(rows[0] or 0),
        "milestoneCount": int(rows[1] or 0),
        "totalCount": int(rows[2] or 0),
    }


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prune_autosave_snapshots(conn, project_id: str) -> int:
    if AUTOSAVE_RETENTION_LIMIT < 1:
        return 0
    result = conn.execute(
        """
        delete from np_project_snapshots
        where id in (
          select id
          from np_project_snapshots
          where project_id = %s and event_type = 'autosave'
          order by created_at desc, id desc
          offset %s
        )
        """,
        (project_id, AUTOSAVE_RETENTION_LIMIT),
    )
    return result.rowcount or 0
