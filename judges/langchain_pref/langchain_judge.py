"""LangChainPrefJudge: preference-based contrastive nugget judge built on LangChain.

Imitates the prefnugget-starterkit "best-decide-plum" variant:

  Phase 1  Pairwise preference judgments (must_decide, both orders) -> Borda scores
  Phase 2  Iterative contrastive nugget extraction from winner/loser pairs,
           one pair per topic per round, one question per pair, until the
           nugget bank reaches ``target_nuggets`` (20)
  Phase 3  Grade every (response, nugget) pair 0-5; covered means grade >= threshold

The twist over prefnugget: Phase 1 starts with a *small* preference pool
(``initial_num_others`` comparisons per response). Whenever Phase 2 runs out of
productive winner/loser pairs before reaching the nugget target, a DECISION
POINT triggers: judge additional preference pairs (grow the pool by one
comparison offset per response, up to ``max_num_others``), recompute Borda,
and continue extracting. Extraction only gives up when the pool cannot grow
further or the pair budget (``max_pairs_considered``) is exhausted.

LLM access goes through LangChain (ChatOpenAI against the endpoint injected in
``llm_config``); responses are parsed leniently with the same regex approach as
prefnugget, so no provider-specific tool-calling support is required. Prompt
caching uses LangChain's SQLiteCache stored under ``llm_config.cache_dir``.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from autojudge_base import (
    AutoJudge,
    Leaderboard,
    LeaderboardBuilder,
    LeaderboardSpec,
    LlmConfigProtocol,
    MeasureSpec,
    NuggetBanks,
    Qrels,
    Report,
    Request,
    auto_judge_to_click_command,
)
from autojudge_base.nugget_data import Creator, NuggetBank, NuggetQuestion

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


# =============================================================================
# Leaderboard schema (same measures as prefnugget)
# =============================================================================

LANGCHAIN_PREF_SPEC = LeaderboardSpec(measures=(
    MeasureSpec("NUGGET_COVERAGE", description="Fraction of nuggets covered by the response (0.0-1.0)"),
    MeasureSpec("AVG_GRADE", description="Average grade across covered nuggets"),
    MeasureSpec("MAX_GRADE", description="Maximum grade among covered nuggets"),
    MeasureSpec("COVERED_COUNT", int, description="Number of nuggets covered by the response"),
))


# =============================================================================
# Prompts (imitating prefnugget's PrefJudgment, IterativeExtractDifferentiatingNuggets,
# GradeNuggetAnswer) and lenient parsers
# =============================================================================

PREF_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a highly experienced and accurate assessor for TREC.\n\n"
     "Select the passage that answers the query better. Just answer 1 or 2, "
     "without any explanation or extra verbiage. "
     "If both passages are similar, select the simplest and clearest."),
    ("human",
     "Query title: {query_title}\n"
     "Background: {query_background}\n"
     "Problem statement: {query_problem}\n\n"
     "Passage 1:\n{passage_1}\n\n"
     "Passage 2:\n{passage_2}\n\n"
     "Which is the better passage? Answer 1 or 2."),
])

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Compare Winner vs Loser RAG responses for a query. Focus on relevance, "
     "correctness, completeness.\n\n"
     "Identify or generate questions the Winner addresses much better than the "
     "Loser, beyond the given exam questions. New differentiating questions must "
     "be brief, atomic questions about information the Winner handles much better.\n\n"
     "Avoid generic quality questions. Make questions self-contained "
     '(e.g., "Capital of France?" not "The capital?").\n\n'
     'Answer with a JSON array of question strings only, e.g. '
     '["Capital of USA?", "Process to cook steel?"]. '
     "Answer [] if no new differentiating question exists."),
    ("human",
     "Query title: {query_title}\n"
     "Background: {query_background}\n\n"
     "Winner passage:\n{winner_passage}\n\n"
     "Loser passage:\n{loser_passage}\n\n"
     "Given exam questions (do not repeat): {given_exam_questions}\n\n"
     "New differentiating questions as JSON array:"),
])

GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Grade how well a passage answers a specific question.\n\n"
     "Can the question be answered based on the available context? Choose one:\n"
     "- 5: The answer is highly relevant, complete, and accurate.\n"
     "- 4: The answer is mostly relevant and complete but may have minor gaps or inaccuracies.\n"
     "- 3: The answer is partially relevant and complete, with noticeable gaps or inaccuracies.\n"
     "- 2: The answer has limited relevance and completeness, with significant gaps or inaccuracies.\n"
     "- 1: The answer is minimally relevant or complete, with substantial shortcomings.\n"
     "- 0: The answer is not relevant or complete at all.\n\n"
     "Answer with the single digit grade only."),
    ("human", "Question: {question}\n\nPassage:\n{passage}\n\nGrade (0-5):"),
])


def parse_better(text: str) -> Optional[int]:
    """Extract 1 or 2 from the preference answer; None when unparseable."""
    m = re.search(r"\b([12])\b", text or "")
    return int(m.group(1)) if m else None


def parse_grade(text: str) -> int:
    """Extract grade 0-5; unparseable answers count as 0 (imitates prefnugget)."""
    m = re.search(r"\b([0-5])\b", text or "")
    return int(m.group(1)) if m else 0


def parse_questions(text: str) -> List[str]:
    """Extract a JSON array of question strings, tolerating surrounding prose."""
    m = re.search(r"\[.*?\]", text or "", re.DOTALL)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [q.strip() for q in items if isinstance(q, str) and q.strip()]


# =============================================================================
# LLM plumbing
# =============================================================================

def build_llm(llm_config: LlmConfigProtocol):
    """Construct the LangChain chat model from the injected llm_config.

    Never hardcode endpoints or keys -- on TIRA they arrive through llm_config.
    """
    if llm_config.cache_dir:
        # Prompt-cache contract: persist under CACHE_DIR, disk-based backend.
        from langchain_community.cache import SQLiteCache
        from langchain_core.globals import set_llm_cache

        cache_dir = Path(llm_config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=str(cache_dir / "langchain_cache.db")))
        print(f"[langchain_pref] Prompt cache: {cache_dir / 'langchain_cache.db'}", file=sys.stderr)

    return ChatOpenAI(
        model=llm_config.model,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key or "-",
        temperature=0.0,
        max_retries=3,
        timeout=120,
    )


class LlmEndpointError(RuntimeError):
    """The LLM endpoint is unusable (bad key, dead endpoint, stale model id)."""


ENDPOINT_HINT = (
    "check OPENAI_BASE_URL / OPENAI_MODEL / OPENAI_API_KEY (see the HowTo: "
    "https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md#troubleshooting)"
)


def preflight(llm) -> None:
    """Fail fast with the provider's actual error instead of N failed calls."""
    try:
        llm.invoke("Answer with the single word: pong")
    except Exception as e:
        raise LlmEndpointError(f"LLM endpoint preflight failed: {e} — {ENDPOINT_HINT}") from e


