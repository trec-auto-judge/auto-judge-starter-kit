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

## Working with restricted evaluation data

Evaluation datasets are anonymised, and only the first 10 topics of a dataset's
topics file are open to inspection by you or your coding agent. The judge itself
is unrestricted — it reads every run and topic, and that is the task. See the
[data-handling policy](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/data-policy.md)
(also shipped with the dataset).

When a judge crashes on a restricted record, do not open the record. Use `scrub`
(from `autojudge-base`) to turn it into something safe to look at:

```bash
scrub --topic 37 --run plum runs/repgen/plum      # tier 1: structure only
scrub --chars --topic 37 runs/repgen/plum         # tier 2: + lengths, punctuation
```

Tier 1 keeps keys, types, nesting and list lengths and replaces every string with
`wiffle waffle` — enough for missing fields, wrong types and bad nesting, and safe
to commit as a fixture. Tier 2 additionally preserves string lengths and every
non-alphanumeric character, so encoding, parsing and length bugs reproduce; it
leaks a run's formatting template, so do not commit it or compare it across runs.
If neither reproduces the bug, hand the exception, stack trace and record id to
your developer — the bug is content-dependent, which is exactly the case where
you do not look.

`scrub` is the only sanctioned path from a restricted record to your view. Do not
write your own, and do not apply it partially. Every invocation is appended to
`scrub-log.jsonl` (counts, not values).


## Documentation

The **[TREC AutoJudge Participant HowTo](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/README.md)** is the canonical guide, one page per activity:

| # | Activity | In Claude Code |
|---|----------|----------------|
| 1 | [Set up your dev environment](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md) | `/autojudge-setup` |
| 2 | [Configure your LLM endpoint](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/02-configure-llm-endpoint.md) | `/autojudge-setup` |
| 3 | [Develop an AutoJudge](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/03-develop-an-autojudge.md) | `/autojudge-develop` |
| 4 | [Run workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md) | `/autojudge-develop` |
| 5 | [Prompt cache](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/05-prompt-cache.md) | `/autojudge-develop` |
| 6 | [Meta-evaluation](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/06-meta-evaluation.md) | `/autojudge-develop` |
| 7 | [Submit to TIRA](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md) | `/autojudge-submit` |

The three [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills, shipped in this repo under `.claude/skills/`, walk you through every activity interactively — the HowTo pages cover the same ground for manual use.

In short, getting started means: clone this repo into your own repository (see the HowTo's setup page), `uv venv && source .venv/bin/activate && uv pip install -e '.[all]'`, verify with `bash run_kiddie.sh`, and build your judge under `judges/` — with the details in the HowTo pages above.

This repository stays a **bare-bones template**: to build on it you **must** make it your own — change the project `name` in `pyproject.toml`, replace this README with a description of your judge, and create your own `judges/<yourjudge>/` entry (deleting the examples before submission).

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

## Real Evaluation Datasets

The real evaluation runs come from a password-protected release. `fetch_datasets.py` downloads them into `./local-data/` (gitignored) — see [setup step 5](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/01-setup-environment.md#step-5--fetch-the-evaluation-datasets) for the credentials. For example, to obtain the TREC 2026 AutoJudge test set:

```bash
./fetch_datasets.py --test-2026
```

`run_all_datasets.py` then runs your judge — one `auto-judge run` per dataset listed in `datasets.yml`:

```bash
python run_all_datasets.py --workflow judges/naive/workflow.yml \
    --dataset rag26-generation --dataset ragtime26-repgen
```

Drop `--dataset` to sweep every fetched dataset. Useful switches: `--dry-run` prints the commands without executing, `--meta-evaluate` correlates against the dataset's truth file, `--upload-tira` uploads the leaderboards to TIRA. Details in [run workflows](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/04-run-workflows.md) and [submit to TIRA](https://github.com/trec-auto-judge/.github/blob/main/profile/howto/07-submit-to-tira.md).

## Project Structure

```
auto-judge-starterkit/
├── pyproject.toml           # Dependencies and package config
├── README.md                # This file
├── run_kiddie.sh            # End-to-end smoke test on kiddie
├── run_all_datasets.py      # Batch driver: one run per dataset in datasets.yml
├── fetch_datasets.py        # Download the released datasets into ./local-data/
├── check_container_setup.sh # Preflight: is Docker/podman ready for a code submission?
├── datasets.yml             # Dataset registry used by run_all_datasets.py
├── judges/
│   ├── complete_example/    # Full protocol example (nuggets, qrels, leaderboard)
│   ├── naive/               # Simple baseline judge
│   ├── tinyjudge/           # Minimal LLM judge example
├── data/
│   └── kiddie/              # Synthetic test dataset
├── local-data/              # Fetched evaluation datasets (gitignored)
├── .claude/skills/          # /autojudge-setup, /autojudge-develop, /autojudge-submit walkthroughs
└── tests/
    └── test_examples.py     # Smoke tests
```

## License

MIT
