"""Smoke tests for example judges."""

import pytest
from pathlib import Path


def test_minimaljudge_imports():
    """Test that MinimalJudge classes can be imported."""
    from judges.minimaljudge import (
        MinimalNuggetCreator,
        MinimalQrelsCreator,
        MinimalLeaderboardJudge,
        MINIMAL_SPEC,
    )

    assert MinimalNuggetCreator is not None
    assert MinimalQrelsCreator is not None
    assert MinimalLeaderboardJudge is not None
    assert len(MINIMAL_SPEC.measures) == 2


def test_naive_judge_imports():
    """Test that NaiveJudge can be imported."""
    from judges.naive import NaiveJudge, NAIVE_LEADERBOARD_SPEC

    assert NaiveJudge is not None
    assert len(NAIVE_LEADERBOARD_SPEC.measures) == 2


def test_workflow_files_exist():
    """Test that workflow.yml files exist for all judges."""
    base = Path(__file__).parent.parent / "judges"

    assert (base / "minimaljudge" / "workflow.yml").exists()
    assert (base / "naive" / "workflow.yml").exists()
    assert (base / "pyterrier_retrieval" / "workflow.yml").exists()


def test_minimal_spec_measures():
    """Test MinimalJudge spec has expected measures."""
    from judges.minimaljudge import MINIMAL_SPEC

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
    from judges.minimaljudge import MinimalNuggetCreator
    from autojudge_base.nugget_data import NuggetBanksProtocol

    creator = MinimalNuggetCreator()
    assert hasattr(creator, 'nugget_banks_type')
    assert issubclass(creator.nugget_banks_type, NuggetBanksProtocol.__class__) or \
           creator.nugget_banks_type is not None
