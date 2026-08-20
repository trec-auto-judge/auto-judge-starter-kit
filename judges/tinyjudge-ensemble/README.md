# TinyJudgeEnsemble

`TinyJudgeEnsemble` is a minimal LLM-ensemble example judge for the Auto-Judge framework, built on top of `TinyJudge`.

It asks **three independently configured LLMs** whether the first sentence of each response is relevant to the topic and writes a leaderboard with four measures:

- `FIRST_SENTENCE_RELEVANT_LLM1`: binary relevance score from LLM1 (`0` or `1`)
- `FIRST_SENTENCE_RELEVANT_LLM2`: binary relevance score from LLM2 (`0` or `1`)
- `FIRST_SENTENCE_RELEVANT_LLM3`: binary relevance score from LLM3 (`0` or `1`)
- `FIRST_SENTENCE_RELEVANT_AVG`: average of the three scores above (`0.0`-`1.0`)

The judge runs all requests for one LLM (a batch), then moves to the next LLM, in a plain `for` loop over the three ensemble members - it does not interleave calls across LLMs.

Each LLM's `minima_llm` config is **always constructed explicitly** from its own environment variables, never via `MinimaLlmConfig.from_env()` or `llm_config.raw`. This keeps the three endpoints unambiguous even though they share the same process.

## Requirements

Install the project with the TinyJudge dependencies:

```bash
uv pip install -e ".[minima-llm,evaluate]"
```

TinyJudgeEnsemble expects these environment variables:

- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` for LLM1
- `OPENAI_API_KEY_2`, `OPENAI_BASE_URL_2`, `OPENAI_MODEL_2` for LLM2
- `OPENAI_API_KEY_3`, `OPENAI_BASE_URL_3`, `OPENAI_MODEL_3` for LLM3
- `CACHE_DIR` for the shared Minima LLM cache

`CACHE_DIR` is especially important for repeatability and for resuming runs without additional API costs for already cached LLM requests. All three LLMs share the same `CACHE_DIR`; their cache entries do not collide because the cache key includes each LLM's own `base_url`/`model`.

## Run locally

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=...
export OPENAI_MODEL=...

export OPENAI_API_KEY_2=...
export OPENAI_BASE_URL_2=...
export OPENAI_MODEL_2=...

export OPENAI_API_KEY_3=...
export OPENAI_BASE_URL_3=...
export OPENAI_MODEL_3=...

export CACHE_DIR=./cache-tinyjudge-ensemble

auto-judge run \
    --workflow judges/tinyjudge-ensemble/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir ./output-tinyjudge-ensemble/
```

Meta-evaluate the produced leaderboard:

```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures \
    --truth-header \
    --eval-format ir_measures \
    --on-missing default \
    output-tinyjudge-ensemble/tinyjudge-ensemble.eval.txt
```

See `judges/tinyjudge/README.md` for details on running from a downloaded cache - the same steps apply here.

## Submit to TIRA

For code submission, make sure Docker or Podman and `tira-cli` are installed.

Export the LLM configuration first (they are only used on your machine):

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=...
export OPENAI_MODEL=...

export OPENAI_API_KEY_2=...
export OPENAI_BASE_URL_2=...
export OPENAI_MODEL_2=...

export OPENAI_API_KEY_3=...
export OPENAI_BASE_URL_3=...
export OPENAI_MODEL_3=...
```

Then run the dry run from the repository root:

```bash
tira-cli code-submission \
    --dry-run \
    --path . \
    --cache-behaviour deterministic \
    --mount-cache '$CACHE_DIR=EMPTY_DIR' \
    --task trec-auto-judge \
    --dataset kiddie-20260605-training \
    --forward-environment-variable OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL OPENAI_API_KEY_2 OPENAI_BASE_URL_2 OPENAI_MODEL_2 OPENAI_API_KEY_3 OPENAI_BASE_URL_3 OPENAI_MODEL_3 \
    --command 'auto-judge run --workflow /auto-judge/judges/tinyjudge-ensemble/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```

If the dry run succeeds, remove `--dry-run` to submit the AutoJudge system.

`--cache-behaviour deterministic` tells TIRA that repeated runs with the same cache should produce the same output, which is useful to know for reproducibility.

For the full submission workflow, see the
[TIRA participant documentation](https://docs.tira.io/participants/participate.html#prepare-your-submission).
