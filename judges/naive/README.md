# Naive Judge

`NaiveJudge` is a minimal example judge for the Auto-Judge framework. The naive judge scores each response with two naive measures:

- `LENGTH`: the number of whitespace-delimited words in the response
- `RANDOM`: a deterministic pseudo-random baseline score

This judge is useful for understanding the workflow end to end without introducing LLM dependencies, nugget generation, or qrels.


## Run locally

These commands assume you are in the repository root and have already installed the project in editable mode, for example:

```bash
uv pip install -e .
```

Run the judge on the kiddie dataset:

```bash
auto-judge run \
    --workflow judges/naive/workflow.yml \
    --rag-responses data/kiddie/runs/repgen/ \
    --rag-topics data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir output-naive/
```

Evaluate the produced leaderboard:

```bash
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures \
    --truth-header \
    --eval-format ir_measures \
    --on-missing default \
    output-naive/naive.eval.txt
```

Example output:

```text
     Judge TruthMeasure EvalMeasure   kendall   pearson  spearman   tauap_b  kendall@10
naive.eval    RELEVANCE      LENGTH -0.333333 -0.482239      -0.6 -0.111111   -0.333333
naive.eval    RELEVANCE      RANDOM -0.333333 -0.640714      -0.4 -0.444444   -0.333333
```

The kiddie dataset is synthetic, so these numbers are not meaningful, but still can help to easily verify that a judge produces a valid output.


## Submit to TIRA

To submit the judge to tira, first make sure Docker (or Podman) and `tira-cli` are installed.

Run this from the repository root:

```bash
tira-cli code-submission \
    --dry-run \
    --path . \
    --task trec-auto-judge \
    --dataset kiddie-20260605-training \
    --command 'auto-judge run --workflow /auto-judge/judges/naive/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```

If everything worked, the output should look like this:

<img width="1069" height="129" alt="Screenshot_20260703_160326" src="https://github.com/user-attachments/assets/8713334b-c27e-4fa9-8db4-b91521cd6a53" />

If the dry run succeeds, remove `--dry-run` to submit the AutoJudge system.

For more details on the submission workflow and on how to prepare your software, please have a short look at the [TIRA participant documentation](https://docs.tira.io/participants/participate.html#prepare-your-submission). (The AutoJudge starter kit is already developed so that everything should be compatible with TIRA without much effort.)

## Run a published Naive Judge

This naive judge is already published on TIRA and can also be executed locally via `tira-cli`:

```bash
tira-cli run local \
    --approach trec-auto-judge/webis/Naive-AutoJudge \
    --input kiddie-20260605-training
```

The output should look like:

<img width="1030" height="393" alt="Screenshot_20260703_160041" src="https://github.com/user-attachments/assets/7e0d8348-d5d2-48b7-b986-33b0a2a91039" />

(This is similar how we then run private submitted AutoJudges on the test datasets, potentially via different LLMs.)
