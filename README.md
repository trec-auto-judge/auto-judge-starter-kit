# AutoJudge Starterkit

A forkable template repository with example AutoJudge implementations for building custom judges.

## Quick Start

### Installation

```bash
# Clone this repository
git clone https://github.com/trec-autojudge/auto-judge-starterkit.git
cd auto-judge-starterkit

# Install autojudge-base (required dependency)
pip install git+https://github.com/trec-auto-judge/auto-judge-base.git

# Install in development mode
pip install -e .

# Or with optional dependencies
pip install -e ".[minima-llm]"      # For LLM-based judges
pip install -e ".[pyterrier]"       # For PyTerrier retrieval judge
pip install -e ".[test]"            # For running tests
```

### Running a Judge

```bash
# Run the minimal judge
auto-judge run \
    --workflow judges/minimaljudge/workflow.yml \
    --rag-responses /path/to/responses/ \
    --rag-topics /path/to/topics.jsonl \
    --out-dir ./output/

# Run with a specific variant
auto-judge run \
    --workflow judges/minimaljudge/workflow.yml \
    --variant strict \
    --rag-responses /path/to/responses/ \
    --rag-topics /path/to/topics.jsonl \
    --out-dir ./output/

# See all options
auto-judge run --workflow judges/minimaljudge/workflow.yml --help
```

## Example Judges

### MinimalJudge (`judges/minimaljudge/`)

A fully-documented example demonstrating the modular protocol pattern:
- `MinimalNuggetCreator`: Creates nugget questions for topics
- `MinimalQrelsCreator`: Creates relevance judgments
- `MinimalLeaderboardJudge`: Scores responses and produces leaderboard

No LLM calls - all logic is deterministic. Use this as a starting template.

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

## Creating Your Own Judge

1. **Copy an example**: Start from `judges/minimaljudge/` or `judges/naive/`

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
│   ├── minimaljudge/
│   │   ├── minimal_judge.py # Modular judge implementation
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

- See `judges/minimaljudge/README.md` for detailed protocol documentation
- See the [autojudge-base](https://github.com/trec-autojudge/auto-judge-base) repository for core API docs

## License

MIT
