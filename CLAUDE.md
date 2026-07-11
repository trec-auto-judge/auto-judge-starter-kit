# CLAUDE.md — Auto-Judge Starterkit

## Project Overview

This repository, the [auto-judge-starterkit](https://github.com/trec-auto-judge/auto-judge-starter-kit), serves as a forkable template for building a custom LLM judge for TREC AutoJudge. The **canonical participant documentation** lives in the org profile as the
[TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md) — one page per activity. Defer to it rather than duplicate it.

## Getting Started

Three interactive skills in `.claude/skills/` cover every HowTo activity; the HowTo pages cover the same ground for manual use:

| Activity | Skill | Canonical pages |
|----------|-------|-----------------|
| Set up env + LLM endpoint | `/autojudge-setup` | [01-setup-environment](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md), [02-configure-llm-endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md) |
| Develop, run, cache, meta-evaluate | `/autojudge-develop` | [03](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md)–[06](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) |
| Submit to TIRA | `/autojudge-submit` | [07-submit-to-tira](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md) |

## Development Commands

```bash
# Setup (recommended: everything to develop, test, and submit)
uv venv && source .venv/bin/activate
uv pip install -e '.[all]'

# Run judge
auto-judge run --workflow judges/MYJUDGE/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-kiddie/

# Smoke test (example judge + meta-eval)
bash run_kiddie.sh

# Meta-evaluate
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures --truth-header \
    --eval-format ir_measures --on-missing default \
    output-kiddie/*.eval.txt
```

## Conventions

Follow the conventions in [develop-an-autojudge](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md) — most importantly: read the LLM endpoint from `llm_config` (never hardcode keys), sort responses by `run_id` before creating comparison pairs (deterministic prompts → stable cache keys), give every `MeasureSpec` a `description`, and accept the injected `filebase`/`outdir` parameters.

## Key References

- [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md) — canonical guide for all activities
- [Workflow guide](https://github.com/trec-auto-judge/auto-judge-base/blob/main/src/autojudge_base/workflow/README.md) — `workflow.yml` schema: lifecycle flags, variants, sweeps
- [auto-judge-base](https://github.com/trec-auto-judge/auto-judge-base) — data classes (`Report`, `Request`, `Leaderboard`, `NuggetBanks`)
- [minima-llm](https://github.com/trec-auto-judge/minima-llm) — LLM backend, prompt caching
- `judges/complete_example/` — full protocol example (nuggets + qrels + leaderboard)
