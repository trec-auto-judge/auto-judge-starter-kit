"""Smoke tests for example judges."""

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


def test_example_judge_imports():
    """Test that CompleteExampleJudge classes can be imported."""
    from judges.complete_example import (
        ExampleNuggetCreator,
        ExampleQrelsCreator,
        ExampleLeaderboardJudge,
        MINIMAL_SPEC,
    )

    assert ExampleNuggetCreator is not None
    assert ExampleQrelsCreator is not None
    assert ExampleLeaderboardJudge is not None
    assert len(MINIMAL_SPEC.measures) == 2


def test_naive_judge_imports():
    """Test that NaiveJudge can be imported."""
    from judges.naive import NaiveJudge, NAIVE_LEADERBOARD_SPEC

    assert NaiveJudge is not None
    assert len(NAIVE_LEADERBOARD_SPEC.measures) == 2


def test_judges_discovered():
    """At least one judge with a workflow.yml is defined in this repo."""
    assert WORKFLOWS, "no tracked judges/*/workflow.yml found"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.parent.name)
def test_workflow_parses_and_classes_import(workflow):
    """Every judge defined in this repo has a parseable workflow.yml whose
    declared classes import. Judges are discovered dynamically (git-tracked
    workflow.yml files), so this test never goes stale when judges are
    added or removed."""
    cfg = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    refs = [cfg[k] for k in ("judge_class", "nugget_class", "qrels_class") if cfg.get(k)]
    assert refs, f"{workflow} declares no judge/nugget/qrels class"
    for ref in refs:
        module_name, _, attr = ref.partition(":")
        module = importlib.import_module(module_name)
        assert hasattr(module, attr), f"{ref}: {attr} not found in {module_name}"


def test_minimal_spec_measures():
    """Test MinimalJudge spec has expected measures."""
    from judges.complete_example import MINIMAL_SPEC

    measure_names = [m.name for m in MINIMAL_SPEC.measures]
    assert "SCORE" in measure_names
    assert "HAS_KEYWORDS" in measure_names


def test_naive_spec_measures():
    """Test NaiveJudge spec has expected measures."""
    from judges.naive import NAIVE_LEADERBOARD_SPEC

    measure_names = [m.name for m in NAIVE_LEADERBOARD_SPEC.measures]
    assert "LENGTH" in measure_names
    assert "RANDOM" in measure_names


def test_nugget_creator_has_banks_type():
    """Test that nugget creators declare their nugget_banks_type."""
    from judges.complete_example import ExampleNuggetCreator
    from autojudge_base.nugget_data import NuggetBanksProtocol

    creator = ExampleNuggetCreator()
    assert hasattr(creator, 'nugget_banks_type')
    assert issubclass(creator.nugget_banks_type, NuggetBanksProtocol.__class__) or \
           creator.nugget_banks_type is not None
