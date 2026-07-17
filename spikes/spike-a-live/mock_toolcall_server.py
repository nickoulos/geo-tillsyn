#!/usr/bin/env python3
"""Tool-aware OpenAI-compatible mock model for the A-live MCP verification.

Extends eneo's e2e mock (deterministic, stdlib-only, :8200) with one behaviour:
when the request carries `tools` and no tool result yet, it answers with a
`tool_calls` completion targeting the geo-tillsyn analysis tool; once a
role="tool" message is present it produces a final answer quoting the result.
This proves Eneo chat -> MCP client -> geo-tillsyn-mcp -> answer-with-citations
end-to-end with zero real LLM calls.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("MOCK_PORT", "8200"))
REPLY = os.environ.get("MOCK_REPLY", "A-live mock: inget verktyg tillgängligt, svarar direkt.")
TOOL_ARGS = os.environ.get(
    "MOCK_TOOL_ARGS",
    '{"easting": 158140.4, "northing": 6918389.3, "radie_m": 120}',
)
PREFERRED_TOOL = os.environ.get("MOCK_PREFERRED_TOOL", "analysera")


def _tool_result_text(req: dict) -> str | None:
    for message in reversed(req.get("messages") or []):
        if isinstance(message, dict) and message.get("role") == "tool":
            content = message.get("content")
            if isinstance(content, list):
                content = " ".join(
                    str(i.get("text", "")) for i in content if isinstance(i, dict)
                )
            return str(content or "")
    return None


def _pick_tool(req: dict) -> str | None:
    tools = req.get("tools") or []
    names = [
        t.get("function", {}).get("name")
        for t in tools
        if isinstance(t, dict) and t.get("function", {}).get("name")
    ]
    if not names:
        return None
    for name in names:
        if PREFERRED_TOOL in name:
            return name
    return names[0]


def _final_answer(tool_text: str) -> str:
    try:
        data = json.loads(tool_text)
        traffar = data.get("traffar", [])
        rader = [
            f"Analys klar: {data.get('antal_byggnader', '?')} byggnader i området, "
            f"{data.get('antal_traffar', '?')} inom strandskyddszon."
        ]
        for t in traffar[:3]:
            rader.append(
                f"- {t.get('byggnad_id')}: {t.get('laege')}, uppförd {t.get('byggnads_ar')}, "
                f"dispens krävs idag: {t.get('dispens_kravs_idag')}"
            )
        if data.get("juridisk_not"):
            rader.append(data["juridisk_not"])
        return "\n".join(rader)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return f"Verktygssvar mottaget: {tool_text[:600]}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[mock-toolcall] {fmt % args}", flush=True)

    def do_GET(self):
        self._json(200, {"status": "ok"} if self.path.endswith("/health") else {"data": []})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) if length else b"{}")
        except json.JSONDecodeError:
            req = {}

        if not self.path.endswith("/chat/completions"):
            self._json(404, {"error": "not found"})
            return

        tool_text = _tool_result_text(req)
        tool_name = _pick_tool(req)
        if tool_text is not None:
            self._respond(req, content=_final_answer(tool_text))
        elif tool_name:
            print(f"[mock-toolcall] issuing tool_call: {tool_name}({TOOL_ARGS})", flush=True)
            self._respond(req, tool_call=(tool_name, TOOL_ARGS))
        else:
            self._respond(req, content=REPLY)

    def _respond(self, req: dict, content: str | None = None, tool_call=None):
        if req.get("stream"):
            self._stream(content, tool_call)
            return
        message: dict = {"role": "assistant", "content": content}
        finish = "stop"
        if tool_call:
            name, args = tool_call
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_geotillsyn_1",
                        "type": "function",
                        "function": {"name": name, "arguments": args},
                    }
                ],
            }
            finish = "tool_calls"
        self._json(
            200,
            {
                "id": "mock-toolcall",
                "object": "chat.completion",
                "model": req.get("model", "e2e-mock"),
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    def _stream(self, content: str | None, tool_call):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(_chunk({"role": "assistant"}))
        if tool_call:
            name, args = tool_call
            self.wfile.write(
                _chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_geotillsyn_1",
                                "type": "function",
                                "function": {"name": name, "arguments": ""},
                            }
                        ]
                    }
                )
            )
            self.wfile.write(
                _chunk(
                    {
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": args}}
                        ]
                    }
                )
            )
            self.wfile.write(_chunk({}, finish_reason="tool_calls"))
        else:
            self.wfile.write(_chunk({"content": content or ""}))
            self.wfile.write(_chunk({}, finish_reason="stop"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, status: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _chunk(delta: dict, finish_reason=None) -> bytes:
    payload = {
        "id": "mock-toolcall",
        "object": "chat.completion.chunk",
        "model": "e2e-mock",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload)}\n\n".encode()


if __name__ == "__main__":
    print(f"[mock-toolcall] listening on :{PORT}, tool args={TOOL_ARGS}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
