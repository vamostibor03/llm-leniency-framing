"""Exercise the real HTTP backend against a local fake OpenAI-compatible server (no key, no
network): request shape, JSON-mode fallback, token accounting, cost, caching."""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from leniency.config import load_config
from leniency.runner import run_experiment

ROOT = Path(__file__).resolve().parents[1]

# one reply that satisfies every phase's validator
UNIVERSAL = {
    "message": "Let's both keep our price at 9.", "price": 9, "secret_report": False, "public_report": True,
    "submit_r1": False, "submit_r2": True, "ruling": "guilty", "rationale": "explicit agreement",
    "agreement": "explicit", "agreed_price": 9, "silence_pact": False, "reasoning": "(9,9) pays 180.",
}


class _Handler(BaseHTTPRequestHandler):
    requests: list = []
    reject_json_mode_once = True

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append({"auth": self.headers.get("Authorization"), **body})
        if "response_format" in body and type(self).reject_json_mode_once:
            type(self).reject_json_mode_once = False
            self._send(400, {"error": {"message": "response_format is not supported by this model"}})
            return
        self._send(200, {
            "choices": [{"message": {"role": "assistant", "content": json.dumps(UNIVERSAL)}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 50},
        })

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):  # silence
        pass


@pytest.fixture()
def fake_server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    monkeypatch.setenv("LENIENCY_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    monkeypatch.setenv("LENIENCY_API_KEY", "test-key")
    _Handler.requests, _Handler.reject_json_mode_once = [], True
    yield _Handler
    srv.shutdown()


def test_http_backend_end_to_end(fake_server, tmp_path):
    cfg = load_config(ROOT / "configs" / "smoke.yaml")
    cfg.conditions = [c for c in cfg.conditions if c.name == "E2"]
    cfg.supergames, cfg.periods = 1, 2
    usage = asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    reqs = fake_server.requests
    assert reqs and all(r["auth"] == "Bearer test-key" for r in reqs)
    assert all(r["model"] == "openai/gpt-4.1-mini" for r in reqs)
    assert "response_format" in reqs[0]  # first call asks for JSON mode, gets a 400 ...
    assert all("response_format" not in r for r in reqs[1:])  # ... and it is never sent again
    t = usage["total"]
    # 2 periods x (4 chat + 2 price + 2 public + 1 authority + 1 classifier) = 20 calls
    assert t["calls"] == 20 and t["input_tokens"] == 20_000 and t["output_tokens"] == 1_000
    assert usage["cost_usd"] == pytest.approx(20_000 * 0.40e-6 + 1_000 * 1.60e-6)
    rows = [json.loads(l) for l in (tmp_path / "periods.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["price_a"] == 9 and rows[0]["authority_ruling"] == "guilty"
    # both firms file a public report, guilty, E2 -> F/2 each: 180 - 100 = 80
    assert rows[0]["report_type"] == "public" and rows[0]["reporters"] == "AB"
    assert rows[0]["fine_a"] == 100 and rows[0]["payoff_a"] == 80
    # re-run: everything comes from the cache, no new HTTP requests
    n = len(reqs)
    (tmp_path / "periods.jsonl").unlink()
    asyncio.run(run_experiment(cfg, tmp_path, quiet=True))
    assert len(fake_server.requests) == n
