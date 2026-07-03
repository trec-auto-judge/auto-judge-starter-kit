# Naive Judge

A naive judge that just uses the length of responses respectively a random score as evaluation measure.

This judge is intended to showcase the AutoJudge framework and submission process to TIRA in a minimal example without dependencies to an LLM or a nugget base.

# Local Usage

You can run the naive judge on the kiddie dataset via (the PYTHONPATH environment variable ensures that the packages are found):

```
PYTHONPATH=../.. \
auto-judge run \
    --workflow workflow.yml \
    --rag-responses ../../data/kiddie/runs/repgen/ \
    --rag-topics ../../data/kiddie/topics/kiddie-topics.jsonl \
    --out-dir my-results
```

Now, we can evaluate the results:

```
auto-judge-evaluate meta-evaluate \
    --truth-leaderboard ../../data/kiddie/eval/kiddie_fake.eval.ir_measures.txt \
    --truth-format ir_measures \
    --eval-format ir_measures \
    --input my-results/naive.eval.txt
```


The output should contain something like:

```
     Judge TruthMeasure EvalMeasure   kendall   pearson  spearman   tauap_b  kendall@10
naive.eval    RELEVANCE      LENGTH -0.333333 -0.482239      -0.6 -0.111111   -0.333333
naive.eval    RELEVANCE      RANDOM -0.333333 -0.640714      -0.4 -0.444444   -0.333333
```


# Submit to TIRA

To submit your solution to TIRA, you can either contact [Maik](https://www.tira.io/u/maik_froebe) and give Maik access to your repository, Maik can submit the solution to TIRA. To submit the solution yourself, please [install docker on your machine](https://docs.docker.com/engine/install/) (alternatively, you can use podman) and the tira-cli (via `pip3 install tira`).

We use code-submissions, if you want to submit from your machine, please [skim over the prepare your submission section of the documentation](https://docs.tira.io/participants/participate.html#prepare-your-submission) as this explains the steps that are done by the tira-cli.

For the Naive Judge, please run the following code submission command from the root of this repository:

```
tira-cli code-submission \
            --dry-run \
            --path . \
            --task trec-auto-judge \
            --dataset kiddie-20260605-training \
            --command 'auto-judge run --workflow /auto-judge/judges/naive/workflow.yml --rag-responses $inputDataset/runs/*/ --rag-topics $inputDataset/topics/*.jsonl --out-dir $outputDir'
```

If everything worked, the output should look like this:


remove the `--dry-run` flag to actually submit the auto judge to TIRA.

# Execution of Publically Available AutoJudge Systems

The goal is that after we have collected the autoJudge systems we would like to make them publically available in cases where this is possible so that also others can easily run an auto judge on their data. We also run the submitted AutoJudge systems at scale on all RAG tasks that we have. If applicable, we will also run the AutoJudge systems on different large language models (this is not applicable here, as the naive judge does not use an LLM). This naive autojudge system is already submitted and published to TIRA (you can submit it again to ensure that everything works on your side), the command to run the AutoJudge as it was submitted to tira would be:

```
tira-cli run local --approach trec-auto-judge/webis/Naive-AutoJudge --input kiddie-20260605-training
```

The output would look like:



```
