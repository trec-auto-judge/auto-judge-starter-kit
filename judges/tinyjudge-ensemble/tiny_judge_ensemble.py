#!/usr/bin/env python3
"""
TinyJudgeEnsemble: Minimal LLM-ensemble judge example.

Like TinyJudge, it checks if the first sentence of each response is relevant
to the query - but it asks three independently configured LLMs (LLM1, LLM2,
LLM3) instead of one, reports each LLM's judgment as its own measure, and
reports the average across all three as a fourth measure.

Each LLM's endpoint is configured through its own trio of environment
variables (OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL for LLM1, the "_2"
suffixed variants for LLM2, and the "_3" suffixed variants for LLM3). Unlike
TinyJudge, the `minima_llm` configs here are always built explicitly from
those environment variables rather than via `llm_config.raw` /
`MinimaLlmConfig.from_env()`, so each LLM's endpoint is unambiguous.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from autojudge_base import (
    Leaderboard,
    LeaderboardBuilder,
    LeaderboardSpec,
    LlmConfigProtocol,
    MeasureSpec,
    NuggetBanksProtocol,
    Qrels,
    Report,
    Request,
)
from minima_llm import MinimaLlmConfig, MinimaLlmRequest, MinimaLlmResponse, OpenAIMinimaLlm


# One LLM per suffix: LLM1 reads OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL,
# LLM2 reads the "_2" suffixed variants, LLM3 the "_3" suffixed variants.
LLM_SUFFIXES: Tuple[Tuple[str, str], ...] = (
    ("LLM1", ""),
    ("LLM2", "_2"),
    ("LLM3", "_3"),
)

TINY_ENSEMBLE_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("FIRST_SENTENCE_RELEVANT_LLM1", description="LLM1 judgment of first sentence relevance (0.0-1.0)"),
    MeasureSpec("FIRST_SENTENCE_RELEVANT_LLM2", description="LLM2 judgment of first sentence relevance (0.0-1.0)"),
    MeasureSpec("FIRST_SENTENCE_RELEVANT_LLM3", description="LLM3 judgment of first sentence relevance (0.0-1.0)"),
    MeasureSpec(
        "FIRST_SENTENCE_RELEVANT_AVG",
        description="Average of the LLM1/LLM2/LLM3 first-sentence relevance judgments (0.0-1.0)",
    ),
))


def _llm_config_from_env(suffix: str) -> MinimaLlmConfig:
    """Explicitly construct a MinimaLlmConfig from the env vars for one ensemble member.

    Always reads OPENAI_API_KEY{suffix}/OPENAI_BASE_URL{suffix}/OPENAI_MODEL{suffix}
    directly - never `MinimaLlmConfig.from_env()` (which only looks at the
    unsuffixed names) and never `llm_config.raw`.
    """
    base_url = os.environ.get(f"OPENAI_BASE_URL{suffix}")
    model = os.environ.get(f"OPENAI_MODEL{suffix}")
    api_key = os.environ.get(f"OPENAI_API_KEY{suffix}")

    missing = [
        name
        for name, value in ((f"OPENAI_BASE_URL{suffix}", base_url), (f"OPENAI_MODEL{suffix}", model))
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    return MinimaLlmConfig(
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=api_key,
        cache_dir=os.environ.get("CACHE_DIR"),
    )


class TinyJudgeEnsemble:
    """
    Judges whether the first sentence of each response is relevant, once per
    ensemble member LLM (LLM1, LLM2, LLM3), and reports their average.

    Implements LeaderboardJudgeProtocol. Configure in workflow.yml:
        judge_class: "judges.tinyjudge-ensemble.tiny_judge_ensemble:TinyJudgeEnsemble"
    """

    def judge(
        self,
        rag_responses: Iterable[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        qrels: Optional[Qrels] = None,
        # Standard output path settings (auto-filled by judge_runner)
        filebase: str = "default",
        outdir: Path = Path("."),
        segments: int = 1,
        **kwargs: Any,
    ) -> Leaderboard:
        """Judge first-response-segment relevance with each ensemble LLM (batched per LLM).

        `segments` (from workflow settings) controls how many leading response
        segments are sent to each LLM; the default of 1 judges only the first.
        """
        topic_titles: Dict[str, str] = {t.request_id: t.title or "" for t in rag_topics}
        expected_topic_ids: List[str] = list(topic_titles.keys())

        # Collect all requests with metadata once; sorted by run_id for deterministic,
        # cache-friendly prompts (same requests are reused across all three LLMs).
        requests_info: List[Tuple[str, str, MinimaLlmRequest]] = []  # (run_id, topic_id, request)
        for i, response in enumerate(sorted(rag_responses, key=lambda r: r.metadata.run_id)):
            query = topic_titles.get(response.metadata.topic_id, "")
            judged_text = " ".join(r.text for r in response.responses[:segments] if r.text)
            requests_info.append((
                response.metadata.run_id,
                response.metadata.topic_id,
                MinimaLlmRequest(
                    request_id=f"q{i}",
                    messages=[
                        {"role": "system", "content": "You are a relevance evaluator. Respond with only 1 or 0."},
                        {"role": "user", "content": f"Is this relevant to the query?\n\nQuery: {query}\nText: {judged_text}"},
                    ],
                    temperature=0.0,
                ),
            ))

        # Run each ensemble member's LLM in its own batch, in a for loop, keyed by measure name.
        scores_per_llm: Dict[str, List[int]] = {}
        for llm_name, suffix in LLM_SUFFIXES:
            config = _llm_config_from_env(suffix)
            backend = OpenAIMinimaLlm(config)
            llm_results = asyncio.run(backend.run_batched([req for _, _, req in requests_info]))
            scores_per_llm[llm_name] = [self._parse_relevance(result) for result in llm_results]

        # Build leaderboard: one measure per LLM, plus the average across all three.
        builder = LeaderboardBuilder(TINY_ENSEMBLE_SPEC)
        for idx, (run_id, topic_id, _) in enumerate(requests_info):
            per_llm_values = {
                f"FIRST_SENTENCE_RELEVANT_{llm_name}": scores_per_llm[llm_name][idx]
                for llm_name, _ in LLM_SUFFIXES
            }
            average = sum(per_llm_values.values()) / len(per_llm_values)
            builder.add(
                run_id=run_id,
                topic_id=topic_id,
                values={**per_llm_values, "FIRST_SENTENCE_RELEVANT_AVG": average},
            )

        return builder.build(expected_topic_ids=expected_topic_ids, on_missing="fix_aggregate")

    def _parse_relevance(self, result: Any) -> int:
        """Parse LLM response to relevance score (0 or 1)."""
        if not isinstance(result, MinimaLlmResponse):
            print(f"[TinyJudgeEnsemble] LLM error: {result}")
            return 0

        text = result.text.strip().lower()
        # Check negative indicators first (order matters: "not relevant" contains "relevant")
        if text.startswith("0") or "not relevant" in text or text == "no":
            return 0
        if text.startswith("1") or "relevant" in text or text == "yes":
            return 1
        return 0
