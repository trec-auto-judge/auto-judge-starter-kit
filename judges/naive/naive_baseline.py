#!/usr/bin/env python3
from typing import Any, Dict, Optional, Sequence, Type

from autojudge_base import (
    AutoJudge,
    Report,
    Request,
    LeaderboardSpec,
    LeaderboardBuilder,
    LeaderboardVerification,
    MeasureSpec,
    auto_judge_to_click_command,
    Leaderboard,
    Qrels,
    LlmConfigProtocol,
    NuggetBanks,
    NuggetBanksProtocol,
)
from tqdm import tqdm
import random


def rand(seed: str) -> float:
    random.seed(seed)
    return random.random()


NAIVE_LEADERBOARD_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("LENGTH"),
    MeasureSpec("RANDOM"),
))


class NaiveJudge(AutoJudge):
    nugget_banks_type: Type[NuggetBanksProtocol] = NuggetBanks

    def create_nuggets(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        corpus: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[NuggetBanksProtocol]:
        return None

    def create_qrels(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        corpus: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Qrels]:
        return None

    def judge(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        qrels: Optional[Qrels] = None,
        corpus: Optional[str] = None,
        **kwargs: Any,
    ) -> Leaderboard:
        builder: LeaderboardBuilder = LeaderboardBuilder(NAIVE_LEADERBOARD_SPEC)
        
        for rag_response in tqdm(rag_responses, "Process RAG Responses"):
            vals: Dict[str, float] = {
                "LENGTH": len(rag_response.get_report_text().split()),
                "RANDOM": rand(rag_response.metadata.run_id + rag_response.metadata.topic_id),
            }
            builder.add(
                run_id=rag_response.metadata.run_id,
                topic_id=rag_response.metadata.topic_id,
                values=vals,
            )

        leaderboard: Leaderboard = builder.build()
        LeaderboardVerification(leaderboard, on_missing="fix_aggregate", warn=True).all()
        return leaderboard


if __name__ == '__main__':
    auto_judge_to_click_command(NaiveJudge(), "naive-judge")()
