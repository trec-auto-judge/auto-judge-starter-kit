#!/usr/bin/env python3
from subprocess import check_output
import click
from glob import glob
import json
from tira.io_utils import to_prototext
import yaml
from pathlib import Path


def find_leaderboard(input_dir):
    matches = glob(f"{input_dir}/*.txt")
    if len(matches) == 1:
        return matches[0]
    matches = glob(f"{input_dir}/*eval.txt")
    if len(matches) == 1:
        return matches[0]


def extract_llm(input_dir):
    matches = glob(f"{input_dir}/*.config.yml")
    ret = set()
    for i in matches:
        i = yaml.safe_load(Path(i).read_text())
        if i and "llm_model" in i:
            ret.add(i["llm_model"])

    ret = list(ret)
    if len(ret) == 1:
        return ret[0]
    elif len(ret) > 1:
        return ret
    else:
        return None

@click.command()
@click.option("--truth-format", type=str, default="ir_measures")
@click.option("--eval-format", type=str, default="ir_measures")
@click.argument("truth_leaderboard", required=True)
@click.argument("input_directory", required=True)
@click.argument("output_directory", required=True)
def main(truth_format, eval_format, truth_leaderboard, input_directory, output_directory):    
    leaderboard_to_eval = find_leaderboard(input_directory)
    if leaderboard_to_eval is None:
        print(f"No leaderboard found in {input_directory}")
        return

    cmd = f"auto-judge-evaluate meta-evaluate --truth-leaderboard {truth_leaderboard} --truth-format {truth_format} --eval-format {eval_format} -i {leaderboard_to_eval} --on-missing warn --output {output_directory}/correlations.jsonl"

    print(cmd)
    check_output(["bash", "-c", f"yes| {cmd}"])
    
    scores = {"kendall": [], "tauap_b": []}
    measures = set()

    with open(f"{output_directory}/correlations.jsonl", "r") as f:
        for l in f:
            l = json.loads(l)
            print(l)
            measures.add(l["EvalMeasure"])
            for s in scores:
                scores[s].append(l[s] if l[s] is not None else 0)
    
    ret = {"Eval-Measures": len(measures)}

    if extract_llm(input_directory):
        ret["Model"] = extract_llm(input_directory)

    for s in sorted(scores.keys()):
        ret[f"Max ({s})"] = max(scores[s])
        ret[f"Min ({s})"] = min(scores[s])

    print(ret)

    with open(f"{output_directory}/evaluation.prototext", "w") as f:
        f.write(to_prototext([ret]))
            

if __name__ == '__main__':
    main()

#yes | ../kiddie/eval/kiddie_fake.eval.ir_measures.txt --truth-format  ir_measures --eval-format ir_measures -i /tmp/tira-iige6_0c/naive.eval.txt --output correlations.jsonl
