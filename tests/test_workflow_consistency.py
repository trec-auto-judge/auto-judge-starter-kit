"""Consistency between a judge's workflow.yml lifecycle flags and its classes.

If a judge turns on a phase — `create_nuggets`, `create_qrels`, or `judge` —
the class that runs it must actually implement that method. The runner resolves
each phase to `nugget_class` / `qrels_class` if given, otherwise falls back to
`judge_class` (one class may implement the whole AutoJudge protocol). This test
resolves the same way and checks the method exists, so a judge that flips
`create_qrels: true` but never implements `create_qrels()` fails here — before a
run — instead of mid-run.

This is the cheap, LLM-free half of "verify your outputs". The complementary
runtime guarantee — that a produced artifact is complete (non-empty nugget
banks, every expected topic scored) — is enforced by the workflow runner's own
verification during the run, and encouraged as an explicit `verify(...)` call in
judge code (see the develop-an-autojudge howto). Judges are discovered
dynamically, so this never goes stale as judges change.
"""

import importlib
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).parent.parent


def _tracked_workflows():
    """Judges defined in this repo = git-tracked judges/*/workflow.yml
    (a filesystem glob would also pick up local untracked leftovers)."""
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

# (flag that turns the phase on, method the resolved class must implement,
#  the class key that overrides judge_class for this phase, flag default).
# Defaults match the runner: judge runs unless disabled; nuggets/qrels are opt-in.
PHASE_RULES = [
    ("create_nuggets", "create_nuggets", "nugget_class", False),
    ("create_qrels", "create_qrels", "qrels_class", False),
    ("judge", "judge", "judge_class", True),
]


def _load_class(ref):
    module_name, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module_name), attr, None)


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.parent.name)
def test_enabled_phases_are_implemented(workflow):
    cfg = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    for flag, method, class_key, default in PHASE_RULES:
        if not cfg.get(flag, default):
            continue
        ref = cfg.get(class_key) or cfg.get("judge_class")
        assert ref, (
            f"{workflow.parent.name}: {flag} is on but neither {class_key} nor "
            f"judge_class is declared to run that phase."
        )
        cls = _load_class(ref)
        assert cls is not None, f"{workflow.parent.name}: class {ref} not found"
        assert callable(getattr(cls, method, None)), (
            f"{workflow.parent.name}: {flag} is on and resolves to {ref}, but that "
            f"class does not implement {method}(). Implement it, or set {flag}: false."
        )
