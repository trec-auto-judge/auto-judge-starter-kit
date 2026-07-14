#!/usr/bin/env python3
"""
Run a judge workflow against multiple datasets.

Usage:
    python run_all_datasets.py --workflow judges/naive/workflow.yml
    python run_all_datasets.py --workflow judges/naive/workflow.yml --datasets my_datasets.yml
    python run_all_datasets.py --workflow judges/naive/workflow.yml --runs prio1
    python run_all_datasets.py --workflow judges/naive/workflow.yml --topics assessed
"""

import os
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
    corpus: str | None = None   # Optional (recommended): document corpus path or ir-datasets ID
    tira_id: str | None = None  # Optional: TIRA dataset id, for `tira-cli upload` (data submission)
    bucket: str | None = None   # Optional: meta-evaluation service track bucket (dragun/ragtime/rag-generation/rag-auggen)


LOCAL_DATA = Path("./local-data")   # where fetch_pilot_dataset.sh extracts each track


def _resolve_from_release(rel: Dict[str, str], name: str):
    """Pull responses/topics/prio1_runs/assessed_topics from a fetched tarball's own datasets.yml
    (./local-data/<track>/datasets.yml), rooting its relative paths at the extract dir. Returns a
    (responses, topics, prio1_runs, assessed_topics) tuple, or None if the track isn't fetched
    (or the task is absent)."""
    track, task = rel.get("track"), rel.get("task")
    bundled: Path = LOCAL_DATA / str(track) / "datasets.yml"
    if not bundled.exists():
        return None  # not fetched — summarized by the caller
    cfg: Dict[str, Any] = yaml.safe_load(bundled.read_text(encoding="utf-8")) or {}
    base: Path = LOCAL_DATA / str(track)

    def rooted(p: Any) -> str:
        s = str(p)
        if s.startswith("/"):
            return s  # already absolute (a fixed release should not emit these)
        return str(base / (s[2:] if s.startswith("./") else s))

    for ds in cfg.get("datasets", []):
        if ds.get("name") == task:
            return (rooted(ds["responses"]), rooted(ds["topics"]),
                    ds.get("prio1_runs", []) or [], ds.get("assessed_topics", []) or [])
    print(f"Warning: {name}: task '{task}' not found in {bundled}", file=sys.stderr)
    return None


def load_datasets(config_path: Path) -> List[Dataset]:
    """Load datasets from YAML. Entries with `from_release: {track, task}` pull their
    responses/topics/prio1_runs/assessed_topics from the fetched tarball's own datasets.yml,
    so data paths live in the release, not here (only tira_id/bucket/name are maintained here)."""
    with open(config_path, encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f) or {}

    datasets: List[Dataset] = []
    unfetched: List[str] = []
    for entry in config.get("datasets", []):
        rel = entry.get("from_release")
        if rel:
            resolved = _resolve_from_release(rel, entry["name"])
            if resolved is None:
                unfetched.append(entry["name"])
                continue
            responses, topics, prio1_runs, assessed_topics = resolved
        else:
            responses = entry["responses"]
            topics = entry["topics"]
            prio1_runs = entry.get("prio1_runs", []) or []
            assessed_topics = entry.get("assessed_topics", []) or []
        datasets.append(Dataset(
            name=entry["name"],
            responses=responses,
            topics=topics,
            prio1_runs=prio1_runs,
            assessed_topics=assessed_topics,
            truth=entry.get("truth"),
            corpus=entry.get("corpus"),
            tira_id=entry.get("tira_id"),
            bucket=entry.get("bucket"),
        ))
    if unfetched:
        print(f"Note: not fetched yet (run ./fetch_pilot_dataset.sh --dataset <name>): {', '.join(unfetched)}",
              file=sys.stderr)
    return datasets