def run_chain_batched(chain, inputs: List[dict], max_concurrency: int, phase: str = "") -> List[str]:
    """Run a LangChain chain over inputs; failed items yield empty strings.

    Individual failures are tolerated (logged, counted); when EVERY call fails
    the endpoint itself is broken and we raise instead of degrading silently.
    """
    if not inputs:
        return []
    results = chain.batch(inputs, config={"max_concurrency": max_concurrency}, return_exceptions=True)
    out, failures, first_error = [], 0, None
    for r in results:
        if isinstance(r, Exception):
            failures += 1
            first_error = first_error or r
            out.append("")
        else:
            out.append(r)
    if failures == len(inputs):
        raise LlmEndpointError(
            f"All {failures} LLM calls failed in {phase or 'batch'} "
            f"(first error: {first_error}) — {ENDPOINT_HINT}"
        )
    if failures:
        print(f"[langchain_pref] {phase}: {failures}/{len(inputs)} LLM calls failed "
              f"(first error: {first_error}); continuing with partial results", file=sys.stderr)
    return out


# =============================================================================
# Phase 1: preference pool (growable) and Borda scores
# =============================================================================

@dataclass
class PrefPool:
    """Preference judgments for one topic, grown on demand.

    Pairs are sampled deterministically: run_ids are sorted, and comparison
    offset k pairs run i with run (i+k) % n. Offsets 1..num_others define the
    pool; growing the pool means judging the next offset for every response.
    """

    run_ids: List[str]                                  # sorted
    judged_offsets: int = 0
    judged_keys: set = field(default_factory=set)       # unordered pairs already judged
    consistent_pairs: List[Tuple[str, str]] = field(default_factory=list)  # (winner, loser)

    def pairs_at_offset(self, k: int) -> List[Tuple[str, str]]:
        """New unordered pairs introduced by comparison offset k (dedup across offsets)."""
        n = len(self.run_ids)
        pairs = []
        for i in range(n):
            a, b = self.run_ids[i], self.run_ids[(i + k) % n]
            if a == b:
                continue
            key = tuple(sorted((a, b)))
            if key not in self.judged_keys:
                self.judged_keys.add(key)
                pairs.append((key[0], key[1]))
        return pairs

    def can_grow(self) -> bool:
        # Offsets beyond n//2 only repeat earlier pairs (offset n-k mirrors offset k)
        return self.judged_offsets < len(self.run_ids) // 2

    def borda(self) -> Dict[str, int]:
        scores = {r: 0 for r in self.run_ids}
        for (winner, loser) in self.consistent_pairs:
            scores[winner] += 1
            scores[loser] -= 1
        return scores


