#!/usr/bin/env python3
"""
MinimalJudge: A simple example AutoJudge implementation.

This judge demonstrates the modular protocol pattern with three separate classes:
- MinimalNuggetCreator: Creates nugget questions for topics
- MinimalQrelsCreator: Creates relevance judgments
- MinimalLeaderboardJudge: Scores responses and produces leaderboard

Each class implements a single protocol, allowing flexible composition in workflow.yml.
No LLM calls are used - all logic is deterministic based on text length and keywords.

Use this as a starting template for building your own modular judge.
"""

from typing import Iterable, Optional, Sequence, Type

from autojudge_base import (
    MinimaLlmConfig,
    Report,
    Request,
    Leaderboard,
    LeaderboardBuilder,
    LeaderboardSpec,
    MeasureSpec,
    Qrels,
    QrelsSpec,
    build_qrels,
    doc_id_md5,
)
from autojudge_base.nugget_data import (
    NuggetBanks,
    NuggetBank,
    NuggetQuestion,
    NuggetBanksProtocol,
)


# =============================================================================
# Leaderboard Specification
# =============================================================================
# Define what measures the judge produces and how to aggregate them.

MINIMAL_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("SCORE"),
    MeasureSpec("HAS_KEYWORDS"),  # Use 1.0/0.0 for boolean
))


# =============================================================================
# Qrels Specification
# =============================================================================
# Define how to extract (topic_id, doc_id, grade) from grading records.

class GradeRecord:
    """Simple record for qrels building."""
    def __init__(self, topic_id: str, text: str, grade: int):
        self.topic_id = topic_id
        self.text = text
        self.grade = grade


MINIMAL_QRELS_SPEC = QrelsSpec[GradeRecord](
    topic_id=lambda r: r.topic_id,
    doc_id=lambda r: doc_id_md5(r.text),  # Hash response text as doc_id
    grade=lambda r: r.grade,
    on_duplicate="keep_max",  # Keep highest grade if duplicates
)


# =============================================================================
# MinimalNuggetCreator - NuggetCreatorProtocol
# =============================================================================

class MinimalNuggetCreator:
    """
    Creates nugget questions for each topic.

    Implements NuggetCreatorProtocol. In a real judge, this would use an LLM
    to generate meaningful questions. Here we create simple template questions.
    """

    # Declare the nugget format this creator produces
    nugget_banks_type: Type[NuggetBanksProtocol] = NuggetBanks

    def create_nuggets(
        self,
        rag_responses: Iterable[Report],
        rag_topics: Sequence[Request],
        llm_config: MinimaLlmConfig,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        # Settings from workflow.yml nugget_settings
        questions_per_topic: int = 3,
        **kwargs,
    ) -> Optional[NuggetBanksProtocol]:
        """Create nugget questions for each topic."""
        banks = []

        for topic in rag_topics:
            # Create a NuggetBank for this topic
            bank = NuggetBank(
                query_id=topic.request_id,
                title_query=topic.title or topic.request_id,
            )

            # Generate questions (in a real judge, use LLM)
            questions = []
            for i in range(questions_per_topic):
                question = NuggetQuestion.from_lazy(
                    query_id=topic.request_id,
                    question=f"Q{i+1}: What information about '{topic.title}' is provided?",
                    gold_answers=[f"Answer about {topic.title}"],
                )
                questions.append(question)

            bank.add_nuggets(questions)
            banks.append(bank)

        nugget_banks = NuggetBanks.from_banks_list(banks)
        print(f"MinimalNuggetCreator: Created nuggets for {len(banks)} topics")
        return nugget_banks


# =============================================================================
# MinimalQrelsCreator - QrelsCreatorProtocol
# =============================================================================

class MinimalQrelsCreator:
    """
    Creates relevance judgments (qrels) for responses.

    Implements QrelsCreatorProtocol. In a real judge, this would use an LLM
    to assess relevance. Here we use a simple length-based heuristic.
    """

    def create_qrels(
        self,
        rag_responses: Iterable[Report],
        rag_topics: Sequence[Request],
        llm_config: MinimaLlmConfig,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        # Settings from workflow.yml qrels_settings
        grade_range: tuple = (0, 3),
        length_threshold: int = 100,
        **kwargs,
    ) -> Optional[Qrels]:
        """Create relevance judgments for each response."""
        grade_records = []

        for response in rag_responses:
            topic_id = response.metadata.topic_id
            text = response.get_report_text()

            # Simple grading heuristic (replace with LLM in real judge)
            text_length = len(text)
            if text_length > length_threshold * 3:
                grade = grade_range[1]  # Excellent
            elif text_length > length_threshold * 2:
                grade = 2  # Good
            elif text_length > length_threshold:
                grade = 1  # Fair
            else:
                grade = grade_range[0]  # Poor

            grade_records.append(GradeRecord(topic_id, text, grade))

        qrels = build_qrels(records=grade_records, spec=MINIMAL_QRELS_SPEC)
        print(f"MinimalQrelsCreator: Created qrels for {len(grade_records)} responses")
        return qrels