def run_dir(out_dir: Path, workflow: Path, dataset_name: str, variant: str | None,
            runs_filter: str, topics_filter: str) -> Path:
    """Output directory for one result set, nested <dataset>/<workflow>/<variant> so different
    datasets, judges, and variants never share a directory — each holds a single leaderboard,
    which is what `tira-cli upload` and meta-evaluate expect. Computed in one place so the run,
    dry-run, and summary paths cannot drift apart."""
    leaf = f"{variant or 'default'}-{runs_filter}-{topics_filter}"
    return out_dir / dataset_name / workflow.parent.name / leaf


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


def run_tira_upload(dataset: Dataset, dataset_out: Path, system: str) -> None:
    """Upload the run output to TIRA via `tira-cli upload` (data submission), if the dataset has a tira_id."""
    if not dataset.tira_id:
        print(f"Skipping TIRA upload for {dataset.name}: no 'tira_id' in datasets.yml")
        return
    if shutil.which("tira-cli") is None:
        print("Skipping TIRA upload: tira-cli not installed (uv pip install -e '.[tira]').")
        return
    cmd: List[str] = [
        "tira-cli", "upload",
        "--dataset", dataset.tira_id,
        "--directory", str(dataset_out),
        "--system", system,
    ]
    print(f"\n=== TIRA data upload: {dataset.name} -> {dataset.tira_id} (system={system}) ===")
    subprocess.run(cmd)


