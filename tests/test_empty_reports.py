"""Judges must handle empty reports (responses: []).

Released runs may legitimately contain an empty report for a topic the system
skipped. Every judge must score such a report rather than crash or silently
drop the topic. This test feeds each judge (same git-tracked discovery as
test_examples) a single-run input whose one report is empty, and asserts the
produced eval.txt still includes that topic.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

KIDDIE_TOPICS = REPO / "data" / "kiddie" / "topics" / "kiddie-topics.jsonl"
EMPTY_TOPIC = "leaf"  # first kiddie topic; the run below leaves it unanswered


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


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.parent.name)
def test_judge_scores_empty_report(workflow, tmp_path):
    responses_dir = tmp_path / "runs"
    responses_dir.mkdir()
    (responses_dir / "empty-run.jsonl").write_text(
        json.dumps({
            "metadata": {"team_id": "teamE", "run_id": "empty-run",
                         "topic_id": EMPTY_TOPIC},
            "responses": [],
        }) + "\n",
        encoding="utf-8",
    )

    env = dict(
        os.environ,
        # a dead endpoint must not be the reason this test fails; LLM judges
        # have nothing to grade in an empty report anyway
        OPENAI_BASE_URL="http://127.0.0.1:9", OPENAI_API_KEY="test-key",
        OPENAI_MODEL="test-model", CACHE_DIR=str(tmp_path / "cache"),
        MAX_ATTEMPTS="1", TIMEOUT_S="20", RPM="10000",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "autojudge_base.cli", "run",
         "--workflow", str(workflow),
         "--rag-responses", str(responses_dir),
         "--rag-topics", str(KIDDIE_TOPICS),
         "--topic", EMPTY_TOPIC,
         "--out-dir", str(tmp_path / "out")],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=300,
    )

    if "Failed to load judge classes" in (proc.stderr or ""):
        pytest.skip("judge classes failed to import in a subprocess (environment "
                    "issue; import compatibility is covered by test_examples)")

    assert proc.returncode == 0, (
        f"judge crashed on an empty report (responses: []) for topic "
        f"'{EMPTY_TOPIC}'\nstderr tail: {proc.stderr[-2000:]}"
    )

    eval_files = list((tmp_path / "out").glob("*.eval.txt"))
    assert eval_files, f"no eval.txt produced\nstderr tail: {proc.stderr[-2000:]}"
    content = "\n".join(f.read_text(encoding="utf-8") for f in eval_files)
    assert EMPTY_TOPIC in content, (
        f"topic '{EMPTY_TOPIC}' (whose report was empty) is missing from the "
        f"leaderboard — empty reports must be scored, not dropped"
    )
