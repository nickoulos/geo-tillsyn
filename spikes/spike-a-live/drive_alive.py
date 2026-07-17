"""A-live driver: register geo-tillsyn-mcp in a running Eneo e2e stack and
prove chat -> MCP tool call -> citation end-to-end.

Run on the host (needs `requests`):
    python drive_alive.py [--base http://localhost:8124/api/v1]
                          [--mcp-url http://host.docker.internal:8464/mcp]

Assumes the e2e stack is up with the tool-aware mock model and that
seed_tool_support.py has flipped the mock model to supports_tool_calling=True.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import argparse
import json
import sys

import requests

EMAIL = "e2e@example.com"
PASSWORD = "E2ePassword1!"


def die(msg: str, response: requests.Response | None = None) -> None:
    print(f"FAIL: {msg}")
    if response is not None:
        print(f"  HTTP {response.status_code}: {response.text[:800]}")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8124/api/v1")
    parser.add_argument("--mcp-url", default="http://host.docker.internal:8464/mcp")
    parser.add_argument(
        "--fraga",
        default="Vad gäller för byggnaderna vid punkten E 158140, N 6918389 på Alnö?",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")

    s = requests.Session()

    # 1. Login (OAuth2 password form).
    r = s.post(
        f"{base}/users/login/token/",
        data={"username": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        die("login", r)
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("[1] inloggad som", EMAIL)

    # 2. Register the MCP server in the global catalog (idempotent by name).
    r = s.get(f"{base}/mcp-servers/", timeout=30)
    if r.status_code != 200:
        die("list mcp servers", r)
    existing = [
        i for i in r.json().get("items", []) if i.get("name") == "geo-tillsyn"
    ]
    if existing:
        server = existing[0]
        print("[2] geo-tillsyn redan registrerad:", server["id"])
    else:
        r = s.post(
            f"{base}/mcp-servers/",
            json={
                "name": "geo-tillsyn",
                "description": (
                    "Fall 7 strandskydd: REALITY x RULE -> spårbar dossier. "
                    "Systemet bedömer, handläggaren beslutar."
                ),
                "http_url": args.mcp_url,
                "http_auth_type": "none",
            },
            timeout=30,
        )
        if r.status_code not in (200, 201):
            die("create mcp server", r)
        print("[2] create-svar:", json.dumps(r.json(), ensure_ascii=False)[:400])
        r = s.get(f"{base}/mcp-servers/", timeout=30)
        skapade = [
            i for i in r.json().get("items", []) if i.get("name") == "geo-tillsyn"
        ]
        if not skapade:
            die("server saknas efter create", r)
        server = skapade[0]
        print("[2] registrerad:", server["id"])
    server_id = server["id"]

    # 3. Sync tools from the live server.
    r = s.post(f"{base}/mcp-servers/{server_id}/tools/sync/", timeout=60)
    if r.status_code != 200:
        die("tools sync", r)
    print("[3] tools sync:", json.dumps(r.json())[:300])

    r = s.get(f"{base}/mcp-servers/{server_id}/tools/", timeout=30)
    tools = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
    print("[3] tools:", [t.get("name") for t in tools])

    # 4. Enable for tenant.
    r = s.post(f"{base}/mcp-servers/settings/{server_id}/", json={}, timeout=30)
    if r.status_code not in (200, 201):
        print("  (enable settings:", r.status_code, r.text[:200], ")")
    else:
        print("[4] aktiverad för tenant")

    # 5. Create a space and attach the MCP server.
    r = s.post(f"{base}/spaces/", json={"name": "Geo-Tillsyn A-live"}, timeout=30)
    if r.status_code not in (200, 201):
        die("create space", r)
    space = r.json()
    space_id = space["id"]
    print("[5] space:", space_id)

    patch = {"mcp_servers": [{"id": server_id}]}
    r = s.patch(f"{base}/spaces/{space_id}/", json=patch, timeout=30)
    if r.status_code != 200:
        die("attach mcp server to space", r)
    print("[5] mcp_servers i space:", [m.get("name") for m in r.json().get("mcp_servers", [])])

    # 6. Create an assistant in the space.
    r = s.post(
        f"{base}/spaces/{space_id}/applications/assistants/",
        json={"name": "Geo-Tillsyn"},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        die("create assistant", r)
    assistant = r.json()
    assistant_id = assistant["id"]
    print("[6] assistant:", assistant_id)

    # The assistant must itself select the MCP servers made available by the
    # space, AND explicitly enable each tool — tools are OFF by default per
    # assistant (space_repo: "tools must be explicitly enabled at assistant
    # level"). Governance by design, easy to miss.
    r = s.post(
        f"{base}/assistants/{assistant_id}/",
        json={
            "mcp_servers": [{"id": server_id}],
            "mcp_tools": [
                {"tool_id": t["id"], "is_enabled": True} for t in tools
            ],
        },
        timeout=30,
    )
    if r.status_code != 200:
        die("attach mcp server + enable tools on assistant", r)
    print(
        "[6] assistantens mcp_servers:",
        [m.get("name") for m in r.json().get("mcp_servers", [])],
    )

    # 7. Ask. The tool-aware mock model will fire the MCP tool call.
    r = s.post(
        f"{base}/assistants/{assistant_id}/sessions/",
        json={"question": args.fraga, "stream": False},
        timeout=180,
    )
    if r.status_code != 200:
        die("ask", r)
    svar = r.json()
    print("\n[7] SVAR:")
    print(json.dumps(svar, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
