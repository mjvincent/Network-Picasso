# Containerized Network Picasso

Network Picasso can run either with the local developer workflow or with Docker Compose.
The Compose defaults intentionally avoid ports used by the other local RVTools stacks:

- API: host `8788` to container `8787`
- UI: host `5174` to container `5173`
- Postgres: host `55432` to container `5432`
- Compose project/network/container names are prefixed with `network-picasso`

## Start

From the repository root, run one command:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:5174
```

This is the recommended entry point for end users. It starts the UI, API, and Postgres
persistence together, so Project Activity and restore points work immediately.

For day-to-day use after the first build, the same command is still fine. Docker will reuse cached
layers unless the source or dependencies changed.

## Override Ports

```bash
NETWORK_PICASSO_API_PORT=8790 NETWORK_PICASSO_UI_PORT=5176 NETWORK_PICASSO_DB_PORT=55433 docker compose up --build
```

## Storage

The Compose stack mounts local folders so generated work remains available on the host:

- `./inputs:/app/inputs`
- `./outputs:/app/outputs`

Postgres stores durable metadata in the named Docker volume:

- `network-picasso_network_picasso_postgres`

The filesystem remains the easiest place to inspect generated project artifacts:

```text
inputs/projects/<customer>/<project>/architecture.json
inputs/projects/<customer>/<project>/uploads/
outputs/
```

Postgres stores a searchable project index, architecture JSON snapshots, and project events.
The API initializes its tables automatically at startup when
`NETWORK_PICASSO_DATABASE_URL` is set.

Routine autosave restore points are pruned per project while milestone restore points are kept.
The default autosave limit is `25`. Change it in **Settings > Restore retention** after startup,
or override the initial fallback with an environment variable:

```bash
NETWORK_PICASSO_AUTOSAVE_RETENTION=50 docker compose up --build
```

Check persistence health:

```bash
curl http://127.0.0.1:8788/api/persistence/status
```

Re-index existing filesystem projects into Postgres:

```bash
curl -X POST http://127.0.0.1:8788/api/persistence/sync
```

Use `docker compose down` to stop the app while preserving the Postgres volume. Use
`docker compose down -v` only when you intentionally want to delete persisted database state.

## Ollama And MCP Notes

Ollama is not included in the first Compose stack. The app can still use a host Ollama service
from the local developer workflow. A later Compose profile can add Ollama, but model storage
and GPU access should be configured per workstation.

The Draw.io MCP editor is also left host-local for now because it works against a live browser
tab at `localhost:4000`. Containerizing it is possible, but the browser/editor connection should
be tested separately before making it the default path.

The API container reaches the host MCP editor through:

```text
NETWORK_PICASSO_MCP_BASE_URL=http://host.docker.internal:4000
```

If you run Docker on a platform that does not support `host.docker.internal`, override that
environment variable with the host address your containers can reach.
