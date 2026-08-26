#!/usr/bin/env python3
"""fetch_datasets.py - download TREC AutoJudge data into ./local-data/

Fetches both the pilot/training tracks (dragun25, rag25, ragtime25) and the TREC 2026 AutoJudge
TEST tracks (rag26, ragtime26). Which release a track lives in is recorded on its datasets.yml
entries (release/category/tarball), not passed in — ask for a dataset by name and the right
archive is fetched.

All releases are password-protected (HTTP basic auth). Provide credentials via the environment
(never commit them):

  export TREC_AUTOJUDGE_USER=...              # the login (e.g. trec2026)
  export TREC_AUTOJUDGE_PASSWORD=...          # the password

Usage:
  ./fetch_datasets.py                             # fetch every track, pilot and test
  ./fetch_datasets.py --pilot                     # only the pilot/training tracks
  ./fetch_datasets.py --test-2026                 # only the TREC 2026 test tracks
  ./fetch_datasets.py --dataset rag26-generation  # the track for one dataset (repeatable)
  ./fetch_datasets.py --keep-archive              # keep the .tar.gz after extracting

Each tarball is self-describing: it extracts to ./local-data/<track>/ containing runs/, topics/,
and its own datasets.yml (responses/topics/prio1_runs/assessed_topics, relative paths). The
starterkit's datasets.yml references these by {track, task} and merges in tira_id/bucket, so you
do not hand-maintain data paths. Corpora come from the host tracks.

The runs are anonymized, and coding agents must respect the anonymization. See the data policy at
https://github.com/trec-auto-judge/.github/blob/main/profile/howto/data-policy.md
(each 2026 archive also ships it as AGENTS.md / CLAUDE.md).
"""

import argparse
import base64
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml

BASE_URL = "https://trec-auto-judge.cs.unh.edu/datareleases"
DEST = Path("./local-data")
DATASETS_YML = Path(__file__).parent / "datasets.yml"


def load_config():
    """Return (tracks, dataset_to_track) from datasets.yml.

    Each from_release entry carries its archive coordinates (release, category, tarball);
    datasets sharing a track (rag25-gen/rag25-auggen) repeat them, so group per track and
    verify the copies agree.

    tracks: track -> {release, category, tarball}
    dataset_to_track: dataset name (and track name itself) -> track
    """
    with open(DATASETS_YML, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    tracks = {}
    dataset_to_track = {}
    for entry in config["datasets"]:
        from_release = entry.get("from_release")
        if not from_release:
            continue
        track = from_release["track"]
        meta = {key: entry[key] for key in ("release", "category", "tarball")}
        if tracks.setdefault(track, meta) != meta:
            raise SystemExit(f"datasets.yml: conflicting release/category/tarball for track {track}")
        dataset_to_track[entry["name"]] = track
        dataset_to_track[track] = track
    return tracks, dataset_to_track


def fetch(url: str, dest: Path, auth_header: str) -> None:
    request = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(request) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download TREC AutoJudge data releases into ./local-data/.",
        epilog="Run with no selection to fetch every track. See the module docstring for details.",
    )
    parser.add_argument(
        "--dataset", action="append", default=[], metavar="NAME",
        help="dataset or track name to fetch (repeatable); default: all tracks",
    )
    parser.add_argument(
        "--pilot", action="store_true",
        help="fetch the pilot/training tracks (dragun25, rag25, ragtime25)",
    )
    parser.add_argument(
        "--test-2026", dest="test_2026", action="store_true",
        help="fetch the TREC 2026 AutoJudge test tracks (rag26, ragtime26)",
    )
    parser.add_argument(
        "--keep-archive", action="store_true",
        help="keep the downloaded .tar.gz after extracting",
    )
    args = parser.parse_args()

    user = os.environ.get("TREC_AUTOJUDGE_USER", "")
    password = os.environ.get("TREC_AUTOJUDGE_PASSWORD", "")
    if not user or not password:
        print("Error: set both the data-release credentials (HTTP basic auth; ask the organizers, do not commit):", file=sys.stderr)
        print("  export TREC_AUTOJUDGE_USER=...        # the login (e.g. trec2026)", file=sys.stderr)
        print("  export TREC_AUTOJUDGE_PASSWORD=...", file=sys.stderr)
        return 1
    auth_header = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    tracks, dataset_to_track = load_config()

    # Resolve the selection into a unique set of track tarballs. --pilot/--test-2026 select by
    # category, --dataset by name; the selections combine as a union.
    wanted = set()
    for category_flag, category in ((args.pilot, "pilot"), (args.test_2026, "test-2026")):
        if category_flag:
            wanted.update(t for t, meta in tracks.items() if meta["category"] == category)
    for name in args.dataset:
        track = dataset_to_track.get(name)
        if track is None:
            print(f"Unknown dataset/track: {name} (known: {' '.join(sorted(dataset_to_track))})", file=sys.stderr)
            return 1
        wanted.add(track)
    if not wanted and not args.dataset and not args.pilot and not args.test_2026:
        wanted = set(tracks)

    DEST.mkdir(parents=True, exist_ok=True)
    example = ""
    for track in sorted(wanted):
        meta = tracks[track]
        tarball = meta["tarball"]
        url = f"{BASE_URL}/{meta['release']}/{tarball}"
        out = DEST / track
        print(f"==> Fetching {tarball}")
        if out.exists():
            shutil.rmtree(out)  # clean re-fetch (avoid stale files from an older release)
        out.mkdir(parents=True)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            try:
                fetch(url, tmp_path, auth_header)
            except urllib.error.HTTPError as e:
                hint = " (check TREC_AUTOJUDGE_USER/PASSWORD)" if e.code in (401, 403) else ""
                print(f"Error: HTTP {e.code} fetching {url}{hint}", file=sys.stderr)
                return 1
            print(f"==> Extracting into {out}")
            with tarfile.open(tmp_path, "r:gz") as tar:
                try:
                    tar.extractall(out, filter="data")
                except TypeError:  # Python < 3.12 has no extraction filters
                    tar.extractall(out)
            if args.keep_archive:
                shutil.copy(tmp_path, DEST / tarball)
        finally:
            tmp_path.unlink(missing_ok=True)
        example = next((name for name, t in dataset_to_track.items() if t == track and name != track), track)
        # The archive's own README describes its contents, licence and -- for the 2026 test data --
        # the anonymization rules. Show it here: it is the one moment we know the reader is looking,
        # and it beats a directory listing they would have to interpret.
        readme = out / "README.md"
        if readme.is_file():
            print()
            print(f"----- {track}: README.md -----")
            print(readme.read_text(encoding="utf-8"))
            print(f"----- end of {track} README (extracted to {out}) -----")
        else:
            print("Layout:")
            for subdir in sorted(p for p in out.rglob("*") if p.is_dir() and len(p.relative_to(out).parts) <= 2):
                print(f"  {subdir}")

    print()
    print(f"Done -> {DEST}/. Each <track>/ ships its own datasets.yml; run_all_datasets.py reads it for")
    print("datasets declared with 'from_release: {track, task}'. Try:")
    print(f"  python run_all_datasets.py --workflow judges/<judge>/workflow.yml --dataset {example} --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
