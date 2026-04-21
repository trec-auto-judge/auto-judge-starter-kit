#!/usr/bin/env python3
"""
Run a judge workflow against multiple datasets.

Usage:
    python run_all_datasets.py --workflow judges/naive/workflow.yml
    python run_all_datasets.py --workflow judges/naive/workflow.yml --datasets my_datasets.yml
    python run_all_datasets.py --workflow judges/naive/workflow.yml --runs prio1
    python run_all_datasets.py --workflow judges/naive/workflow.yml --topics assessed
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


@dataclass
class Dataset:
    name: str
    responses: str              # Path to responses directory
    topics: str                 # Path to topics file
    prio1_runs: List[str] = field(default_factory=list)      # Run IDs for --runs prio1
    assessed_topics: List[str] = field(default_factory=list)  # Topic IDs for --topics assessed
    truth: str | None = None    # Optional: path to truth leaderboard for meta-evaluation


def load_datasets(config_path: Path) -> List[Dataset]:
    """Load datasets from YAML configuration file."""
    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f) or {}

    datasets: List[Dataset] = []
    for entry in config.get("datasets", []):
        datasets.append(Dataset(
            name=entry["name"],
            responses=entry["responses"],
            topics=entry["topics"],
            prio1_runs=entry.get("prio1_runs", []) or [],
            assessed_topics=entry.get("assessed_topics", []) or [],
            truth=entry.get("truth"),
        ))
    return datasets


def run_meta_evaluate(dataset: Dataset, dataset_out: Path) -> None:
    """Invoke auto-judge-evaluate meta-evaluate against the dataset's truth file, if available."""
    if not dataset.truth:
        print(f"Skipping meta-evaluation for {dataset.name}: no 'truth' in datasets.yml")
        return
    if shutil.which("auto-judge-evaluate") is None:
        print("Skipping meta-evaluation: auto-judge-evaluate not installed.")
        print("Install with: uv pip install -e '.[evaluate]'")
        return
    eval_files: List[Path] = sorted(dataset_out.glob("*.eval.txt"))
    if not eval_files:
        print(f"Skipping meta-evaluation for {dataset.name}: no *.eval.txt in {dataset_out}")
        return

    cmd: List[str] = [
        "auto-judge-evaluate", "meta-evaluate",
        "--truth-leaderboard", dataset.truth,
        "--truth-format", "ir_measures", "--truth-header",
        "--eval-format", "ir_measures",
        "--on-missing", "default",
        *[str(p) for p in eval_files],
    ]
    print(f"\n=== Meta-evaluation: {dataset.name} (truth={dataset.truth}) ===")
    subprocess.run(cmd)


