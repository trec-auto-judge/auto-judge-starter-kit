---
name: autojudge-setup
description: Set up a development environment to start building a new TREC AutoJudge from this starter kit. Use when the user wants to get the starter kit running, install dependencies, configure the LLM endpoint, or asks "how do I start / set up / begin developing my judge". Walks through venv, install, LLM endpoint configuration, and a verification run on the kiddie dataset.
---

# Set up an AutoJudge development environment

Walk the developer through this **interactively, one step at a time**. After each step, report what you found or did, then confirm before moving on. Do not run all steps in one shot.

The **canonical instructions live in the [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** — this skill drives its pages [setup-environment](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md) and [configure-llm-endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md); defer to them and do not contradict them. This repo's README holds the kit-specific reference (example judges, kiddie dataset, project structure). Building and running the judge belongs to `/autojudge-develop`; submitting belongs to `/autojudge-submit`.

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

## Step 3 — Make the fork theirs
Check `pyproject.toml`: if `name` still reads `auto-judge-starterkit`, walk through renaming it, updating `description`/`authors`/`project.urls`, and adding the judge's own dependencies — then reinstall with `uv pip install -e '.[all]' --refresh`. Keep `[tool.setuptools.packages.find]` with `include = ["judges*"]` unchanged.

## Step 4 — Configure the LLM endpoint
If the judge calls an LLM, set the endpoint per [configure-llm-endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md):
```bash
export OPENAI_BASE_URL=...  OPENAI_MODEL=...  OPENAI_API_KEY=...
export CACHE_DIR="./cache"   # optional, enables prompt caching
```
or an `llm-config.dev.yml` passed via `--llm-config`. Judges must read these from the injected `llm_config` parameter — never hardcoded. Any OpenAI-compatible client works (minima-llm, DSPy, litellm, raw); the canonical page explains the choices and how the endpoint is injected on TIRA.

## Step 5 — Verify the environment
```bash
bash run_kiddie.sh
pytest
```
Any failure here signals an environment problem to fix before writing judge code. Once green, hand off to `/autojudge-develop` for building and running the judge.