def judge_preference_pairs(
    llm, pool: PrefPool, pairs: List[Tuple[str, str]],
    topic: Request, texts: Dict[str, str], max_concurrency: int,
) -> None:
    """Judge each pair in both orders (must_decide); record consistent winners."""
    chain = PREF_PROMPT | llm | StrOutputParser()
    inputs, order = [], []
    for (a, b) in pairs:
        for (p1, p2) in ((a, b), (b, a)):
            inputs.append({
                "query_title": topic.title or "",
                "query_background": topic.background or "",
                "query_problem": topic.problem_statement or "",
                "passage_1": texts[p1],
                "passage_2": texts[p2],
            })
            order.append((p1, p2))
    answers = run_chain_batched(chain, inputs, max_concurrency, phase="preference judging")

    winners_by_pair: Dict[Tuple[str, str], List[str]] = {}
    for (p1, p2), ans in zip(order, answers):
        better = parse_better(ans)
        if better is None:
            continue
        winner = p1 if better == 1 else p2
        winners_by_pair.setdefault(tuple(sorted((p1, p2))), []).append(winner)

    for key, winners in winners_by_pair.items():
        # Both orders agree -> a clear winner/loser pair (ties/inconsistency dropped)
        if len(winners) == 2 and winners[0] == winners[1]:
            winner = winners[0]
            loser = key[0] if winner == key[1] else key[1]
            pool.consistent_pairs.append((winner, loser))


# =============================================================================
# Phase 2: iterative extraction with decision points
# =============================================================================

def extract_nuggets_for_topic(
    llm, topic: Request, responses: List[Report], settings: dict,
) -> Tuple[List[str], dict]:
    """Run Phase 1 + Phase 2 for one topic; returns (questions, stats)."""
    target = settings["target_nuggets"]
    max_pairs = settings["max_pairs_considered"]
    per_pair = settings["max_questions_per_pair"]
    concurrency = settings["max_concurrency"]

    texts = {r.metadata.run_id: r.get_report_text() for r in responses}
    # Deterministic ordering: sort by run_id (stable prompts -> stable cache keys)
    pool = PrefPool(run_ids=sorted(texts.keys()))

    chain = EXTRACT_PROMPT | llm | StrOutputParser()
    questions: List[str] = []
    seen_normalized: set = set()
    consumed: set = set()
    pairs_used = 0
    rounds = 0
    growths = 0

    def grow_pool() -> bool:
        """Decision point outcome: judge one more comparison offset per response."""
        nonlocal growths
        if not pool.can_grow():
            return False
        k = pool.judged_offsets + 1
        judge_preference_pairs(llm, pool, pool.pairs_at_offset(k), topic, texts, concurrency)
        pool.judged_offsets = k
        growths += 1
        return True

    # Start with the initial (small) pool
    while pool.judged_offsets < settings["initial_num_others"] and pool.can_grow():
        grow_pool()
    growths = 0  # only count on-demand growths

    while len(questions) < target and pairs_used < max_pairs:
        # Plum ordering: strongest winner first, then strongest loser
        borda = pool.borda()
        queue = [p for p in pool.consistent_pairs if p not in consumed]
        queue.sort(key=lambda p: (borda[p[0]] + 0.99 * borda[p[1]], p), reverse=True)

        if not queue:
            # DECISION POINT: no unconsumed pairs left but nugget target not reached.
            # Create more preference pairs if the pool can still grow; otherwise give up.
            if not grow_pool():
                break
            continue

        # plum: one pair per round, one question per pair
        winner, loser = queue[0]
        consumed.add((winner, loser))
        pairs_used += 1
        rounds += 1

        answer = run_chain_batched(chain, [{
            "query_title": topic.title or "",
            "query_background": topic.background or "",
            "winner_passage": texts[winner],
            "loser_passage": texts[loser],
            "given_exam_questions": json.dumps(questions),
        }], concurrency, phase="nugget extraction")[0]

        added = 0
        for q in parse_questions(answer)[:per_pair]:
            norm = q.casefold().strip()
            if norm and norm not in seen_normalized:
                seen_normalized.add(norm)
                questions.append(q)
                added += 1
                if len(questions) >= target:
                    break

        if added == 0 and not queue[1:]:
            # DECISION POINT: the last remaining pair yielded nothing new.
            # Try to widen the preference pool rather than stopping short.
            if not grow_pool():
                break

    stats = {
        "questions": len(questions), "pairs_used": pairs_used,
        "pool_offsets": pool.judged_offsets, "on_demand_growths": growths,
        "consistent_pairs": len(pool.consistent_pairs),
    }
    return questions, stats


# =============================================================================
# The judge
# =============================================================================

