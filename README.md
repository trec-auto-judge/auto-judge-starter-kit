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

## Documentation

The **[TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** is the canonical guide, one page per activity:

| # | Activity | In Claude Code |
|---|----------|----------------|
| 1 | [Set up your dev environment](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md) | `/autojudge-setup` |
| 2 | [Configure your LLM endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md) | |
| 3 | [Developing practices](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-developing-practices.md) | |
| 4 | [Run workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md) | |
| 5 | [Prompt cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md) | |
| 6 | [Meta-evaluation](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) | |
| 7 | [Submit to TIRA](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md) | `/autojudge-submit` |

The two [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills, shipped in this repo under `.claude/skills/`, walk you through setup and submission interactively — the HowTo pages cover the same ground for manual use.

In short, getting started means: fork this repo, `uv venv && source .venv/bin/activate && uv pip install -e '.[all]'`, verify with `bash run_kiddie.sh`, and build your judge under `judges/` — with the details in the HowTo pages above.

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

## What is this code for?

This project provides a means to evaluate AutoJudge approaches and provide a system ranking / leaderboard.

It will be used by TREC AutoJudge coordinators to score submissions. We encourage prospective participants to run this locally for method development.

This code will handle obtaining data sets (akin to `ir_datasets`), input/output and format conversions, and evaluation measures.

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

### TinyJudge (`judges/tinyjudge/`)

A minimal LLM-based judge with prompt caching — the smallest realistic template for an LLM judge.

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

## Project Structure

```
auto-judge-starterkit/
├── pyproject.toml           # Dependencies and package config
├── README.md                # This file
├── run_kiddie.sh            # End-to-end smoke test on kiddie
├── run_all_datasets.py      # Batch driver: one run per dataset in datasets.yml
├── judges/
│   ├── complete_example/    # Full protocol example (nuggets, qrels, leaderboard)
│   ├── naive/               # Simple baseline judge
│   ├── tinyjudge/           # Minimal LLM judge example
├── data/
│   └── kiddie/              # Synthetic test dataset
├── .claude/skills/          # /autojudge-setup and /autojudge-submit walkthroughs
└── tests/
    └── test_examples.py     # Smoke tests
```

## License

MIT