def run_metaeval_upload(dataset: Dataset, dataset_out: Path, dest: str | None) -> None:
    """Deposit *.eval.txt into the meta-evaluation service's per-track bucket via rsync."""
    if not dataset.bucket:
        print(f"Skipping meta-eval upload for {dataset.name}: no 'bucket' in datasets.yml")
        return
    if not dest:
        print(f"Skipping meta-eval upload for {dataset.name}: pass --metaeval-dest (e.g. c02:/autojudge-eval/in)")
        return
    if shutil.which("rsync") is None:
        print("Skipping meta-eval upload: rsync not installed.")
        return
    eval_files: List[Path] = sorted(dataset_out.glob("*.eval.txt"))
    if not eval_files:
        print(f"Skipping meta-eval upload for {dataset.name}: no *.eval.txt in {dataset_out}")
        return
    bucket_dest: str = dest.rstrip("/") + "/" + dataset.bucket + "/"
    cmd: List[str] = ["rsync", "-Laur", *[str(p) for p in eval_files], bucket_dest]
    print(f"\n=== Meta-eval service deposit: {dataset.name} -> {bucket_dest} ===")
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
    upload_tira: bool = False,
    upload_metaeval: bool = False,
    metaeval_dest: str | None = None,
) -> bool:
    """Run the workflow against a single dataset. Returns True on success."""
    # Separate results by dataset/workflow/variant so different judges never share a dir
    dataset_out: Path = run_dir(out_dir, workflow, dataset.name, variant, runs_filter, topics_filter)
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

    # Add corpus (optional; only doc-consulting judges need it)
    if dataset.corpus:
        cmd.extend(["--corpus", dataset.corpus])

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
        system: str = f"{workflow.parent.name}-{variant or 'default'}"
        if meta_evaluate:
            run_meta_evaluate(dataset, dataset_out)
        if upload_tira:
            run_tira_upload(dataset, dataset_out, system)
        if upload_metaeval:
            run_metaeval_upload(dataset, dataset_out, metaeval_dest)
    return result.returncode == 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run judge workflow against multiple datasets")
    parser.add_argument("--workflow", "-w", required=True, help="Path to workflow.yml")
    parser.add_argument("--datasets", "-d", default="datasets.yml", help="Path to datasets.yml config (default: datasets.yml)")
    parser.add_argument("--out-dir", "-o", default="./output", help="Base output directory")
    parser.add_argument("--variant", "-v", default=None, help="Workflow variant to run (optional; omit to use the workflow's default)")
    parser.add_argument("--meta-evaluate", action="store_true", help="After each run, invoke auto-judge-evaluate meta-evaluate against the dataset's 'truth' file (if set in datasets.yml)")
    parser.add_argument("--upload-tira", action="store_true", help="After each run, upload the output to TIRA via `tira-cli upload` (needs the dataset's 'tira_id')")
    parser.add_argument("--upload-metaeval", action="store_true", help="After each run, deposit *.eval.txt into the meta-evaluation service's per-track bucket via rsync (needs the dataset's 'bucket' and --metaeval-dest)")
    parser.add_argument("--metaeval-dest", default=None, metavar="DEST", help="rsync destination base for --upload-metaeval (e.g. c02:/autojudge-eval/in); the dataset's bucket is appended")
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
    parser.add_argument("--dataset", "-D", action="append", default=[], metavar="NAME",
                        help="Restrict to dataset(s) by name (repeatable). Default: all datasets in the config.")
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

    # Restrict to user-specified dataset names (if any)
    if args.dataset:
        known_names: set[str] = {d.name for d in all_datasets}
        unknown: List[str] = [n for n in args.dataset if n not in known_names]
        if unknown:
            print(f"Error: unknown dataset name(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(known_names))}", file=sys.stderr)
            sys.exit(1)
        requested: set[str] = set(args.dataset)
        all_datasets = [d for d in all_datasets if d.name in requested]

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

    # Show the injected LLM configuration up front (auto-judge run reads these from the environment)
    base_url: str = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or "(unset)"
    model: str = os.environ.get("OPENAI_MODEL") or "(unset)"
    cache_dir: str = os.environ.get("CACHE_DIR") or os.environ.get("LLM_CACHE_DIR") or "(unset)"
    print("LLM configuration (from environment):")
    print(f"  OPENAI_BASE_URL: {base_url}")
    print(f"  OPENAI_MODEL:    {model}")
    print(f"  OPENAI_API_KEY:  {'set' if os.environ.get('OPENAI_API_KEY') else '(unset)'}")
    print(f"  CACHE_DIR:       {cache_dir}")

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
        for dataset in datasets:
            print(f"\nWould run: {dataset.name}")
            cmd_parts: List[str] = [
                f"auto-judge run --workflow {workflow}",
                f"--rag-responses {dataset.responses}",
                f"--rag-topics {dataset.topics}",
                f"--out-dir {run_dir(out_dir, workflow, dataset.name, args.variant, args.runs, args.topics)}",
            ]
            if args.variant:
                cmd_parts.append(f"--variant {args.variant}")
            if dataset.corpus:
                cmd_parts.append(f"--corpus {dataset.corpus}")
            if args.runs == "prio1" and dataset.prio1_runs:
                cmd_parts.append(f"--run {' --run '.join(dataset.prio1_runs)}")
            if args.topics == "assessed" and dataset.assessed_topics:
                cmd_parts.append(f"--topic {' --topic '.join(dataset.assessed_topics)}")
            if extra:
                cmd_parts.append(" ".join(extra))
            print("  " + " \\\n    ".join(cmd_parts))
            system_name: str = f"{workflow.parent.name}-{args.variant or 'default'}"
            ddir: Path = run_dir(out_dir, workflow, dataset.name, args.variant, args.runs, args.topics)
            if args.upload_tira:
                if dataset.tira_id:
                    print(f"  # then: tira-cli upload --dataset {dataset.tira_id} --directory {ddir} --system {system_name}")
                else:
                    print(f"  # (skip TIRA upload: no tira_id for {dataset.name})")
            if args.upload_metaeval:
                if dataset.bucket and args.metaeval_dest:
                    print(f"  # then: rsync -Laur {ddir}/*.eval.txt {args.metaeval_dest.rstrip('/')}/{dataset.bucket}/")
                else:
                    print(f"  # (skip meta-eval upload: needs bucket + --metaeval-dest for {dataset.name})")
        return

    # Run each dataset
    results: Dict[str, str] = {}
    for dataset in datasets:
        key: str = str(run_dir(out_dir, workflow, dataset.name, args.variant, args.runs, args.topics).relative_to(out_dir))
        success: bool = run_workflow(workflow, dataset, out_dir, args.runs, args.topics, extra, variant=args.variant, meta_evaluate=args.meta_evaluate, upload_tira=args.upload_tira, upload_metaeval=args.upload_metaeval, metaeval_dest=args.metaeval_dest)
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