# CLAUDE.md — Auto-Judge Starterkit

## Project Overview

This is a fork of the [auto-judge-starterkit](https://github.com/trec-auto-judge/auto-judge-starter-kit) for building a custom LLM judge for TREC Auto-Judge.

## Fork Checklist

**On first interaction**, check which of these steps have been completed and remind the developer of remaining items. Use `DEVELOPER_HOWTO.md` for detailed guidance on each step.

1. **pyproject.toml updated** — `name` changed from `auto-judge-starterkit`, own dependencies added
2. **README.md updated** — describes this judge's approach (not the starterkit examples)
3. **Judge directory created** — new directory under `judges/` with `__init__.py`, judge module, `workflow.yml`
4. **Judge implemented** — `judge()` method returns a `Leaderboard`; optionally `create_nuggets()` and `create_qrels()`
5. **Runs on kiddie dataset** — `auto-judge run --workflow judges/MYJUDGE/workflow.yml --rag-responses data/kiddie/runs/repgen/ --rag-topics data/kiddie/topics/kiddie-topics.jsonl --out-dir ./output-kiddie/`
6. **Meta-evaluation tested** — `auto-judge-evaluate meta-evaluate` produces output without errors
7. **Example judges deleted before submission** — remove `judges/naive/`, `judges/tinyjudge/`, `judges/complete_example/`, `judges/pyterrier_retrieval/`

If `pyproject.toml` still has `name = "auto-judge-starterkit"`, the fork has not been customized yet — prompt the developer to start with steps 1-3.

## Interactive Setup

On **"Setup checklist"**: Walk through the fork checklist interactively, one step at a time. For each step: inspect the repo to determine whether it's done, report what you found, then ask the developer how to proceed before moving on.

### Step 1: pyproject.toml
- Read `pyproject.toml`. Check if `name` is still `"auto-judge-starterkit"`.
- Check if any custom dependencies were added beyond `autojudge-base` and `tqdm`.
- Show the developer what needs changing. Reference: `DEVELOPER_HOWTO.md` section "2. Update pyproject.toml".
- Ask: *What should the package name be? What dependencies does your judge need?*

### Step 2: README.md
- Read `README.md`. Check if it still describes the starterkit examples (NaiveJudge, TinyJudge, etc.).
- Ask: *Can you describe your judge's approach so I can draft a README?*
- Reference: `DEVELOPER_HOWTO.md` section "3. Update README.md".

### Step 3: Judge directory
- List directories under `judges/`. Check for any directory beyond the starterkit examples (`naive/`, `tinyjudge/`, `complete_example/`, `pyterrier_retrieval/`).
- If none found, ask: *What should your judge be called? (This becomes the directory name under `judges/`.)*
- Create directory with `__init__.py` and a starter `workflow.yml`.
- Reference: `DEVELOPER_HOWTO.md` section "4. Create Your Judge Directory".

### Step 4: Judge implementation
- If judge directory exists, read the judge module. Check whether `judge()` method exists and returns a `Leaderboard`.
- Check for `create_nuggets()` and `create_qrels()` if workflow.yml enables them.
- Reference: `DEVELOPER_HOWTO.md` section "5. Implement Your Judge" for minimal and full protocol templates.
- Also read `judges/complete_example/` for the full protocol pattern, or `judges/tinyjudge/` for the minimal LLM pattern.
- Ask: *Does your judge need nuggets, qrels, or just a leaderboard?*

### Step 5: Run on kiddie
- Check if `output-kiddie/` exists and contains `.eval.txt` files from this judge.
- If not, show the run command with the developer's actual workflow.yml path.
- Reference: `DEVELOPER_HOWTO.md` section "6. Run Your Judge" for LLM config and dev flags.
- Reference: `run_kiddie.sh` for the smoke-test pattern.
- Ask: *Ready to run? Do you have your LLM endpoint configured?* (Show env var checklist if judge uses LLM.)

### Step 6: Meta-evaluation
- Check if `auto-judge-evaluate` is installed (`uv pip show autojudge-evaluate`).
- Check if meta-evaluate has been run (look for correlation output).
- Show the meta-evaluate command with the developer's actual output files.
- Reference: `DEVELOPER_HOWTO.md` section "7. Meta-Evaluation".
- Note: kiddie ground truth is synthetic — useful for pipeline validation only.

### Step 7: Submission cleanup
- List `judges/*/` directories. Flag any starterkit examples still present.
- Reference: `DEVELOPER_HOWTO.md` section "8. Submission" and `documentation/README.md` for TIRA instructions.
- Ask: *Ready to clean up example judges and prepare for submission?*

## Development Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e '.[minima-llm,test]'

# Run judge
auto-judge run --workflow judges/MYJUDGE/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-kiddie/

# Smoke test (NaiveJudge + meta-eval)
bash run_kiddie.sh

# Meta-evaluate
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures --truth-header \
    --eval-format tot --on-missing default \
    output-kiddie/*.eval.txt
```

## Key Conventions

- **Never hardcode API keys.** Use the `llm_config` parameter passed to judge methods.
- **Config layering:** env -> yaml -> cli (each overrides the previous).
- **`{_name}` in `filebase`:** Automatically names output files after the variant/sweep being run.
- **Sort by `run_id`** before creating comparison pairs for deterministic prompt ordering and cache consistency.

## Key References

- [DEVELOPER_HOWTO.md](DEVELOPER_HOWTO.md) — full step-by-step guide
- [autojudge-base workflow README](https://github.com/trec-auto-judge/auto-judge-base/tree/main/src/autojudge_base/workflow/README.md) — lifecycle flags, variants, sweeps
- [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base) — data classes (`Report`, `Request`, `Leaderboard`, `NuggetBanks`)
- [minima-llm](https://github.com/trec-auto-judge/minima-llm) — LLM backend configuration
- `judges/complete_example/` — full protocol example (nuggets + qrels + leaderboard)
- [documentation/README.md](documentation/README.md) — TIRA submission instructions
