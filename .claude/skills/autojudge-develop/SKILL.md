---
name: autojudge-develop
description: Implement, run, and evaluate a TREC AutoJudge. Use when the user wants to build a judge, scaffold a judge directory, write judge()/create_nuggets()/create_qrels(), run workflows or variants, debug prompt-cache misses, or meta-evaluate against ground truth. Covers the develop, run, cache, and meta-evaluation activities.
---

# Develop, run, and evaluate an AutoJudge

Walk the developer through this **interactively, one step at a time**. After each step, report what you found or did, then confirm before moving on.

The **canonical instructions live in the [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** — this skill drives its pages [develop-an-autojudge](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md), [run-workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md), [prompt-cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md), and [meta-evaluation](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md); defer to them and do not contradict them. Environment or endpoint problems belong to `/autojudge-setup`; submitting belongs to `/autojudge-submit`.

## Step 0 — Read the canonical pages IN FULL before writing or running anything
Read [develop-an-autojudge](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md) and [run-workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md) end to end **now** (and [prompt-cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md) / [meta-evaluation](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) before Steps 4-5). Do not skim, do not grep, and do not consult framework source code for anything these pages answer. If a local checkout of the howto exists (e.g. a `profile/howto/` directory), read the local files. Only after both pages are read, continue with Step 1.

**Essentials** (the facts every session needs immediately; if context was lost mid-walkthrough, recover from here):
- There is ONE run command: `auto-judge run` (plus `export-corpus`). There is no `judge`/`nuggify` subcommand.
- `auto-judge run --help` lists every flag; the everyday ones: `--limit-topics/--topic`, `--run/--limit-runs`, `--variant`, `-S/-N/-J KEY=VALUE` overrides, `--nugget-banks FILE-OR-DIR`, `--out-dir`, `--filebase`.
- A judge may implement ONLY `judge()` (`LeaderboardJudgeProtocol`) and consume prebuilt banks via `--nugget-banks` — then the class MUST declare `nugget_banks_type = NuggetBanks` or the runner cannot load them.
- Judge classes are `module:Class` dotted paths — any importable package works (`judges.myjudge...` in the kit, or an installed package path).
- Output files are `{filebase}.eval.txt` + `.eval.measures.yml` + `.config.yml` in `--out-dir` (the runner prefixes `tmp-` onto the filebase when `--limit-topics`/`--topic` is set).

## Step 1 — Scaffold the judge
Check `judges/` for a directory beyond the example judges. If none exists, ask the developer for a judge name and create `judges/<name>/` with `__init__.py`, the judge module, and a minimal `workflow.yml` (`judge_class`, lifecycle flags, `settings.filebase: "{_name}"`). Use `judges/complete_example/` (full protocol) or `judges/tinyjudge/` (minimal LLM) as templates. Run `git add judges/<name>/`.

## Step 2 — Implement, guided by the data model
Follow [develop-an-autojudge](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md) section by section, asking which shape fits (leaderboard-only vs nuggets/qrels):
- read responses via `Report`/`Request` (`Report.get_sentences_with_citations()` for citation-aware judging)
- batch LLM calls (`run_batched` for plain prompts; `run_dspy_batch` for DSPy signatures) with the endpoint from `llm_config`
- build the leaderboard through `LeaderboardSpec`/`LeaderboardBuilder`, every `MeasureSpec` with a `description`
- nuggets via `NuggetBank`/`NuggetBanks`, qrels via `QrelsSpec`/`build_qrels`/`write_qrel_file`
- hyperparameters as `workflow.yml` settings and `variants`, not constants in code
Enforce the conventions: no hardcoded keys/endpoints (the task-provided `OPENAI_BASE_URL`/`OPENAI_MODEL`/`OPENAI_API_KEY` must be used as-is and routed into the LLM client — hardcoded values do not run on TIRA, and that failure surfaces only after submission; `tests/test_endpoint_contract.py` checks this; judges without LLM calls declare `uses_llm: false` in their workflow.yml, which xfails their case), sort by `run_id` before pairing, accept `filebase`/`outdir`, verify before returning.

## Step 3 — Run on kiddie, iterate fast
```bash
auto-judge run --workflow judges/<name>/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-kiddie/
```
During iteration prefer `--limit-topics 2` or `--topic ID`, and `-S/-N/-J KEY=VALUE` for quick setting overrides ([full flag table](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md)). Confirm the expected output files appear (`.eval.txt`, `.config.yml`, plus `.nuggets.jsonl`/`.qrels` when enabled); when eyeballing `.nuggets.jsonl`, the questions live under `nugget_bank` as a mapping keyed by nugget id, not a list. Keep `pytest` green as you go — the suite checks every git-tracked judge for minimum framework compatibility (workflow parses, declared classes import: exactly what `auto-judge run` does at load time), so your judge is covered once its directory is `git add`ed, and passing tests are a submission requirement.

## Step 4 — Keep the prompt cache warm
With `CACHE_DIR` set, re-runs should be near-instant. If they are not, diagnose per [prompt-cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md): check prompt determinism first, then trace with `MINIMA_TRACE_FILE=trace.jsonl` and diff the canonical JSON between runs. Use `CACHE_FORCE_REFRESH=1` when fresh answers are wanted.

## Step 5 — Meta-evaluate
```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures --truth-header \
    --eval-format ir_measures --on-missing default \
    output-kiddie/*.eval.txt
```
Remind the developer that kiddie truth is synthetic — a pipeline check, not a quality signal; real correlations come from the [meta-evaluation service](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) or real assessments. When ready to submit, hand off to `/autojudge-submit`.
