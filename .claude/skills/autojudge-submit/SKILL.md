---
name: autojudge-submit
description: Submit a TREC AutoJudge to TIRA via a code submission. Use when the user wants to submit, upload, or run tira-cli code-submission for their judge, or asks "how do I submit to TIRA / ship my judge". Walks through the pre-submission checklist, a local dry-run, and the real upload.
---

# Submit your AutoJudge to TIRA

Walk the developer through this **interactively, one step at a time**, confirming before each step.

The **canonical instructions live in the [TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** — this skill drives its [submit-to-tira](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md) page (with [prompt-cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md) for the cache flags); defer to it for account setup, authentication, and any detail not repeated here, and do not contradict it. This repo's README holds the kit-specific reference. To set up a dev environment first, use `/autojudge-setup`.

## Step 1 — Pre-submission checklist
- **Clean repository.** `git status --porcelain` must print nothing. Only *committed* state on the *currently checked-out branch* is submitted — commit or `.gitignore` anything that shows up.
- **Tests pass.** Run `pytest` — it must complete without failures.
- **Example judges removed.** Delete the starter-kit example judges the developer did not write.
- **Docker/podman running.** The daemon must be up; `tira-cli code-submission` builds and tests the image locally before uploading. (Podman `policy.json` fix: see the canonical page.)
- **No secrets in the image.** Never `COPY`/`ADD` API keys into the Dockerfile; the judge runs in a sandbox without internet and gets its LLM endpoint via forwarded environment variables.

## Step 2 — Authenticate
```bash
pip3 install --upgrade tira
tira-cli login --token <AUTH-TOKEN>
tira-cli verify-installation
```
The `<AUTH-TOKEN>` comes from TIRA: task page → submit → Code Submission → "from my local machine" (screenshots on the canonical page).

## Step 3 — Dry run (builds + tests locally, uploads nothing)
```bash
export OPENAI_API_KEY=...  OPENAI_BASE_URL=...  OPENAI_MODEL=...
tira-cli code-submission \
    --dry-run --path . \
    --cache-behaviour deterministic --mount-cache '$CACHE_DIR=EMPTY_DIR' \
    --forward-environment-variable OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL \
    --task trec-auto-judge --dataset kiddie-20260605-training \
    --command 'auto-judge run --workflow /auto-judge/judges/<your-judge>/workflow.yml --variant <name> --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```
- `--variant <name>` and every other `auto-judge run` flag belong **inside** the quoted `--command` (there is no `tira-cli --variant` flag).
- The cache flags apply to LLM judges that cache; judges without an LLM can omit them ([details](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md)).

## Step 4 — Submit for real
When the dry run passes, remove `--dry-run` and rerun the same command to upload. Repeat per judge/variant.

If anything fails or the developer cannot run Docker locally, point them to the private TIRA chat (Maik, Laura cc'd) described in the canonical page's prerequisites.
