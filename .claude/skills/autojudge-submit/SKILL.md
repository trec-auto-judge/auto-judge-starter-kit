---
name: autojudge-submit
description: Submit a TREC AutoJudge to TIRA via a code submission. Use when the user wants to submit, upload, or run tira-cli code-submission for their judge, or asks "how do I submit to TIRA / ship my judge". Walks through local verification, LLM environment, git hygiene, authentication, a dry-run, and the real upload.
---

# Submit your AutoJudge to TIRA

Walk the developer through this **interactively, one step at a time**, confirming before each step. At every step, actively **check** the condition rather than just stating it, and help fix what fails.

The **canonical instructions live in the [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** — this skill drives its [submit-to-tira](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md) page (with [prompt-cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md) for the cache flags); defer to it for account setup, authentication, and any detail not repeated here, and do not contradict it. To set up a dev environment first, use `/autojudge-setup`.

## Step 1 — LLM environment and local verification
Check whether `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` are set (`env | grep OPENAI`, never print the key's value) — if not, remind the developer to load them, plus `CACHE_DIR` for caching judges, before anything else. Then verify the judge end to end locally:
```bash
bash run_kiddie.sh
pytest
```
Fixing failures locally beats debugging them through a Docker build, and `tira-cli` runs the test suite during submission, so red tests block it. Both must be green before continuing — note the starter-kit tests also enforce up-to-date framework versions (`autojudge-base`, `tira`) and template customization (project name + README).

## Step 2 — Git hygiene (help, don't just check)
Run `git status --porcelain`. When output appears, triage it with the developer instead of just reporting it:
- build artifacts, caches, venvs, output directories → append to `.gitignore` and commit that change
- genuine source/config changes → commit them
- anything surprising → ask before touching it
Only the *committed* state of the *current branch* is submitted. Run `git branch --show-current`; recommend `main`, and confirm intent if they are on another branch. Also confirm example judges the developer did not write are deleted, and check `pyproject.toml`: a `name` still reading `auto-judge-starterkit` means the template was never made their own — walk through renaming it, replacing the README, and owning a `judges/` entry before submitting.

## Step 3 — tira-cli, Docker, authentication
```bash
uv pip install --upgrade tira        # inside the venv; pip3 works outside
tira-cli login --token <AUTH-TOKEN>
tira-cli verify-installation --task trec-auto-judge --team <TEAM>
```
The `<AUTH-TOKEN>` comes from TIRA: task page → submit → Code Submission → "from my local machine" (screenshots on the canonical page). The scoped verification confirms Docker/podman is reachable AND that login and team registration line up. Docker daemon problems or the podman `policy.json` error: see the canonical page's Step 2.

## Step 4 — Dry run (builds + tests locally, uploads nothing)
```bash
tira-cli code-submission \
    --dry-run --path . \
    --cache-behaviour deterministic --mount-cache '$CACHE_DIR=EMPTY_DIR' \
    --forward-environment-variable OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL \
    --task trec-auto-judge --dataset kiddie-20260605-training \
    --command 'auto-judge run --workflow /auto-judge/judges/<your-judge>/workflow.yml --variant <name> --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```
- `--variant <name>` and every other `auto-judge run` flag belong **inside** the quoted `--command` (there is no `tira-cli --variant` flag).
- tira's local test runs without network by default: add `--allow-network` when the judge calls an external endpoint, or rely on a mounted warm cache (no network needed on hits).
- The cache flags apply to LLM judges that cache; judges without an LLM can omit them ([details](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md)). For a fast dry-run, offer to mount the developer's populated cache instead: `--mount-cache '$CACHE_DIR=cache'` (same `OPENAI_MODEL` as when the cache was built; the container writes to a copy). The variable must be whatever this judge actually reads — `CACHE_DIR` by convention, but other backends may use different/additional variables (repeat `--mount-cache` per variable). Keep `EMPTY_DIR` for the real submission (cold-start proof).

## Step 5 — Submit for real
When the dry run passes, rerun the same command without `--dry-run` to upload. Repeat per judge/variant. The canonical page's "A complete session" section shows a full real transcript.

If anything fails or the developer cannot run Docker locally, point them to the private TIRA chat (Maik, Laura cc'd) described in the canonical page's prerequisites.
