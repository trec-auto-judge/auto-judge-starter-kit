# Developer How-To: Building a Judge from the Starterkit

A practical guide for building your own LLM judge by forking the
[auto-judge-starterkit](https://github.com/trec-auto-judge/auto-judge-starter-kit).
Covers the full lifecycle from fork to submission.

---

## Quick-Reference Checklist

Use this as a progress tracker. Each item links to an elaborated section below.

1. [Fork & clone](#1-fork--clone) the starterkit; set up `upstream` remote
2. [Update `pyproject.toml`](#2-update-pyprojecttoml) -- rename package, add your dependencies
3. [Update `README.md`](#3-update-readmemd) -- describe your approach
4. [Create your judge directory](#4-create-your-judge-directory) under `judges/`
5. [Implement your judge](#5-implement-your-judge) -- `judge()`, optionally `create_nuggets()` / `create_qrels()`
6. [Run your judge](#6-run-your-judge) on the kiddie dataset to smoke-test
7. [Meta-evaluate](#7-meta-evaluation) -- correlate with ground truth
8. [Submit](#8-submission) -- clean up example judges, package for TIRA

---

## 1. Fork & Clone

Fork from <https://github.com/trec-auto-judge/auto-judge-starter-kit>, then clone your fork:

```bash
git clone git@github.com:YOUR_USER/auto-judge-starter-kit.git my-judge
cd my-judge
```

Set up a remote to pull future starterkit updates:

```bash
git remote add upstream https://github.com/trec-auto-judge/auto-judge-starter-kit.git
git remote -v   # verify: origin = your fork, upstream = starterkit
```

To pull upstream changes later:

```bash
git fetch upstream
git merge upstream/main
```

**What comes from where:**
- **Upstream (starterkit repo)** provides template structure, example judges, test data, and build config.
- **Library updates** (`autojudge-base`, `minima-llm`, etc.) come via `pip`/`uv pip install --upgrade`. The starterkit pins `autojudge-base>=0.3.2`; pulling upstream gets template changes, not library upgrades.


## 2. Update `pyproject.toml`

Open `pyproject.toml` and make these changes:

| Field | Change to |
|-------|-----------|
| `name` | Your project name (e.g., `"my-awesome-judge"`) |
| `description` | One-line summary of your approach |
| `authors` | Your name / team |
| `project.urls` | Your fork's URL |

**Add your dependencies** under `[project] > dependencies`. For example, if your judge uses DSPy and LiteLLM:

```toml
dependencies = [
    "autojudge-base>=0.3.2",   # keep this -- core framework
    "tqdm>=4.0",                # keep this
    "dspy>=3.0",                # your additions
    "litellm>=1.0",
]
```

**Keep these unchanged:**
- `[tool.setuptools.packages.find]` with `include = ["judges*"]` -- this is how your judge package gets discovered
- The optional dependency groups (`test`, `minima-llm`, `evaluate`, etc.) unless you need to modify them

After editing, refresh your environment:

```bash
uv pip install -e '.[all]' --refresh
```


## 3. Update README.md

Replace the starterkit overview with your project's description:

- Motivation and approach of your judge
- Citations / references for your method
- Your judge's variants, settings, and how to interpret output
- Brief acknowledgment that this was built on the auto-judge-starterkit

Remove the descriptions of example judges (NaiveJudge, TinyJudge, etc.) since those won't ship with your submission.


## 4. Create Your Judge Directory

Create a new directory under `judges/`:

```
judges/myjudge/
  __init__.py
  my_judge.py       # your judge class(es)
  workflow.yml       # workflow configuration
```

Don't forget to `git add judges/myjudge/` -- new directories are untracked by default.

**Example judges** (`judges/naive/`, `judges/tinyjudge/`, `judges/complete_example/`, `judges/pyterrier_retrieval/`) are useful as reference during development. **Delete them before submission** (see [Section 8](#8-submission)).


## 5. Implement Your Judge

### Minimal Judge (Leaderboard Only)

If your judge only produces a leaderboard (no nuggets, no qrels), you need one method:

```python
from autojudge_base import Leaderboard, LeaderboardBuilder, LeaderboardSpec, MeasureSpec

MY_SPEC = LeaderboardSpec(measures=(MeasureSpec("MY_SCORE"),))

class MyJudge:
    def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
        builder = LeaderboardBuilder(MY_SPEC)
        for response in rag_responses:
            score = evaluate_response(response)  # your logic
            builder.add(
                run_id=response.metadata.run_id,
                topic_id=response.metadata.topic_id,
                values={"MY_SCORE": score},
            )
        topic_ids = [t.request_id for t in rag_topics]
        return builder.build(expected_topic_ids=topic_ids, on_missing="fix_aggregate")
```

With a minimal `workflow.yml`:

```yaml
judge_class: "judges.myjudge.my_judge:MyJudge"

create_nuggets: false
create_qrels: false
judge: true

settings:
  filebase: "{_name}"
```

### Full Protocol (Nuggets + Qrels + Leaderboard)

For a multi-phase judge that creates nuggets, then uses them for judging:

```python
from autojudge_base import NuggetBanks

class MyJudge:
    nugget_banks_type = NuggetBanks

    def create_nuggets(self, rag_responses, rag_topics, llm_config, **kwargs):
        # Generate nugget questions/claims for each topic
        # Return NuggetBanks or None
        return nugget_banks

    def create_qrels(self, rag_responses, rag_topics, llm_config, **kwargs):
        # Generate relevance judgments
        # Return Qrels or None
        return None

    def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
        nugget_banks = kwargs.get("nugget_banks")
        # Use nuggets to score responses
        return leaderboard
```

With the corresponding `workflow.yml`:

```yaml
nugget_class: "judges.myjudge.my_judge:MyJudge"
judge_class: "judges.myjudge.my_judge:MyJudge"

create_nuggets: true
judge: true
nugget_depends_on_responses: true
judge_uses_nuggets: true

settings:
  filebase: "{_name}"
```

You can also use separate classes for each phase (see `judges/complete_example/workflow.yml` for the modular pattern with `nugget_class`, `qrels_class`, and `judge_class`).

### Key References

| Resource | What it covers |
|----------|---------------|
| [autojudge-base workflow README](https://github.com/trec-auto-judge/auto-judge-base/tree/main/src/autojudge_base/workflow/README.md) | Quick-start template, lifecycle flags, variants, sweeps, settings |
| `judges/complete_example/` | Full working example with all three protocols |
| `judges/tinyjudge/` | Minimal LLM-based judge |
| [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base) | Data classes: `Report`, `Request`, `Leaderboard`, `NuggetBanks`, etc. |

### Important Conventions

- **Use `llm_config`**: Never hardcode API keys or endpoints. Use the `llm_config` parameter passed to your methods. See the README's [LLM Configuration](#) section.
- **Deterministic ordering**: Sort responses by `run_id` before creating comparison pairs to ensure consistent cache keys and reproducible results.
- **`{_name}` in filebase**: Using `filebase: "{_name}"` in workflow.yml automatically names output files after the variant/sweep name being run.


## 6. Run Your Judge

### Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -e '.[minima-llm,test]'
```

**Common pitfall:** `uv venv` creates a venv but does not activate it. If you skip `source .venv/bin/activate`, `uv pip install` may install into a different environment. Always activate first, then install.

### Run Against Kiddie Dataset

The `data/kiddie/` dataset is a small synthetic dataset included for smoke testing:

```bash
auto-judge run \
    --workflow judges/myjudge/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-kiddie/
```

Or use the included smoke-test script (runs NaiveJudge + meta-evaluation):

```bash
bash run_kiddie.sh
```

### LLM Configuration

If your judge makes LLM calls, configure via environment variables:

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"   # or your endpoint
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_API_KEY="sk-..."
export CACHE_DIR="./cache"                            # optional, enables prompt caching
```

Or via a YAML config file:

```yaml
# llm-config.yml
base_url: "http://localhost:8000/v1"
model: "llama-3.3-70b-instruct"
cache_dir: "./cache"
```

```bash
auto-judge run --llm-config llm-config.yml --workflow ...
```

Configuration layering: **env -> yaml -> cli** (each layer overrides the previous).

See [minima-llm](https://github.com/trec-auto-judge/minima-llm) for full backend documentation.

### Useful Development Flags

| Flag | Purpose |
|------|---------|
| `--limit-topics 2` | Run on a subset of topics |
| `--topic TOPIC_ID` | Run on one specific topic |
| `--variant NAME` | Run a specific variant from workflow.yml |
| `-S KEY=VALUE` | Override a shared setting |
| `-N KEY=VALUE` | Override a nugget setting |
| `-J KEY=VALUE` | Override a judge setting |

### Output Files

Given `filebase: "myjudge"` and `--out-dir ./output/`:

| File | When produced | Purpose |
|------|--------------|---------|
| `myjudge.judgment.json` | `judge: true` | Leaderboard scores (JSON) |
| `myjudge.eval.txt` | `judge: true` | Leaderboard in evaluation format (primary input for meta-evaluate) |
| `myjudge.nuggets.jsonl` | `create_nuggets: true` | Generated nugget banks |
| `myjudge.qrels` | `create_qrels: true` | Relevance judgments |
| `myjudge.config.yml` | always | Full config snapshot for reproducibility |


## 7. Meta-Evaluation

Install the evaluation extra:

```bash
uv pip install -e '.[evaluate]'
```

Run correlation against ground truth:

```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures --truth-header \
    --eval-format tot \
    --on-missing default \
    output-kiddie/*.eval.txt
```

**Note:** The kiddie dataset has synthetic/fake ground truth. It's useful for validating that the pipeline runs end-to-end, but not for drawing conclusions about judge quality.

For real evaluation, use actual TREC datasets with manual relevance judgments, or the shared evaluation service.


## 8. Submission

Before submitting:

1. **Delete example judges** that you didn't write:
   - `judges/naive/`
   - `judges/tinyjudge/`
   - `judges/complete_example/`
   - `judges/pyterrier_retrieval/`

2. **Verify a clean end-to-end run** of your judge

3. **Check that your workflow runs in a container** (for TIRA submission)

For detailed TIRA submission instructions (account setup, Docker packaging, upload), see [documentation/README.md](documentation/README.md).
