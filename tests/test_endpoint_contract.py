"""Checks that judges use the injected LLM endpoint.

On TIRA, the endpoint reaches the judge exclusively through the task-provided
environment variables (OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_API_KEY); judge
code must route them into whatever LLM client it uses. This test launches a
local pretend endpoint that returns well-formed but useless answers and runs
each judge against it: the judge will not produce sensible output, but the
server records whether the judge contacted the injected endpoint with the
injected model. Judges that need no LLM (e.g. the naive example) pass by
completing successfully without any call.
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent


def _tracked_workflows():
    """Same discovery as test_examples: git-tracked judges/*/workflow.yml."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "judges/*/workflow.yml"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.split()
        if out:
            return [REPO / p for p in out]
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return sorted(REPO.glob("judges/*/workflow.yml"))


WORKFLOWS = _tracked_workflows()


def _uses_llm(workflow: Path) -> bool:
    """A judge declares `uses_llm: false` in its own workflow.yml when it makes
    no LLM calls; the endpoint-contact assertion is then expected to fail
    (xfail). strict=True keeps the declaration honest: when such a judge starts
    calling an LLM, the unexpected pass fails the suite until the declaration
    is removed. The workflow runner ignores the key."""
    import yaml
    return yaml.safe_load(workflow.read_text(encoding="utf-8")).get("uses_llm", True)


PARAMS = [
    w if _uses_llm(w) else pytest.param(w, marks=pytest.mark.xfail(
        reason="declares uses_llm: false — no endpoint contact expected", strict=True))
    for w in WORKFLOWS
]

KIDDIE_RESPONSES = REPO / "data" / "kiddie" / "runs" / "repgen"
KIDDIE_TOPICS = REPO / "data" / "kiddie" / "topics" / "kiddie-topics.jsonl"


class _RecordingEndpoint:
    """Minimal OpenAI-compatible /v1/chat/completions server that logs requests."""

    def __init__(self):
        self.hits = 0
        self.models_seen = set()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                try:
                    outer.models_seen.add(json.loads(body).get("model"))
                except Exception:
                    pass
                outer.hits += 1
                payload = json.dumps({
                    "id": "fake", "object": "chat.completion", "created": 0,
                    "model": "fake", "choices": [{"index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "1"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):  # /v1/models etc.
                payload = json.dumps({"object": "list", "data": [{"id": "test-model"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):  # keep pytest output clean
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def shutdown(self):
        self.server.shutdown()


@pytest.mark.parametrize("workflow", PARAMS, ids=lambda p: p.parent.name)
def test_judge_uses_injected_endpoint(workflow, tmp_path):
    endpoint = _RecordingEndpoint()
    env = dict(
        os.environ,
        OPENAI_BASE_URL=f"http://127.0.0.1:{endpoint.port}/v1",
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="test-model",
        CACHE_DIR=str(tmp_path / "cache"),   # fresh: cache hits must not mask the contact
        # keep LLM clients snappy against the fake endpoint
        MAX_ATTEMPTS="1", TIMEOUT_S="20", RPM="10000",
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "autojudge_base.cli", "run",
             "--workflow", str(workflow),
             "--rag-responses", str(KIDDIE_RESPONSES),
             "--rag-topics", str(KIDDIE_TOPICS),
             "--limit-topics", "1",
             "--out-dir", str(tmp_path / "out")],
            cwd=REPO, env=env, capture_output=True, text=True, timeout=300,
        )
    finally:
        endpoint.shutdown()

    if "Failed to load judge classes" in (proc.stderr or ""):
        pytest.skip("judge classes failed to import in a subprocess (environment "
                    "issue; import compatibility is covered by test_examples)")

    # Nonsense answers may legitimately make an LLM judge fail later; the
    # contract under test is only that it talked to the injected endpoint.
    assert endpoint.hits > 0, (
        "the judge never contacted the injected OPENAI_BASE_URL endpoint — it is "
        "probably not routing the task-provided environment variables into its "
        "LLM client (non-LLM judges belong in NON_LLM_JUDGES)\n"
        f"stderr tail: {proc.stderr[-2000:]}"
    )
    assert "test-model" in endpoint.models_seen, (
        f"the judge contacted the endpoint but requested {endpoint.models_seen} "
        "instead of the injected OPENAI_MODEL"
    )
