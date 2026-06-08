---
configs:
- config_name: inputs
  data_files:
  - split: test
    path: ["runs/*/*.jsonl", "topics/topics.jsonl"]
- config_name: truths
  data_files:
  - split: test
    path: ["eval/ragtime.repgen.official.eval.jsonl"]

tira_configs:
  resolve_inputs_to: "."
  resolve_truths_to: "."
  baseline:
    link: https://github.com/trec-auto-judge/auto-judge-starter-kit/tree/main/
    command: auto-judge run --workflow /auto-judge/judges/naive/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir
    file: judges/naive/Dockerfile
    format:
      name: ["trec-eval-leaderboard"]
  input_format:
    name: "trec-rag-runs"
  truth_format:
    name: "arbitrary"
  evaluator:
    image: ghcr.io/trec-auto-judge/auto-judge-code/cli:0.0.3
    command: /evaluator.py --truth-format jsonl $inputDataset/eval/ragtime.repgen.official.eval.jsonl ${inputRun} ${outputDir}
---

# TBD

# Admin Section

Submit to TIRA via:

```
tira-cli dataset-submission --path ragtime25 --task trec-auto-judge --split test --dry-run
```
