---
configs:
- config_name: inputs
  data_files:
  - split: train
    path: ["runs/*/*.jsonl", "topics/*.jsonl"]
- config_name: truths
  data_files:
  - split: train
    path: ["topics/*.jsonl"]

tira_configs:
  resolve_inputs_to: "."
  resolve_truths_to: "."
  baseline:
    link: https://github.com/trec-auto-judge/auto-judge-starter-kit/tree/main/
    command: auto-judge run --workflow /auto-judge/judges/naive/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir
    format:
      name: ["trec-eval-leaderboard"]
  input_format:
    name: "trec-rag-runs"
  truth_format:
    name: "arbitrary"
  evaluator:
    image: ghcr.io/trec-auto-judge/auto-judge-code/cli:0.0.2
    command: trec-auto-judge evaluate --input ${inputRun}/*eval.txt --aggregate --output ${outputDir}/evaluation.prototext
---

# 2026 LongEval RAG Dataset



# Admin Section

Submit to TIRA via:

```
tira-cli dataset-submission --path longeval26-rag --task trec-auto-judge --split train --dry-run
```
