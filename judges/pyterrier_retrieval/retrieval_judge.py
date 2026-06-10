#!/usr/bin/env python3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Type

from autojudge_base import (
    Report,
    LeaderboardSpec,
    LeaderboardBuilder,
    LeaderboardVerification,
    MeasureSpec,
    AutoJudge,
    auto_judge_to_click_command,
    Leaderboard,
    Qrels,
    Request,
    LlmConfigProtocol,
    NuggetBanks,
    NuggetBanksProtocol,
)
from collections import defaultdict
from tqdm import tqdm
from tira.third_party_integrations import ensure_pyterrier_is_loaded
import pyterrier as pt


def group_by_topic_id(rag_responses: Sequence[Report]) -> Dict[str, Dict[str, str]]:
    """Group RAG responses by topic_id, then by run_id."""
    ret: Dict[str, Dict[str, str]] = defaultdict(dict)
    for rag_response in rag_responses:
        run_id: str = rag_response.metadata.run_id
        topic_id: str = rag_response.metadata.topic_id
        ret[topic_id][run_id] = rag_response.get_report_text()
    return ret


# Some semi-random selected weighting models from http://terrier.org/docs/v4.2/javadoc/org/terrier/matching/models/WeightingModel.html
LEADERBOARD_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("BM25", description="BM25 retrieval score"),
    MeasureSpec("DirichletLM", description="Dirichlet language model score"),
    MeasureSpec("Hiemstra_LM", description="Hiemstra language model score"),
    MeasureSpec("DFIC", description="Divergence from independence score"),
    MeasureSpec("DPH", description="Divergence from randomness (DPH)"),
    MeasureSpec("DLH", description="Divergence from randomness (DLH)"),
    MeasureSpec("Tf", description="Term frequency score"),
    MeasureSpec("TF_IDF", description="TF-IDF score"),
    MeasureSpec("PL2", description="Divergence from randomness (PL2)"),
    MeasureSpec("InL2", description="Inverse document frequency model (InL2)"),
))


class RetrievalJudge(AutoJudge):
    nugget_banks_type: Type[NuggetBanksProtocol] = NuggetBanks

    def create_nuggets(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        # Standard output path settings (auto-filled by judge_runner)
        filebase: str = "default",
        outdir: Path = Path("."),
        **kwargs: Any,
    ) -> Optional[NuggetBanksProtocol]:
        return None

    def create_qrels(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        # Standard output path settings (auto-filled by judge_runner)
        filebase: str = "default",
        outdir: Path = Path("."),
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
        # Standard output path settings (auto-filled by judge_runner)
        filebase: str = "default",
        outdir: Path = Path("."),
        **kwargs: Any,
    ) -> Leaderboard:
        ensure_pyterrier_is_loaded()
        tokeniser: Any = pt.java.autoclass(
            "org.terrier.indexing.tokenisation.Tokeniser"
        ).getTokeniser()

        def pt_tokenize(text: str) -> str:
            return " ".join(tokeniser.getTokens(text))

        topic_id_to_title: Dict[str, str] = {
            i.request_id: pt_tokenize(i.title) for i in rag_topics
        }
        topic_id_to_responses: Dict[str, Dict[str, str]] = group_by_topic_id(
            rag_responses
        )
        all_systems: set[str] = set(i.metadata.run_id for i in rag_responses)

        builder: LeaderboardBuilder = LeaderboardBuilder(LEADERBOARD_SPEC)

        for topic in tqdm(topic_id_to_responses.keys(), "Process Topics"):
            query_text: str = topic_id_to_title[topic]
            docs: List[Dict[str, str]] = [
                {"docno": system, "text": system_response}
                for system, system_response in topic_id_to_responses[topic].items()
            ]
            system_to_wmodel_to_score: Dict[str, Dict[str, float]] = defaultdict(
                lambda: defaultdict(lambda: 1000.0)
            )
            index: Any = pt.IterDictIndexer(
                "/not-needed/for-memory-index",
                meta={"docno": 100},
                type=pt.IndexingType.MEMORY,
            ).index(docs)

            for wmodel in LEADERBOARD_SPEC.measures:
                retriever: Any = pt.terrier.Retriever(index, wmodel=wmodel.name)
                rtr: Any = retriever.search(query_text)
                run_id_to_score: Dict[str, float] = defaultdict(lambda: 0.0)
                for _, i in rtr.iterrows():
                    run_id_to_score[i["docno"]] = max(0.0, 1000.0 - i["rank"])

                for system in all_systems:
                    system_to_wmodel_to_score[system][wmodel.name] = run_id_to_score.get(
                        system, 0.0
                    )

            for system in all_systems:
                builder.add(
                    run_id=system,
                    topic_id=topic,
                    values=dict(system_to_wmodel_to_score[system]),
                )

        leaderboard: Leaderboard = builder.build()
        LeaderboardVerification(leaderboard, on_missing="fix_aggregate").all()
        return leaderboard


if __name__ == '__main__':
    auto_judge_to_click_command(RetrievalJudge(), "retrieval-judge")()
