---
name: autojudge-setup
description: Set up a development environment to start building a new TREC AutoJudge from this starter kit. Use when the user wants to get the starter kit running, install dependencies, create a new judge, or asks "how do I start / set up / begin developing my judge". Walks through venv, install, a verification run on the kiddie dataset, and scaffolding a new judge directory.
---

# Set up an AutoJudge development environment

Walk the developer through this **interactively, one step at a time**. After each step, report what you found or did, then confirm before moving on. Do not run all steps in one shot.

The **canonical instructions live in the [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** — this skill drives its pages [setup-environment](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md), [configure-llm-endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md), [developing-practices](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-developing-practices.md), and [run-workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md); defer to them and do not contradict them. This repo's README holds the kit-specific reference (example judges, kiddie dataset, project structure). For submitting, use `/autojudge-submit`.

## Step 1 — Create and activate a virtual environment
```bash
uv venv
source .venv/bin/activate
```
Common pitfall: `uv venv` creates the venv but does **not** activate it — if activation is skipped, the next `uv pip install` may land in the wrong environment.

## Step 2 — Install the toolchain
```bash
uv pip install -e '.[all]'
```
The `.[all]` extra covers develop + test + evaluate + submit. If the developer just wants to write code first, the lightweight `uv pip install -e .` works; they should switch to `.[all]` before testing or submitting.

## Step 3 — Verify the environment on the kiddie dataset
```bash
bash run_kiddie.sh
pytest
```
Any failure here signals an environment problem to fix before writing judge code.

## Step 4 — Configure the LLM endpoint
If the judge calls an LLM, set the endpoint per [configure-llm-endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md): `OPENAI_BASE_URL`/`OPENAI_MODEL`/`OPENAI_API_KEY` (plus optional `CACHE_DIR` for prompt caching), or an `llm-config.dev.yml` passed via `--llm-config`. Judges must read these from the injected `llm_config` parameter — never hardcoded.

## Step 5 — Scaffold a new judge
Check `judges/` for a directory beyond the example judges. If none exists, ask the developer for a judge name and create `judges/<name>/` with `__init__.py`, the judge module (a `judge()` returning a `Leaderboard`; optionally `create_nuggets()`/`create_qrels()`), and `workflow.yml`. Use `judges/complete_example/` (full protocol) or `judges/tinyjudge/` (minimal LLM) as templates, following [developing-practices](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-developing-practices.md).

## Step 6 — Point the developer at the details
- [run-workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md) — dev flags, variants, output files, multi-dataset runs
- [meta-evaluation](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) — checking judge quality against ground truth
- When ready to submit, use `/autojudge-submit`.

Stop here — implementing the judge's logic is the developer's work; offer help but do not write judge logic unless asked.
