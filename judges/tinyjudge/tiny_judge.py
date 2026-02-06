#!/usr/bin/env python3
"""
TinyJudge: Minimal LLM-based judge example.

Uses an LLM to check if the first sentence of each response is relevant to the query.
This is the simplest possible LLM judge - use it as a starting point.
"""

import asyncio
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


TINY_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("FIRST_SENTENCE_RELEVANT"),
))


class TinyJudge:
    """
    Judges whether the first sentence of each response is relevant.

    Implements LeaderboardJudgeProtocol. Configure in workflow.yml:
        judge_class: "judges.tinyjudge.tiny_judge.TinyJudge"
    """

    def judge(
        self,
        rag_responses: Iterable[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        qrels: Optional[Qrels] = None,
        **kwargs: Any,
    ) -> Leaderboard:
        """Judge first-sentence relevance using LLM (batched for efficiency)."""
        topic_titles: Dict[str, str] = {t.request_id: t.title or "" for t in rag_topics}
        expected_topic_ids: List[str] = list(topic_titles.keys())

        # Collect all requests with metadata
        requests_info: List[Tuple[str, str, MinimaLlmRequest]] = []  # (run_id, topic_id, request)
        for i, response in enumerate(rag_responses):
            query = topic_titles.get(response.metadata.topic_id, "")
            first_sentence = response.responses[0].text if response.responses else ""
            requests_info.append((
                response.metadata.run_id,
                response.metadata.topic_id,
                MinimaLlmRequest(
                    request_id=f"q{i}",
                    messages=[
                        {"role": "system", "content": "You are a relevance evaluator. Respond with only 1 or 0."},
                        {"role": "user", "content": f"Is this relevant to the query?\n\nQuery: {query}\nSentence: {first_sentence}"},
                    ],
                    temperature=0.0,
                ),
            ))

        # Run all LLM requests in batch
        # Convert base config to full MinimaLlmConfig for backend features (batching, retry, etc.)
        full_config = MinimaLlmConfig.from_dict(llm_config.raw) if llm_config.raw else MinimaLlmConfig.from_env()
        backend = OpenAIMinimaLlm(full_config)
        llm_results = asyncio.run(backend.run_batched([req for _, _, req in requests_info]))

        # Build leaderboard from responses
        builder = LeaderboardBuilder(TINY_SPEC)
        for (run_id, topic_id, _), result in zip(requests_info, llm_results):
            relevance = self._parse_relevance(result)
            builder.add(run_id=run_id, topic_id=topic_id, values={"FIRST_SENTENCE_RELEVANT": relevance})

        return builder.build(expected_topic_ids=expected_topic_ids, on_missing="fix_aggregate")

    def _parse_relevance(self, result: Any) -> int:
        """Parse LLM response to relevance score (0 or 1)."""
        if not isinstance(result, MinimaLlmResponse):
            print(f"[TinyJudge] LLM error: {result}")
            return 0

        text = result.text.strip().lower()
        # Check negative indicators first (order matters: "not relevant" contains "relevant")
        if text.startswith("0") or "not relevant" in text or text == "no":
            return 0
        if text.startswith("1") or "relevant" in text or text == "yes":
            return 1
        return 0