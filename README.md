# Auto-Judge Starterkit

A forkable template repository with example Auto-Judge implementations for building custom judges.



<p align="center">
   <img width=120px src="https://trec-auto-judge.cs.unh.edu/media/trec-auto-judge-logo-small.png">
   <br/>
   <br/>
   <a href="https://github.com/trec-auto-judge/auto-judge-starterkit/actions/workflows/tests.yml">
   <img alt="Tests" src="https://github.com/trec-auto-judge/auto-judge-starterkit/actions/workflows/tests.yml/badge.svg"/>
   </a>
   <a href="tests">
   <img alt="Coverage" src="tests/coverage.svg"/>
   </a>
   <br>
   <a href="https://trec-auto-judge.cs.unh.edu/">Web</a> &nbsp;|&nbsp;
   <a href="https://trec-auto-judge.cs.unh.edu/TREC_Auto_Judge.pdf">Proposal</a>
</p>

This repository contains the code used for evaluation and approaches for the TREC Auto-Judge shared tasks.

- [judges](judges/) the Auto-Judge implementations


We are developing a step-by-step guide on how to submit at [documentation/README.md](documentation/README.md).

## What is TREC AutoJudge?


TREC Auto-Judge offers the first rigorous, cross-task benchmark for
Large-Language-Model judges.

Large-Language-Model judges have emerged as a pragmatic solution when
manual relevance assessment is costly or infeasible. However, recent
studies reveal wide variation in accuracy across tasks, prompts, and
model sizes.

Currently, shared task organizers choose an LLM judge per track ad
hoc, risking inconsistent baselines and hidden biases.

Auto-Judge provides a test bed for comparing different LLM judge ideas 
across several tasks and correlating results against manually created relevance
judgments. AutoJudge provides a testbed to study emerging evaluation approaches,
as well as vulnerabilities of LLM judges, and the efficacy of safeguards for
those vulnerabilities.

This Auto-Judge evaluation script standardizes data handling and evaluation
across multiple shared tasks/TREC tracks that rely on LLM judging and
provides a centralized, comparative evaluation of LLM judges under realistic
conditions.



## What is this code for?

This project provides a means to evaluate AutoJudge approaches and provide a system ranking / leaderboard.

It will be used by TREC AutoJudge coordinators to score submissions. We encourage prospective participants to run this locally for method development.

This code will handle obtaining data sets (akin to `ir_datasets`), input/output and format conversions, and evaluation measures. 



## Quick Start

### Installation

1. Fork this repository
2. Clone
3. Create and activate venv
```
  uv venv
  source .venv/bin/activate   # Use this to restart your session
```
4. Minimal install via `uv pip`  (`pip` should also work)
```
uv pip install -e .
```

4. Optional: installation with all extra tools (includes `auto-judge-evaluate`  )
```
uv pip install -e ".[all]"
```



#### Selecting Tools and Dependencies

 `uv pip install -e ".[all]"` installs all of the below.
 
If you want to be selective in installing tools

* Auto-Judge Meta-Evaluation tools   `uv pip install -e ".[evaluate]"`
* Lightweight batteries-included LLM client (used by TinyJudge)   `uv pip install -e ".[minima-llm]"`
* PyTerrier retrieval  (used by PyTerrier retrieval judge) `uv pip install -e ".[pyterrier]"`
* Pytest unittest infrastructure `uv pip install -e ".[test]"  `

### Add your own Dependencies

Add your own dependencies in `pyproject.toml` under `[project] > dependencies`. 

After modification fetch dependencies, replacing `all` with selected tools and adding  `--refresh` to avoid stale package caches

```
uv pip install -e ".[all]" --refresh
```

#### Meta-Evaluation 
When installed with `[evaluate]`, the Auto-Judge meta-evaluation package provides CLI commands for
* leaderboard correlation: `auto-judge-evaluate  meta-evaluate --help`  
* inter-annotator agreement: `auto-judge-evaluate  qrel-evaluate --help`
* format conversion: `auto-judge-evaluate  eval-result --help`.