class LangChainPrefJudge(AutoJudge):
    """Preference-nugget judge on LangChain, imitating prefnugget best-decide-plum."""

    nugget_banks_type = NuggetBanks

    DEFAULTS = dict(
        target_nuggets=20,
        initial_num_others=2,     # start small; decision points grow on demand ...
        max_questions_per_pair=1,  # plum: one question per pair
        max_pairs_considered=100,
        grade_threshold=4,
        max_concurrency=8,
    )

    def _settings(self, kwargs: dict) -> dict:
        settings = dict(self.DEFAULTS)
        for key in settings:
            if key in kwargs and kwargs[key] is not None:
                settings[key] = type(settings[key])(kwargs[key])
        return settings

    # ---- Phase 1 + 2 ----------------------------------------------------
    def create_nuggets(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanks] = None,
        filebase: str = "default",
        outdir: Path = Path("."),
        **kwargs,
    ) -> Optional[NuggetBanks]:
        settings = self._settings(kwargs)
        llm = build_llm(llm_config)
        preflight(llm)

        by_topic: Dict[str, List[Report]] = {}
        for r in rag_responses:
            by_topic.setdefault(r.metadata.topic_id, []).append(r)

        creator = Creator(
            is_human=False,
            llm_model=llm_config.model,
            llm_backend="langchain",
            llm_prompt_strategy="static",
            contact=["langchain-starterkit"],
        )

        banks: List[NuggetBank] = []
        for topic in sorted(rag_topics, key=lambda t: t.request_id):
            responses = by_topic.get(topic.request_id, [])
            if len(responses) < 2:
                print(f"[langchain_pref] topic {topic.request_id}: <2 responses, skipping", file=sys.stderr)
                continue
            questions, stats = extract_nuggets_for_topic(llm, topic, responses, settings)
            print(f"[langchain_pref] topic {topic.request_id}: {stats}", file=sys.stderr)

            bank = NuggetBank(
                query_id=topic.request_id,
                title_query=topic.title or "",
                full_query={
                    "background": topic.background or "",
                    "problem_statement": topic.problem_statement or "",
                },
            )
            bank.add_nuggets([
                NuggetQuestion.from_lazy(query_id=topic.request_id, question=q, creator=creator)
                for q in questions
            ])
            banks.append(bank)

        if banks and all(len(b.nuggets_as_list()) == 0 for b in banks):
            raise LlmEndpointError(
                f"Nugget extraction produced 0 questions for all {len(banks)} topics; "
                f"LLM calls are likely failing — {ENDPOINT_HINT}"
            )
        return NuggetBanks.from_banks_list(banks)

    # ---- Phase 3 ---------------------------------------------------------
    def judge(
        self,
        rag_responses: Sequence[Report],
        rag_topics: Sequence[Request],
        llm_config: LlmConfigProtocol,
        nugget_banks: Optional[NuggetBanks] = None,
        qrels: Optional[Qrels] = None,
        filebase: str = "default",
        outdir: Path = Path("."),
        **kwargs,
    ) -> Leaderboard:
        settings = self._settings(kwargs)
        if nugget_banks is None:
            raise ValueError("LangChainPrefJudge.judge() requires nugget_banks (judge_uses_nuggets: true)")
        llm = build_llm(llm_config)
        preflight(llm)
        chain = GRADE_PROMPT | llm | StrOutputParser()

        responses = sorted(rag_responses, key=lambda r: (r.metadata.topic_id, r.metadata.run_id))
        inputs, index = [], []
        for r in responses:
            bank = nugget_banks.banks.get(r.metadata.topic_id)
            if bank is None:
                continue
            passage = r.get_report_text()
            for nugget in bank.nuggets_as_list():
                inputs.append({"question": nugget.question, "passage": passage})
                index.append((r.metadata.run_id, r.metadata.topic_id))

        answers = run_chain_batched(chain, inputs, settings["max_concurrency"], phase="grading")

        grades: Dict[Tuple[str, str], List[int]] = {}
        for (run_id, topic_id), ans in zip(index, answers):
            grades.setdefault((run_id, topic_id), []).append(parse_grade(ans))

        threshold = settings["grade_threshold"]
        builder = LeaderboardBuilder(LANGCHAIN_PREF_SPEC)
        for (run_id, topic_id), gs in grades.items():
            covered = [g for g in gs if g >= threshold]
            builder.add(run_id=run_id, topic_id=topic_id, values={
                "NUGGET_COVERAGE": len(covered) / len(gs) if gs else 0.0,
                "AVG_GRADE": sum(covered) / len(covered) if covered else 0.0,
                "MAX_GRADE": float(max(covered)) if covered else 0.0,
                "COVERED_COUNT": len(covered),
            })

        topic_ids = [t.request_id for t in rag_topics]
        return builder.build(expected_topic_ids=topic_ids, on_missing="fix_aggregate")


if __name__ == "__main__":
    auto_judge_to_click_command(LangChainPrefJudge())
