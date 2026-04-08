# CompleteExampleJudge

A fully-documented example demonstrating all three protocols:
- `ExampleNuggetCreator`: Creates nugget questions for topics
- `ExampleQrelsCreator`: Creates relevance judgments
- `ExampleLeaderboardJudge`: Scores responses and produces leaderboard

No LLM calls - all logic is deterministic. Use this as a reference for building judges that use nuggets and qrels.

## Usage
The `judges/complete_example/example_judge.py --help` command provides an overview of the usage. For instance, to process the spot-check dataset, please run:
```bash
judges/complete_example/example_judge.py judge --rag-responses data/kiddie/runs/repgen --rag-topics data/kiddie/topics/kiddie-topics.jsonl --output out/judges/example-judgments
```