See the [autojudge-evaluate README](https://github.com/trec-auto-judge/auto-judge-evaluate#readme)  and built-in `--help`



### Implement Your Own Judge

 A judge is any class with a `judge()` method:

```python
from autojudge_base import Leaderboard, LeaderboardBuilder, LeaderboardSpec, MeasureSpec

MY_SPEC = LeaderboardSpec(measures=(MeasureSpec("MY_SCORE"),))

class MyJudge:
    def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
        builder = LeaderboardBuilder(MY_SPEC)

        for response in rag_responses:
            score = evaluate_response(response)  # your logic here
            builder.add(
                run_id=response.metadata.run_id,
                topic_id=response.metadata.topic_id,
                values={"MY_SCORE": score},
            )

        topic_ids = [t.request_id for t in rag_topics]
        return builder.build(expected_topic_ids=topic_ids, on_missing="fix_aggregate")
```

Register in `workflow.yml`:
```yaml
judge_class: "judges.myjudge.my_judge:MyJudge"
```


For data class documentation (`Report`, `Request`, `Leaderboard`, etc.), see [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base). 

For a full example with LLM calls, see `judges/tinyjudge/`.



### Running a Judge

```bash
auto-judge run \
    --workflow judges/tinyjudge/workflow.yml \
    --rag-responses /path/to/responses/ \
    --rag-topics /path/to/topics.jsonl \
    --out-dir ./output/

# See all options
auto-judge run --workflow judges/tinyjudge/workflow.yml --help
```

For variants, parameter sweeps, and advanced configurations, see the [workflow documentation](judges/complete_example/README.md).

## LLM Configuration

**Important:** Your judge must use the `llm_config` parameter passed to `judge()`. Do not hardcode endpoints or API keys.

The `llm_config` object (`LlmConfigBase`) provides basic fields (`model`, `base_url`, `cache_dir`) and stores the full YAML config in `.raw` to store additional parameters for your LLM backend (e.g. here `MinimaLlmConfig`):

```python
import asyncio
from minima_llm import MinimaLlmConfig, MinimaLlmRequest, OpenAIMinimaLlm

def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
    # Convert to full config for backend features (batching, retry, etc.)
    full_config = MinimaLlmConfig.from_dict(llm_config.raw)
    backend = OpenAIMinimaLlm(full_config)
    # ... your judge logic

    response = asyncio.run(backend.generate(MinimaLlmRequest(
        request_id="example",
        messages=[{"role": "user", "content": "Is this answer relevant? Reply 1 or 0."}],
    )))
    score = float(response.text.strip())
```

The `llm_config` object is automatically populated from environment variables and optional config files.

This example uses MinimaLlm, but you can use any LLM backend you prefer (including `litellm`).

### Environment Variables

Set these before running:

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"  # or your endpoint
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_API_KEY="sk-..."
export CACHE_DIR="./cache"  # optional, enables prompt caching
```

### Config File (optional)

Create `llm-config.yml`:

```yaml
base_url: "http://localhost:8000/v1"
model: "llama-3.3-70b-instruct"
cache_dir: "./cache"
```

Then pass it via CLI:

```bash
auto-judge run --llm-config llm-config.yml --workflow ...
```

Configuration layers: **env → yaml → cli** (each layer overrides the previous).

## Example Judges

### CompleteExampleJudge (`judges/complete_example/`)

A fully-documented example demonstrating all three protocols:
- `ExampleNuggetCreator`: Creates nugget questions for topics
- `ExampleQrelsCreator`: Creates relevance judgments
- `ExampleLeaderboardJudge`: Scores responses and produces leaderboard

No LLM calls - all logic is deterministic. Use this as a reference for building judges that use nuggets and qrels.

### NaiveJudge (`judges/naive/`)

A simple baseline judge that scores based on:
- Response text length
- Deterministic random score (for baseline comparison)

### PyTerrier Retrieval Judge (`judges/pyterrier_retrieval/`)

Uses PyTerrier retrieval models to score responses:
- Indexes responses per topic
- Runs multiple weighting models (BM25, TF-IDF, etc.)
- Ranks responses by retrieval score

Requires the `pyterrier` optional dependency.

## Test Dataset: kiddie (`data/kiddie/`)

A small **synthetic dataset** for development and testing:
- 5 topics with simple queries
- 4 runs of varying quality
- Useful for validating workflow configurations and quick iteration

```bash
# Run your judge against kiddie
auto-judge run \
    --workflow judges/naive/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-kiddie/
```

Or run the included smoke test script which also does meta-evaluation: `bash run_kiddie.sh`

## Running Against Multiple Datasets

Use `run_all_datasets.py` to run a workflow against multiple datasets configured in a YAML file:

```bash
python run_all_datasets.py --workflow judges/naive/workflow.yml --datasets data/datasets.yml
```

### Dataset Configuration (`datasets.yml`)

To run on more than just `kiddie`, add entries to `datasets.yml`:

```yaml
datasets:
  - name: kiddie
    responses: data/kiddie/runs/repgen/
    topics: data/kiddie/topics/kiddie-topics.jsonl
    prio1_runs:           # Used with --runs prio1
      - run1
      - run2
    assessed_topics:      # Used with --topics assessed
      - leaf
      - cloud
      - bee
```

## Meta-Evaluation

The `data/kiddie/eval/` directory contains a synthetic ground-truth leaderboard for testing meta-evaluation:

```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures --truth-header \
    --eval-format tot \
    --on-missing default \
    output-kiddie/*.eval.txt
```

For real evaluation, obtain official TREC datasets separately.


## Creating A More Elaborate Judge

1. **Copy an example**: Start from `judges/complete_example/` or `judges/naive/`

2. **Implement the protocol**: Your judge class needs:
   ```python
   from autojudge_base import AutoJudge, Leaderboard, Report, Request

   class MyJudge(AutoJudge):
       nugget_banks_type = NuggetBanks

       def create_nuggets(self, rag_responses, rag_topics, llm_config, **kwargs):
           # Optional: create nugget questions
           return None

       def create_qrels(self, rag_responses, rag_topics, llm_config, **kwargs):
           # Optional: create relevance judgments
           return None

       def judge(self, rag_responses, rag_topics, llm_config, **kwargs):
           # Required: produce leaderboard
           return leaderboard
   ```

3. **Configure workflow.yml**: Set lifecycle flags, settings, variants

4. **Run your judge**:
   ```bash
   auto-judge run --workflow judges/myjudge/workflow.yml ...
   ```

## Project Structure

```
auto-judge-starterkit/
├── pyproject.toml           # Dependencies and package config
├── README.md                # This file
├── run_kiddie.sh            # End-to-end smoke test on kiddie
├── judges/
│   ├── complete_example/    # Full protocol example (nuggets, qrels, leaderboard)
│   ├── naive/               # Simple baseline judge
│   ├── tinyjudge/           # Minimal LLM judge example
│   └── pyterrier_retrieval/ # PyTerrier retrieval judge
├── data/
│   └── kiddie/              # Synthetic test dataset
├── documentation/           # Submission guide
└── tests/
    └── test_examples.py     # Smoke tests
```

## Documentation

- See `judges/complete_example/README.md` for detailed protocol documentation
- See [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base) for core data classes (`Report`, `Request`, `Leaderboard`, `NuggetBanks`, etc.) and protocol definitions

## License

MIT
