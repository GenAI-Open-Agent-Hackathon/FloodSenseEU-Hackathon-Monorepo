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
DEEP = "nvidia/nemotron-3.5-super-vl-120b-a12b"
OTHER = "nvidia/some-other-model"
EMBED = "nvidia/llama-nemotron-embed-1b-v2"


class FakeRuntime(BaseHTTPRequestHandler):
    """Behaviour comes from self.server.scenario; requests land in self.server.seen."""

    def log_message(self, *_args: object) -> None:  # keep test output clean
        pass

    def _send(self, status: int, payload: object, headers: dict | None = None) -> None:
        raw = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authorised(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {self.server.scenario.get('token', TOKEN)}":
            # A careless runtime echoes what it got. The check must scrub it,
            # even where the report cuts the message short.
            pad = "x" * self.server.scenario.get("echo_pad", 0)
            self._send(401, {"error": f"unauthorized: {pad}{auth}"})
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
            model = body["model"]
            if model in scenario.get("reject", ()):
                self._send(400, {"error": f"unknown model {model}"})
                return
            if model in scenario.get("provider_error", ()):
                # Nightshift's shape when the cloud provider sends nothing back.
                self._send(
                    502,
                    {
                        "error": {
                            "message": f"/{model.split('/')[-1]}_empty_response",
                            "type": "api_error",
                            "code": "provider_error",
                            "param": None,
                            "meterless_detail": {"lane": "lightning", "provider": "nvidia"},
                        }
                    },
                )
                return
            if model in scenario.get("fail_first", ()) and model not in self.server.failed:
                # The upstream provider fails once, as NVIDIA did live with a 502.
                self.server.failed.add(model)
                self._send(502, {"error": "upstream error"})
                return
            lane = "fast" if model == FAST else "deep"
            content = scenario.get("reply", json.dumps({"ok": True, "lane": lane}))
            # Routing can answer a lane with another model, as Nightshift did live.
            # A list rotates per call, like a race between two lanes.
            routes = scenario.get("answered_by", {})
            answered = scenario.get("answer_all") or routes.get(model, model)
            if isinstance(answered, list):
                turn = self.server.turns.get(model, 0)
                self.server.turns[model] = turn + 1
                answered = answered[turn % len(answered)]
            reply = {
                "model": answered,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 31, "completion_tokens": 9},
            }
            extra = {}
            if scenario.get("details"):
                # What a runtime might add about the route: a receipt, the lanes that raced.
                extra = {"meterless-lane": "race:super-vl"}
                reply["meterless"] = {"raced": [FAST, DEEP], "winner": answered}
            self._send(200, reply, extra)
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
        self.server.turns = {}
        self.server.failed = set()
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
            "EXPECT_MODEL_FAST": FAST,
            "EXPECT_MODEL_DEEP": DEEP,
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
        self.assertIn(f"missing: `{DEEP}`", text)
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
        self.assertIn("| deep lane | WARN |", text)
        self.assertIn(f"Pin not honoured: asked for `{DEEP}`, answered by `{FAST}`", text)
        # Both tiers came back from one model, as in the live run at 15:29.
        self.assertIn("| fast lane | WARN |", text)
        self.assertIn(f"Fast and deep were both answered by `{FAST}`: tiers not separate.", text)
        self.assertIn("**Result: PASS with 2 warnings**", text)

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
        self.assertIn(f"Wrong model for the fast tier: it should be `{FAST}`", text)
        self.assertIn("tiers not separate", text)
        self.assertIn("| deep lane | PASS |", text)
        self.assertIn("**Result: PASS with 1 warning**", text)

    def test_listed_embedding_model_without_the_route(self) -> None:
        self.server.scenario["embeddings"] = False
        code, text = self.run_check()
        self.assertEqual(code, 0, text)
        self.assertIn("| embeddings (optional) | WARN |", text)
        self.assertIn("a lane with the embed duty", text)
        self.assertNotIn("ends in /v1", text)
        self.assertIn("**Result: PASS** (3/3 required checks passed)", text)

    def test_config_problems_send_nothing(self) -> None:
        code, text = self.run_check(env=self.write_env(METERLESS_RUNTIME_TOKEN=""))
        self.assertEqual(code, 2)
        self.assertIn("METERLESS_RUNTIME_TOKEN is empty", text)
        docker_url = "http://host.docker.internal:8088/v1"
        code, text = self.run_check(env=self.write_env(METERLESS_BASE_URL=docker_url))
        self.assertEqual(code, 2)
        self.assertIn("127.0.0.1 URL from the root .env.example", text)
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

    def chats(self) -> list[str]:
        return [r["body"]["model"] for r in self.server.seen if r["path"] == "/v1/chat/completions"]

    def test_wrong_model_for_a_tier_is_a_warning(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answered_by"] = {"meterless/fast": OTHER, "meterless/deep": DEEP}
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn(f"| fast lane | WARN | `{OTHER}`", text)
        self.assertIn(f"it should be `{FAST}`. Run with --probe", text)
        self.assertIn("| deep lane | PASS |", text)
        self.assertNotIn("tiers not separate", text)

    def test_expect_any_accepts_whichever_model_answers(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answered_by"] = {"meterless/fast": OTHER, "meterless/deep": DEEP}
        env = self.write_env(
            MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep", EXPECT_MODEL_FAST="any"
        )
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn(f"| fast lane | PASS | `{OTHER}`", text)
        self.assertIn("- Wanted: fast `any`", text)

    def test_unlisted_composed_routing_mode_warns_instead_of_failing(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep", FAST, DEEP]
        self.server.scenario["answered_by"] = {"meterless/text.fast": FAST, "meterless/deep": DEEP}
        env = self.write_env(MODEL_FAST="meterless/text.fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn("| GET /models | WARN |", text)
        self.assertIn("composed routing modes can still route: `meterless/text.fast`", text)
        self.assertIn("Routing modes listed: `meterless/fast`, `meterless/deep` |", text)
        self.assertIn("| fast lane | PASS |", text)

    def test_probe_suggests_one_reliable_id_per_tier(self) -> None:
        self.server.scenario["models"] = [
            "meterless/auto",
            "meterless/fast",
            "meterless/deep",
            "meterless/local",
            "meterless/image",
            "meterless/embed",
            FAST,
            DEEP,
        ]
        self.server.scenario["answered_by"] = {
            "meterless/fast": [DEEP, FAST, DEEP],  # a race: not reliable
            "meterless/text.fast": FAST,
            "meterless/deep": DEEP,
            "meterless/auto": DEEP,
        }
        self.server.scenario["reject"] = ["meterless/vision.fast"]
        self.server.scenario["fail_first"] = ["meterless/deep"]
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--probe", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn("## Nightshift routing probe", text)
        self.assertIn(f"| `meterless/fast` | yes | `{DEEP}` 2/3, `{FAST}` 1/3 |", text)
        self.assertIn(f"| `meterless/text.fast` | no | `{FAST}` 3/3 |", text)
        self.assertIn(
            "| `meterless/vision.fast` | no | (HTTP 400) 1/1; 2 rounds skipped | - |",
            text,
        )
        self.assertIn("### Rounds", text)
        self.assertIn("### Skipped", text)
        self.assertIn("`meterless/local`", text)
        self.assertIn("`meterless/embed`", text)
        # One upstream 502 neither stops the rounds nor disqualifies the route.
        self.assertIn(f"| `meterless/deep` | yes | `{DEEP}` 2/3, (HTTP 502) 1/3 |", text)
        self.assertIn("| `meterless/judge` | no |", text)
        self.assertIn("MODEL_FAST=meterless/text.fast\nMODEL_DEEP=meterless/deep", text)
        self.assertIn("**Result: every tier has a reliable id**", text)
        sent = self.chats()
        self.assertEqual(sent.count("meterless/vision.fast"), 1)
        self.assertEqual(sent.count("meterless/deep"), 3)
        for skipped in ("meterless/local", "meterless/image", "meterless/embed"):
            self.assertNotIn(skipped, sent)
        self.assertNotIn(TOKEN, text)

    def test_probe_reports_a_tier_nothing_reaches(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep", FAST, DEEP]
        self.server.scenario["answer_all"] = DEEP
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--probe", "--probe-rounds", "2", env=env)
        self.assertEqual(code, 1, text)
        self.assertIn(f"**Fast: no id reached `{FAST}` every time.**", text)
        self.assertIn("MODEL_DEEP=meterless/deep", text)
        self.assertNotIn("MODEL_FAST=", text)
        self.assertIn("**Result: 1 tier without a reliable id**", text)

    def test_probe_with_a_wrong_token_sends_no_chat(self) -> None:
        self.server.scenario["token"] = "the-right-one"
        code, text = self.run_check("--probe")
        self.assertEqual(code, 1)
        self.assertIn("## Nightshift routing probe", text)
        self.assertIn("### Rounds", text)
        self.assertIn("Skipped. /models gave no list, so no rounds were sent.", text)
        self.assertIn("### Skipped", text)
        self.assertIn("Not evaluated. The probe stopped before choosing ids.", text)
        self.assertIn("**Result: probe not run**", text)
        self.assertEqual(self.chats(), [])
        self.assertNotIn(TOKEN, text)

    def test_defaults_expect_super_vl_on_both_tiers(self) -> None:
        # Nightshift answers both tiers with Super VL 120B, the faster and stronger lane.
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answer_all"] = DEEP
        env = self.write_env(
            MODEL_FAST="meterless/fast",
            MODEL_DEEP="meterless/deep",
            EXPECT_MODEL_FAST="",
            EXPECT_MODEL_DEEP="",
        )
        code, text = self.run_check("--no-embeddings", env=env)
        self.assertEqual(code, 0, text)
        self.assertIn(f"- Wanted: fast `{DEEP}`, deep `{DEEP}`", text)
        self.assertIn("| fast lane | PASS |", text)
        self.assertIn("| deep lane | PASS |", text)
        self.assertNotIn("tiers not separate", text)
        self.assertIn("**Result: PASS** (3/3 required checks passed)", text)

    def test_token_cut_short_in_an_error_is_still_scrubbed(self) -> None:
        # The report keeps 137 characters of a server error. Put the token
        # across that cut: no piece of it may reach the report.
        self.server.scenario["token"] = "the-right-one"
        self.server.scenario["echo_pad"] = 98
        code, text = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", text)
        for size in range(4, len(TOKEN) + 1):
            self.assertNotIn(TOKEN[:size], text, size)

    def test_probe_lists_routing_details_the_runtime_returns(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        self.server.scenario["answer_all"] = DEEP
        self.server.scenario["details"] = True
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--probe", "--probe-rounds", "1", env=env)
        self.assertIn("**Runtime details**", text)
        self.assertIn("`meterless-lane` = race:super-vl", text)
        self.assertIn(f'`meterless` = {{"raced":["{FAST}","{DEEP}"]', text)

    def test_probe_says_when_there_are_no_routing_details(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--probe", "--probe-rounds", "1", env=env)
        self.assertIn("Nightshift returned no routing details beyond the model name.", text)

    def test_provider_error_is_shown_in_full(self) -> None:
        # A long Nightshift error must not be cut before its own detail fields.
        self.server.scenario["provider_error"] = [FAST]
        code, text = self.run_check("--no-embeddings")
        self.assertEqual(code, 1)
        self.assertIn("| fast lane | FAIL |", text)
        self.assertIn("HTTP 502: message=/nemotron-3.5-lightning-30b-a3b_empty_response", text)
        self.assertIn("code=provider_error", text)
        self.assertIn('meterless_detail={"lane":"lightning","provider":"nvidia"}', text)
        self.assertNotIn("param=", text)

    def test_probe_rounds_outside_the_range_are_noted_not_silently_capped(self) -> None:
        self.server.scenario["models"] = ["meterless/fast", "meterless/deep"]
        env = self.write_env(MODEL_FAST="meterless/fast", MODEL_DEEP="meterless/deep")
        code, text = self.run_check("--probe", "--probe-rounds", "25", env=env)
        self.assertIn("note: --probe-rounds 25 is outside 1 to 10; using 10.", text)
        self.assertIn("Each id sent up to 10 times", text)

    def test_the_check_caps_the_reply_and_says_so(self) -> None:
        self.run_check("--no-embeddings")
        chats = [r["body"] for r in self.server.seen if r["path"] == "/v1/chat/completions"]
        self.assertEqual({c["max_tokens"] for c in chats}, {256})


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
