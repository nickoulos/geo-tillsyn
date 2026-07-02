# Spike A — Eneo + MCP: findings

> Working document (English during development). Based on source inspection of
> `eneo-ai/eneo` (shallow clone 2026-07-02, in `../eneo`). Decision derived from
> this: [ADR-001](adr/001-reasoning-in-eneo.md).

## Verdict: the bid's core bet holds

Eneo has **first-class, mature MCP support** — better than we assumed when
writing the concept. Evidence in source:

| Area | Evidence |
| --- | --- |
| Backend domain module | `backend/src/eneo/mcp_servers/` (DDD: application/domain/infrastructure) |
| Persistence | `mcp_server_table.py`, `mcp_tool_references_table.py`, `chat_session_mcp_state_table.py` + 8 alembic migrations (latest 2026-06) |
| Admin UI | `frontend/.../admin/mcp-servers/` (register, enable, tools panel, delete) |
| Per-space wiring | `spaces/[spaceId]/settings/SelectMCPServers.svelte` — MCP servers are selected per space; assistants in the space use them |
| Governance | `admin/personal-assistant/configuration/mcpPolicy.ts`, `McpRestrictionSection.svelte`; security classification per server (migration 2026-03) |
| Citations | `mcp_tool_references` links tool calls into answers — our "every claim has a source" requirement has native support |

## Hard constraints discovered

1. **Transport is Streamable HTTP only** (`mcp.client.streamable_http`; servers
   registered with `http_url`, `http_auth_type` default "none", optional
   schema-driven auth config). **No stdio.** All our MCP servers must run as
   HTTP services reachable from the Eneo backend container.
2. **Defensive size caps** in the MCP client: resource text blocks truncated at
   **8 kB** (meta 16 kB). Design rule: tools return compact JSON + references
   (WMS URLs, feature ids, key numbers) — never imagery or large GeoJSON.
3. Timeouts configurable via settings (`mcp_client_connect/list_tools/call_timeout_seconds`);
   SSE read timeout 300 s — fine for slow WMS chains if we stream progress.

## Consequence for mcp-ogc (basis for mcp-geodata)

`mcp-ogc` currently runs **stdio only** (`mcp.run()` in `src/mcp_ogc/server.py`).
Work item (small): add streamable-HTTP mode (FastMCP `transport="streamable-http"`)
+ Dockerfile → **good public v0.2.0 release** (strengthens the OSS story too).

## How to run Eneo locally (team, Sprint 1)

Three paths, from `../eneo`:

1. **DevContainer (recommended by Eneo docs):** open in VS Code → "Reopen in
   Container" → set `backend/.env` with an AI provider key → run backend
   (uv) + worker + frontend (bun). See `docs/INSTALLATION.md`.
2. **Manual dev:** `cd backend && docker compose up -d` (pgvector pg13 + redis
   only) + backend on host via `uv`, frontend via `bun`.
3. **Zero-API-key path: e2e stack.** `docker-compose.e2e.yml` brings up db,
   redis, backend AND a **mock model server** (`e2e/mock_model_server.py`,
   seeded via `e2e/seed.py`). Uses the devcontainer image
   (`eneo_devcontainer-eneo` — build it first from `.devcontainer/`). This lets
   us test MCP registration → tool call → citation end-to-end without any LLM
   key or cost. Strong candidate for our CI later.

## Live verification checklist (remaining, Sprint 1)

- [ ] Bring up Eneo (path 3 preferred), log in, open admin → MCP servers.
- [ ] Run mcp-ogc in streamable-HTTP mode, register its URL, verify the tools
      panel lists `get_capabilities`/`get_feature` etc.
- [ ] Attach to a space + assistant; in chat, trigger a tool call against
      `karta.sundsvall.se` ("vilka byggnader finns på fastighet X?").
- [ ] Confirm tool references/citations render in the answer; screenshot for
      the Friday demo + written deliverable.
- [ ] Note model-provider config for the prototype tenant (which LLM, EU/EES).