# =============================================================================
# MinimalLeaderboardJudge - LeaderboardJudgeProtocol
# =============================================================================

class MinimalLeaderboardJudge:
    """
    Scores responses and produces a leaderboard.

    Implements LeaderboardJudgeProtocol. Scores are based on text length
    and keyword matching from topic titles.
    """

    def judge(
        self,
        rag_responses: Iterable[Report],
        rag_topics: Sequence[Request],
        llm_config: MinimaLlmConfig,
        nugget_banks: Optional[NuggetBanksProtocol] = None,
        qrels: Optional[Qrels] = None,
        # Settings from workflow.yml judge_settings
        keyword_bonus: float = 0.2,
        on_missing_evals: str = "fix_aggregate",
        **kwargs,
    ) -> Leaderboard:
        """Judge RAG responses and produce a leaderboard."""
        expected_topic_ids = [t.request_id for t in rag_topics]
        topic_titles = {t.request_id: (t.title or "").lower() for t in rag_topics}

        builder = LeaderboardBuilder(MINIMAL_SPEC)

        for response in rag_responses:
            run_id = response.metadata.run_id
            topic_id = response.metadata.topic_id
            text = response.get_report_text().lower()

            # Base score from text length (normalize to 0-1)
            base_score = min(len(text) / 1000.0, 1.0)

            # Check for keywords from topic title
            title_words = topic_titles.get(topic_id, "").split()
            keywords_found = sum(1 for word in title_words if word in text)
            has_keywords = keywords_found > 0

            # Apply keyword bonus
            score = base_score
            if has_keywords:
                score = min(score + keyword_bonus, 1.0)

            # Optionally use nuggets for additional scoring
            if nugget_banks and topic_id in nugget_banks.banks:
                bank = nugget_banks.banks[topic_id]
                nugget_count = len(bank.nuggets_as_list())
                if nugget_count > 0:
                    score = min(score + 0.05 * nugget_count, 1.0)

            # Optionally use qrels (could adjust score based on grades)
            if qrels:
                pass

            builder.add(
                run_id=run_id,
                topic_id=topic_id,
                values={
                    "SCORE": score,
                    "HAS_KEYWORDS": has_keywords,
                },
            )

        leaderboard = builder.build(
            expected_topic_ids=expected_topic_ids,
            on_missing=on_missing_evals,
        )

        leaderboard.verify(
            expected_topic_ids=expected_topic_ids,
            warn=True,
            on_missing=on_missing_evals,
        )

        print(f"MinimalLeaderboardJudge: Built leaderboard with {len(leaderboard.entries)} entries")
        return leaderboard


# =============================================================================
# CLI Entry Point (optional - for direct execution)
# =============================================================================
# Note: With modular classes, prefer running via:
#   auto-judge run --workflow workflow.yml
#
# For backwards compatibility, we still support direct CLI execution
# by combining all three protocols into a single object.

if __name__ == "__main__":
    from autojudge_base import AutoJudge, auto_judge_to_click_command

    class MinimalJudgeCombined(AutoJudge):
        """Combined class for CLI compatibility."""
        nugget_banks_type = NuggetBanks

        def __init__(self):
            self._nugget_creator = MinimalNuggetCreator()
            self._qrels_creator = MinimalQrelsCreator()
            self._leaderboard_judge = MinimalLeaderboardJudge()

        def create_nuggets(self, *args, **kwargs):
            return self._nugget_creator.create_nuggets(*args, **kwargs)

        def create_qrels(self, *args, **kwargs):
            return self._qrels_creator.create_qrels(*args, **kwargs)

        def judge(self, *args, **kwargs):
            return self._leaderboard_judge.judge(*args, **kwargs)

    auto_judge_to_click_command(MinimalJudgeCombined(), "minimal_judge")()
