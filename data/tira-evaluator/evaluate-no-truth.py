#!/usr/bin/env python3
from subprocess import check_output
import click
from glob import glob
from pathlib import Path
from tira.io_utils import to_prototext, parse_prototext_key_values

from evaluator import extract_llm


def find_leaderboard(input_dir):
    matches = glob(f"{input_dir}/*.txt")
    if len(matches) == 1:
        return matches[0]
    matches = glob(f"{input_dir}/*eval.txt")
    if len(matches) == 1:
        return matches[0]


def expand_prototext_with_llm(output_prototext, input_directory):
    ret = {}
    for measure in parse_prototext_key_values(output_prototext):
        ret[measure["key"]] = measure["value"]

    llm = extract_llm(input_directory)
    if llm:
        ret["Model"] = llm

    Path(output_prototext).write_text(to_prototext([ret]))


@click.command()
@click.argument("input_directory", required=True)
@click.argument("output_directory", required=True)
def main(input_directory, output_directory):
    leaderboard_to_eval = find_leaderboard(input_directory)
    if leaderboard_to_eval is None:
        print(f"No leaderboard found in {input_directory}")
        return

    output_prototext = f"{output_directory}/evaluation.prototext"
    cmd = f"trec-auto-judge evaluate --input {leaderboard_to_eval} --aggregate --output {output_prototext}"

    print(cmd)
    check_output(["bash", "-c", cmd])

    expand_prototext_with_llm(output_prototext, input_directory)


if __name__ == '__main__':
    main()