def run_workflow(
    workflow: Path,
    dataset: Dataset,
    out_dir: Path,
    runs_filter: str,
    topics_filter: str,
    extra_args: List[str],
    variant: str | None = None,
    meta_evaluate: bool = False,
) -> bool:
    """Run the workflow against a single dataset. Returns True on success."""
    # Include runs/topics (and variant, if set) in output path to separate results
    suffix: str = f"-{variant}" if variant else "-default"
    dataset_out: Path = out_dir / f"{dataset.name}{suffix}-{runs_filter}-{topics_filter}"
    dataset_out.mkdir(parents=True, exist_ok=True)

    cmd: List[str] = [
        "auto-judge", "run",
        "--workflow", str(workflow),
        "--rag-responses", dataset.responses,
        "--rag-topics", dataset.topics,
        "--out-dir", str(dataset_out),
    ]
    if variant:
        cmd.extend(["--variant", variant])

    # Add run filtering
    if runs_filter == "prio1" and dataset.prio1_runs:
        for run_id in dataset.prio1_runs:
            cmd.extend(["--run", str(run_id)])

    # Add topic filtering
    if topics_filter == "assessed" and dataset.assessed_topics:
        for topic_id in dataset.assessed_topics:
            cmd.extend(["--topic", str(topic_id)])

    cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"Running: {dataset.name} (runs={runs_filter}, topics={topics_filter})")
    print(f"  Responses: {dataset.responses}")
    print(f"  Topics: {dataset.topics}")
    if runs_filter == "prio1":
        print(f"  Prio1 runs: {len(dataset.prio1_runs)} run(s)")
    if topics_filter == "assessed":
        print(f"  Assessed topics: {len(dataset.assessed_topics)} topic(s)")
    print(f"  Output: {dataset_out}")
    print(f"{'='*60}\n")

    result: subprocess.CompletedProcess[bytes] = subprocess.run(cmd)
    if result.returncode == 0:
        produced: List[Path] = sorted(p for p in dataset_out.iterdir() if p.is_file())
        print(f"\n=== Output files in {dataset_out} ({len(produced)}) ===")
        if produced:
            for p in produced:
                print(f"  {p.name}")
        else:
            print("  (no files produced)")
        if meta_evaluate:
            run_meta_evaluate(dataset, dataset_out)
    return result.returncode == 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run judge workflow against multiple datasets")
    parser.add_argument("--workflow", "-w", required=True, help="Path to workflow.yml")
    parser.add_argument("--datasets", "-d", default="datasets.yml", help="Path to datasets.yml config (default: datasets.yml)")
    parser.add_argument("--out-dir", "-o", default="./output", help="Base output directory")
    parser.add_argument("--variant", "-v", default=None, help="Workflow variant to run (optional; omit to use the workflow's default)")
    parser.add_argument("--meta-evaluate", action="store_true", help="After each run, invoke auto-judge-evaluate meta-evaluate against the dataset's 'truth' file (if set in datasets.yml)")
    parser.add_argument(
        "--runs", "-r",
        choices=["all", "prio1"],
        default="all",
        help="Which runs to evaluate: all (default) or prio1 (uses prio1_runs from config)"
    )
    parser.add_argument(
        "--topics", "-t",
        choices=["all", "assessed"],
        default="all",
        help="Which topics to evaluate: all (default) or assessed (uses assessed_topics from config)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--keep-going", "-k", action="store_true", help="Continue on errors instead of failing fast")

    # Capture remaining args to pass through to auto-judge
    args: Any
    extra: List[str]
    args, extra = parser.parse_known_args()

    workflow: Path = Path(args.workflow)
    if not workflow.exists():
        print(f"Error: Workflow not found: {workflow}", file=sys.stderr)
        sys.exit(1)

    datasets_path: Path = Path(args.datasets)
    if not datasets_path.exists():
        print(f"Error: Datasets config not found: {datasets_path}", file=sys.stderr)
        print("Create a datasets.yml file or specify with --datasets", file=sys.stderr)
        sys.exit(1)

    all_datasets: List[Dataset] = load_datasets(datasets_path)
    out_dir: Path = Path(args.out_dir)

    # Filter datasets that have the required filter lists
    datasets: List[Dataset] = []
    for d in all_datasets:
        # Skip if prio1 requested but no prio1_runs defined
        if args.runs == "prio1" and not d.prio1_runs:
            print(f"Skipping {d.name}: no prio1_runs defined", file=sys.stderr)
            continue
        # Skip if assessed requested but no assessed_topics defined
        if args.topics == "assessed" and not d.assessed_topics:
            print(f"Skipping {d.name}: no assessed_topics defined", file=sys.stderr)
            continue
        datasets.append(d)

    if not datasets:
        if not all_datasets:
            print(f"No datasets in {datasets_path}. Add entries to the 'datasets' list.", file=sys.stderr)
        else:
            print(f"No datasets have required filter lists for --runs={args.runs} --topics={args.topics}", file=sys.stderr)
        sys.exit(1)

    print(f"Running workflow: {workflow}")
    print(f"Datasets config: {datasets_path}")
    print(f"Filter: runs={args.runs}, topics={args.topics}")
    print(f"Matching datasets: {len(datasets)}")
    for d in datasets:
        info: List[str] = []
        if args.runs == "prio1":
            info.append(f"{len(d.prio1_runs)} runs")
        if args.topics == "assessed":
            info.append(f"{len(d.assessed_topics)} topics")
        info_str: str = f" ({', '.join(info)})" if info else ""
        print(f"  - {d.name}{info_str}")

    if args.dry_run:
        suffix: str = f"-{args.variant}" if args.variant else "-default"
        for dataset in datasets:
            print(f"\nWould run: {dataset.name}")
            cmd_parts: List[str] = [
                f"auto-judge run --workflow {workflow}",
                f"--rag-responses {dataset.responses}",
                f"--rag-topics {dataset.topics}",
                f"--out-dir {out_dir / f'{dataset.name}{suffix}-{args.runs}-{args.topics}'}",
            ]
            if args.variant:
                cmd_parts.append(f"--variant {args.variant}")
            if args.runs == "prio1" and dataset.prio1_runs:
                cmd_parts.append(f"--run {' --run '.join(dataset.prio1_runs)}")
            if args.topics == "assessed" and dataset.assessed_topics:
                cmd_parts.append(f"--topic {' --topic '.join(dataset.assessed_topics)}")
            if extra:
                cmd_parts.append(" ".join(extra))
            print("  " + " \\\n    ".join(cmd_parts))
        return

    # Run each dataset
    results: Dict[str, str] = {}
    key_suffix: str = f"-{args.variant}" if args.variant else "-default"
    for dataset in datasets:
        key: str = f"{dataset.name}{key_suffix}-{args.runs}-{args.topics}"
        success: bool = run_workflow(workflow, dataset, out_dir, args.runs, args.topics, extra, variant=args.variant, meta_evaluate=args.meta_evaluate)
        results[key] = "OK" if success else "FAILED"

        # Fail fast unless --keep-going
        if not success and not args.keep_going:
            print(f"\nFailed on {key}. Use --keep-going to continue on errors.")
            sys.exit(1)

    # Summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    for name, status in results.items():
        print(f"  {name}: {status}")

    failed: int = sum(1 for s in results.values() if s == "FAILED")
    if failed:
        print(f"\n{failed} dataset(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()