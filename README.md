# AutoJudge Starterkit

A forkable template repository with example AutoJudge implementations for building custom judges.

## Quick Start

### Installation

1. Fork this repository
2. Clone

```bash
# Install autojudge-base (required dependency)
pip install git+https://github.com/trec-auto-judge/auto-judge-base.git

# Install in development mode
pip install -e .
```

**Optional Dependencies**

```
pip install -e ".[minima-llm]"      # Lightweight batteries-included LLM client (used by TinyJudge)
pip install -e ".[pyterrier]"       # For PyTerrier retrieval judge
pip install -e ".[test]"            # For running tests
```

**Optional: Meta-evaluation Tools**

To evaluate your judge's output against ground-truth leaderboards or qrels, install [autojudge-evaluate](https://github.com/trec-auto-judge/auto-judge-evaluate):

```
pip install autojudge-evaluate
```

This provides CLI commands for leaderboard correlation (`meta-evaluate`), inter-annotator agreement (`qrel-evaluate`), and format conversion (`eval-result`). See the [autojudge-evaluate README](https://github.com/trec-auto-judge/auto-judge-evaluate#readme) for usage.

### Implement Your Own Tiny Judge

See `judges/tinyjudge/` for a complete working example. For data class documentation (`Report`, `Request`, `Leaderboard`, etc.), see [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base).

The core pattern:

```python
import asyncio
from autojudge_base import Leaderboard, LeaderboardBuilder, LeaderboardSpec, MeasureSpec
from minima_llm import MinimaLlmConfig, MinimaLlmRequest, MinimaLlmResponse, OpenAIMinimaLlm

TINY_SPEC = LeaderboardSpec(measures=(MeasureSpec("FIRST_SENTENCE_RELEVANT"),))

class TinyJudge:
    """Implements LeaderboardJudgeProtocol - just needs a judge() method."""

    def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
        # Convert base config to full MinimaLlmConfig for backend features
        full_config = MinimaLlmConfig.from_dict(llm_config.raw) if llm_config.raw else MinimaLlmConfig.from_env()
        backend = OpenAIMinimaLlm(full_config)

        topic_titles = {t.request_id: t.title or "" for t in rag_topics}
        builder = LeaderboardBuilder(TINY_SPEC)

        for i, response in enumerate(rag_responses):
            sentence = response.responses[0].text if response.responses else ""
            query = topic_titles.get(response.metadata.topic_id, "")

            # generate() is async, so wrap with asyncio.run()
            resp = asyncio.run(backend.generate(MinimaLlmRequest(
                request_id=f"q{i}",
                messages=[
                    {"role": "system", "content": "You are a relevance evaluator. Respond with only 1 or 0."},
                    {"role": "user", "content": f"Is this relevant to the query?\n\nQuery: {query}\nSentence: {first_sentence}"},
                ],
            )))

            # Parse LLM response (robust to "1", "yes", "relevant", etc.)
            text = resp.text.strip().lower() if isinstance(resp, MinimaLlmResponse) else ""
            relevance = 1 if (text.startswith("1") or "relevant" in text) and "not" not in text else 0
            builder.add(
                run_id=response.metadata.run_id,
                topic_id=response.metadata.topic_id,
                values={"FIRST_SENTENCE_RELEVANT": relevance},
            )

        return builder.build(expected_topic_ids=list(topic_titles.keys()), on_missing="fix_aggregate")
```

Configure in `workflow.yml`:
```yaml
judge_class: "judges.tinyjudge.tiny_judge.TinyJudge"
```



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
from minima_llm import MinimaLlmConfig, OpenAIMinimaLlm

def judge(self, rag_responses, rag_topics, llm_config, **kwargs) -> Leaderboard:
    # Convert to full config for backend features (batching, retry, etc.)
    full_config = MinimaLlmConfig.from_dict(llm_config.raw) if llm_config.raw else MinimaLlmConfig.from_env()
    backend = OpenAIMinimaLlm(full_config)
    # ... your judge logic
```

The `llm_config` object is automatically populated from environment variables and optional config files.

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

## Test Dataset

### kiddie (`data/kiddie/`)

A small **synthetic dataset** for development and testing:
- 5 topics with simple queries
- 4 runs of varying quality
- Useful for validating workflow configurations and quick iteration

```bash
# Test your judge against kiddie
auto-judge run \
    --workflow judges/naive/workflow.yml \
    --rag-responses data/kiddie/responses/ \
    --rag-topics data/kiddie/topics.jsonl \
    --out-dir ./output/
```

The `data/kiddie/eval/` directory contains a synthetic ground-truth leaderboard for testing meta-evaluation:

```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures \
    --eval-format tot -i ./output/*eval.txt \
    --correlation kendall --on-missing default
```

For real evaluation, obtain official TREC datasets separately.

## Running Against Multiple Datasets

Use `run_all_datasets.py` to run a workflow against multiple datasets configured in a YAML file.

```bash
# Run against all datasets in data/datasets. 
python run_all_datasets.py --workflow judges/naive/workflow.yml --datasets data/datasets.yml
```

### Dataset Configuration (`datasets.yml`)

```yaml
datasets:
  - name: kiddie
    responses: data/kiddie/responses/
    topics: data/kiddie/topics.jsonl
    prio1_runs:           # Used with --runs prio1
      - run_good
      - run_medium
    assessed_topics:      # Used with --topics assessed
      - topic-1
      - topic-2
```


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
├── judges/
│   ├── complete_example/
│   │   ├── example_judge.py  # Modular judge implementation
│   │   └── workflow.yml     # Configuration
│   ├── naive/
│   │   ├── naive_baseline.py
│   │   └── workflow.yml
│   └── pyterrier_retrieval/
│       ├── retrieval_judge.py
│       └── workflow.yml
└── tests/
    └── test_examples.py     # Smoke tests
```

## Documentation

- See `judges/complete_example/README.md` for detailed protocol documentation
- See [autojudge-base](https://github.com/trec-auto-judge/auto-judge-base) for core data classes (`Report`, `Request`, `Leaderboard`, `NuggetBanks`, etc.) and protocol definitions

## License

MIT
