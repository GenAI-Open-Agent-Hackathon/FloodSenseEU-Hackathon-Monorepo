"""Nightshift live check against a fake OpenAI-compatible runtime on 127.0.0.1."""

from __future__ import annotations

import io
import json
import socket
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nightshift_check import load_values, main, parse_env_file  # noqa: E402

TOKEN = "fakefakefakefake"
FAST = "nvidia/nemotron-3.5-lightning-30b-a3b"
DEEP = "nvidia/nemotron-3-super-120b-a12b"
EMBED = "nvidia/llama-nemotron-embed-1b-v2"


class FakeRuntime(BaseHTTPRequestHandler):
    """Behaviour comes from self.server.scenario; requests land in self.server.seen."""

    def log_message(self, *_args: object) -> None:  # keep test output clean
        pass

    def _send(self, status: int, payload: object) -> None:
        raw = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authorised(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {self.server.scenario.get('token', TOKEN)}":
            # A careless runtime echoes what it got. The check must scrub it.
            self._send(401, {"error": f"unauthorized: {auth}"})
            return False
        return True

    def _record(self, body: dict | None) -> None:
        self.server.seen.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": body,
            }
        )

    def do_GET(self) -> None:  # noqa: N802
        self._record(None)
        if not self._authorised():
            return
        if self.path == "/v1/models":
            ids = self.server.scenario.get("models", [FAST, DEEP, EMBED])
            self._send(200, {"object": "list", "data": [{"id": i} for i in ids]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        self._record(body)
        if not self._authorised():
            return
        scenario = self.server.scenario
        if self.path == "/v1/chat/completions":
            if "response_format" in body and not scenario.get("json_mode", True):
                self._send(400, {"error": "response_format is not supported"})
                return
            lane = "fast" if body["model"] == FAST else "deep"
            content = scenario.get("reply", json.dumps({"ok": True, "lane": lane}))
            # Routing can answer a lane with another model, as Nightshift AUTO did live.
            answered = scenario.get("answered_by", {}).get(body["model"], body["model"])
            self._send(
                200,
                {
                    "model": answered,
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 31, "completion_tokens": 9},
                },
            )
        elif self.path == "/v1/embeddings":
            if not scenario.get("embeddings", True):
                self._send(404, {"error": {"message": "not_found"}})
                return
            self._send(200, {"data": [{"embedding": [0.1] * 2048}], "model": body["model"]})
        else:
            self._send(404, {"error": "not found"})


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class NightshiftCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRuntime)
        self.server.scenario = {}
        self.server.seen = []
        threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.base = f"http://127.0.0.1:{self.server.server_port}/v1"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def write_env(self, **overrides: str) -> Path:
        values = {
            "METERLESS_BASE_URL": self.base,
            "METERLESS_APP": "floodsense-eu",
            "METERLESS_SCOPE": "user",
            "METERLESS_RUNTIME_TOKEN": TOKEN,
            "MODEL_FAST": FAST,
            "MODEL_DEEP": DEEP,
            "LLM_TIMEOUT_S": "5",
        }
        values.update(overrides)
        path = Path(self.tmp.name) / ".env"
        path.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
        return path

    def run_check(self, *extra: str, env: Path | None = None) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--env", str(env or self.write_env()), *extra], environ={})
        return code, out.getvalue() + err.getvalue()

    def test_all_checks_pass_and_token_never_printed(self) -> None:
        code, text = self.run_check()
        self.assertEqual(code, 0, text)
        self.assertIn("**Result: PASS** (3/3 required checks passed)", text)
        self.assertIn("| fast lane | PASS |", text)
        self.assertIn("| deep lane | PASS |", text)
        self.assertIn(f"`{EMBED}`, 2048 dims", text)
        self.assertNotIn(TOKEN, text)
        for req in self.server.seen:
            self.assertEqual(req["headers"]["authorization"], f"Bearer {TOKEN}")
            self.assertEqual(req["headers"]["meterless-app"], "floodsense-eu")
            self.assertEqual(req["headers"]["meterless-scope"], "user")
        chats = [r["body"] for r in self.server.seen if r["path"] == "/v1/chat/completions"]
        self.assertEqual([c["model"] for c in chats], [FAST, DEEP])
        for chat in chats:
            self.assertEqual(chat["temperature"], 0.1)
            self.assertEqual(chat["chat_template_kwargs"], {"enable_thinking": False})
            self.assertEqual(chat["response_format"], {"type": "json_object"})

    def test_missing_pinned_model_fails(self) -> None:
        self.server.scenario["models"] = [FAST]
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 1)
        self.assertIn(f"missing `{DEEP}`", text)
        self.assertIn("**Result: FAIL**", text)

    def test_json_mode_rejected_falls_back_like_the_agents_client(self) -> None:
        self.server.scenario["json_mode"] = False
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 0, text)
        self.assertIn("JSON mode off", text)
        chats = [r["body"] for r in self.server.seen if r["path"] == "/v1/chat/completions"]
        self.assertEqual(len(chats), 4)
        self.assertIn("response_format", chats[0])
        self.assertNotIn("response_format", chats[1])

    def test_wrong_token_fails_and_echoed_token_is_scrubbed(self) -> None:
        self.server.scenario["token"] = "the-right-one"
        code, text = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", text)
        self.assertIn("METERLESS_RUNTIME_TOKEN", text)
        self.assertIn("not run", text)
        self.assertNotIn(TOKEN, text)
        self.assertEqual(len(self.server.seen), 1)

    def test_no_runtime_listening(self) -> None:
        env = self.write_env(METERLESS_BASE_URL=f"http://127.0.0.1:{free_port()}/v1")
        code, text = self.run_check(env=env)
        self.assertEqual(code, 1)
        self.assertIn("Is Nightshift running?", text)

    def test_fenced_json_reply_passes(self) -> None:
        self.server.scenario["reply"] = '```json\n{"ok": true}\n```'
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 0, text)

    def test_prose_reply_fails(self) -> None:
        self.server.scenario["reply"] = "Sure! Everything looks fine."
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 1)
        self.assertIn("Reply is not JSON", text)

    def test_no_embedding_model_is_skipped_not_failed(self) -> None:
        self.server.scenario["models"] = [FAST, DEEP]
        code, text = self.run_check()
        self.assertEqual(code, 0, text)
        self.assertIn("| embeddings (optional) | SKIP | no embedding model listed", text)

    def test_lane_answered_by_another_model_is_a_warning(self) -> None:
        self.server.scenario["answered_by"] = {DEEP: FAST}
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 0, text)
        self.assertIn("| fast lane | PASS |", text)
        self.assertIn("| deep lane | WARN |", text)
        self.assertIn(f"Pin not honoured: asked for `{DEEP}`, answered by `{FAST}`", text)
        self.assertIn("**Result: PASS with 1 warning**", text)

    def test_routing_modes_answered_by_real_models_pass(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answered_by"] = {"meterless/fast": FAST, "meterless/deep": DEEP}
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn(f"| fast lane | PASS | `{FAST}`", text)
        self.assertIn("routed by `meterless/deep`", text)
        self.assertIn("**Result: PASS** (3/3 required checks passed)", text)

    def test_both_tiers_answered_by_one_model_is_a_warning(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answered_by"] = {"meterless/fast": DEEP, "meterless/deep": DEEP}
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn("| fast lane | WARN |", text)
        self.assertIn("tiers not separate", text)
        self.assertIn("**Result: PASS with 1 warning**", text)

    def test_listed_embedding_model_without_the_route(self) -> None:
        self.server.scenario["embeddings"] = False
        code, text = self.run_check()
        self.assertEqual(code, 0, text)
        self.assertIn("| embeddings (optional) | WARN |", text)
        self.assertIn("this runtime does not serve embeddings", text)
        self.assertNotIn("ends in /v1", text)
        self.assertIn("**Result: PASS** (3/3 required checks passed)", text)

    def test_config_problems_send_nothing(self) -> None:
        code, text = self.run_check(env=self.write_env(METERLESS_RUNTIME_TOKEN=""))
        self.assertEqual(code, 2)
        self.assertIn("METERLESS_RUNTIME_TOKEN is empty", text)
        docker_url = "http://host.docker.internal:8088/v1"
        code, text = self.run_check(env=self.write_env(METERLESS_BASE_URL=docker_url))
        self.assertEqual(code, 2)
        self.assertIn("127.0.0.1:8088", text)
        self.assertEqual(self.server.seen, [])

    def test_missing_env_file(self) -> None:
        code, text = self.run_check(env=Path(self.tmp.name) / "nope.env")
        self.assertEqual(code, 2)
        self.assertIn("init-env", text)

    def test_out_file_matches_report(self) -> None:
        out = Path(self.tmp.name) / "check.md"
        code, text = self.run_check("--no-embeddings", "--out", str(out))
        self.assertEqual(code, 0, text)
        saved = out.read_text(encoding="utf-8")
        self.assertIn("## Nightshift live check", saved)
        self.assertNotIn(TOKEN, saved)


class ParseEnvTest(unittest.TestCase):
    def test_comments_quotes_export_and_inline_comment(self) -> None:
        text = (
            "# comment\n\n"
            "export METERLESS_APP=floodsense-eu\n"
            'MODEL_FAST="nvidia/a"\n'
            "MODEL_DEEP='nvidia/b'\n"
            "LLM_TIMEOUT_S=90 # seconds\n"
            "METERLESS_RUNTIME_TOKEN=\n"
            "not a pair\n"
        )
        self.assertEqual(
            parse_env_file(text),
            {
                "METERLESS_APP": "floodsense-eu",
                "MODEL_FAST": "nvidia/a",
                "MODEL_DEEP": "nvidia/b",
                "LLM_TIMEOUT_S": "90",
                "METERLESS_RUNTIME_TOKEN": "",
            },
        )

    def test_byte_order_mark_and_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("METERLESS_APP=from-file\nMODEL_FAST=file-fast\n", encoding="utf-8-sig")
            values = load_values(path, {"MODEL_FAST": "env-fast", "METERLESS_APP": ""})
        self.assertEqual(values["METERLESS_APP"], "from-file")
        self.assertEqual(values["MODEL_FAST"], "env-fast")


if __name__ == "__main__":
    unittest.main()
