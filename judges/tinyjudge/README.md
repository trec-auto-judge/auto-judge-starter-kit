# TinyJudge


Ensure environment variables are exported:

```
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=...
export OPENAI_MODEL=...
```

Submit to tira:

```
tira-cli code-submission \
    --dry-run \
    --path . \
    --file judges/tinyjudge/Dockerfile \
    --task trec-auto-judge \
    --dataset kiddie-20260605-training \
    --forward-environment-variable OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL \
    --command 'auto-judge run --workflow /auto-judge/judges/tinyjudge/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```
