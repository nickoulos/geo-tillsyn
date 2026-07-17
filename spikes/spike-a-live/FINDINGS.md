# Spike A-live — Eneo → geo-tillsyn-mcp verified end-to-end (2026-07-17)

> Closes the "Live verification checklist" from `docs/spike-a-eneo-findings.md`.
> Zero real LLM calls: the deterministic tool-aware mock stands in for the model.

## Proven chain

Eneo chat (`POST /assistants/{id}/sessions/`, stream) → mock LLM issues
`tool_calls` → Eneo MCP client → **geo-tillsyn-mcp over streamable HTTP**
(`host.docker.internal:8464/mcp`) → live `karta.sundsvall.se` → answer with
real data, tool call persisted on the session:

```json
{"server_name": "geo-tillsyn", "tool_name": "analysera_strandskydd_vid_punkt",
 "arguments": {"easting": 158140.4, "northing": 6918389.3, "radie_m": 120},
 "approved": true, "result_status": "succeeded",
 "mcp_tool_name": "geo-tillsyn__analysera_strandskydd_vid_punkt"}
```

Answer contained: 57 byggnader / 27 inom strandskyddszon, protagonist
`bal_byggnad_yta.38472` (uppförd 2014, dispens krävs) + juridisk not
(MÖD 2021:6 / 2017:16).

## How to reproduce

1. `backend/.env` = copy of `.env.template`. Build devcontainer image + venv
   volume once (see repo history / Taskfile).
2. From the eneo repo root:
   `docker compose -f docker-compose.e2e.yml -f ../geo-tillsyn/spikes/spike-a-live/docker-compose.mcp-live.yml up -d --wait`
3. `docker compose ... exec e2e-backend bash -lc 'PATH=/workspace/backend/.venv/bin:$PATH python /spike/seed_tool_support.py'`
4. Host: `geo-tillsyn-mcp --host 0.0.0.0 --port 8464`
5. Host: `python drive_alive.py` (registers, syncs, enables, wires space +
   assistant + **assistant-level tool enablement**, asks).

## Gotchas discovered (each cost a debug round)

1. **FastMCP DNS-rebinding 421.** FastMCP auto-enables Host-header validation
   with a localhost-only allowlist; requests from containers arrive with
   `Host: host.docker.internal:8464` → `421 Misdirected Request`. Fixed in
   `geo_tillsyn/server.py` by passing explicit `TransportSecuritySettings`
   (protection kept, allowlist widened).
2. **Eneo bug — assistant-attached MCP servers expose zero tools.** Both
   `assistant_repo._options()` and `space_repo._get_assistants()` do
   `selectinload(Assistants.mcp_servers)` **without** chaining
   `.selectinload(MCPServers.tools)`; `MCPServerMapper.to_entity` then silently
   maps `tools=[]` and the proxy builds an empty registry
   ("[MCPProxy] Built registry with 0 tools from 1 servers"). Patched locally
   in our eneo clone (2 one-line fixes) — **candidate upstream PR to
   eneo-ai/eneo**; also worth mentioning in the anbud (we run Eneo deeply
   enough to fix its MCP wiring).
3. **Tools are OFF by default per assistant** (`space_repo`: "tools must be
   explicitly enabled at assistant level") — governance by design. Wiring
   order that works: register server → sync tools → enable for tenant
   (`POST /mcp-servers/settings/{id}/`) → enable each tool for tenant
   (`PUT /mcp-servers/settings/tools/{tool_id}/`) → attach server to space
   (PATCH `mcp_servers`) → attach to assistant **and** send
   `mcp_tools: [{tool_id, is_enabled: true}]`.
4. **e2e seed's mock model has `supports_tool_calling=False`** — flip it with
   `seed_tool_support.py`, and the stock mock server never emits `tool_calls`;
   `mock_toolcall_server.py` here replaces it (OpenAI-compatible, stream +
   non-stream, deterministic).
5. **Non-stream asks don't persist `tool_calls`/references** — use
   `stream: true` (as the real frontend does) for the traceability record.
6. Compose overlay files resolve relative volume paths against the **project
   directory** (first `-f` file), not the overlay's own directory — hence
   absolute paths in `docker-compose.mcp-live.yml`.

## Not covered here

- Real LLM provider in Eneo (model choice/tenant config — team decision).
- The Eneo frontend UI (bun/SvelteKit) — API-level verification only.
- `mcp_tool_references` (resource-link citations) stayed empty with the mock;
  re-check with a real model and with tools that return MCP resources.
