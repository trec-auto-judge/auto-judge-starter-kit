#!/usr/bin/env bash
#
# fetch_pilot_dataset.sh - download TREC AutoJudge data into ./local-data/
#
# Fetches both the pilot/training tracks (dragun25, rag25, ragtime25) and the TREC 2026 AutoJudge
# TEST tracks (rag26, ragtime26). Which release a track lives in is a property of the track, not
# something you pass in, so ask for a dataset by name and the right archive is fetched.
#
# All releases are password-protected (HTTP basic auth). Provide credentials via the environment
# (never commit them):
#
#   export TREC_AUTOJUDGE_USER=...              # the login (e.g. trec2025)
#   export TREC_AUTOJUDGE_PASSWORD=...          # the password
#
# Usage:
#   ./fetch_pilot_dataset.sh                        # fetch every track, pilot and test
#   ./fetch_pilot_dataset.sh --dataset dragun-repgen   # fetch the track for one dataset (repeatable)
#   ./fetch_pilot_dataset.sh --dataset rag26-generation
#   ./fetch_pilot_dataset.sh --keep-archive        # keep the .tar.gz after extracting
#
# Each tarball is self-describing: it extracts to ./local-data/<track>/ containing runs/, topics/,
# and its own datasets.yml (responses/topics/prio1_runs/assessed_topics, relative paths). The
# starterkit's datasets.yml references these by {track, task} and merges in tira_id/bucket, so you
# do not hand-maintain data paths. Corpora come from the host tracks.
#
# The runs are anonymized, and coding agents must respect the anonymization. See the data policy at
# https://github.com/trec-auto-judge/.github/blob/main/profile/howto/data-policy.md
# (each 2026 archive also ships it as AGENTS.md / CLAUDE.md).

set -euo pipefail

BASE_URL="https://trec-auto-judge.cs.unh.edu/datareleases"
DEST="./local-data"
USER_NAME="${TREC_AUTOJUDGE_USER:-}"

# dataset-name (or track) -> tarball track key. rag25-gen and rag25-auggen share the rag25 tarball.
declare -A TRACK_OF=(
  [dragun-repgen]=dragun25 [dragun25]=dragun25
  [rag25-gen]=rag25 [rag25-auggen]=rag25 [rag25]=rag25
  [ragtime25]=ragtime25
  [rag26-generation]=rag26 [rag26]=rag26
  [ragtime26-repgen]=ragtime26 [ragtime26]=ragtime26
)

# Which release each track lives in, and the suffix in its tarball name:
#   $BASE_URL/<release>/anonymized-runs-<track>-<suffix>.tar.gz
# Per track rather than global, so the pilot and the 2026 test data can be fetched by the same
# command and nobody has to know which release a dataset belongs to.
declare -A RELEASE_OF=(
  [dragun25]=v0.2.1 [rag25]=v0.2.1 [ragtime25]=v0.2.1
  [rag26]=v1.0.0    [ragtime26]=v1.0.0
)
declare -A SUFFIX_OF=(
  [dragun25]=v2.1 [rag25]=v2.1 [ragtime25]=v2.1
  [rag26]=v1      [ragtime26]=v1
)

# One dataset name per track, for the worked example printed at the end. A track can serve
# several datasets (rag25 -> rag25-gen and rag25-auggen); any one of them demonstrates the
# command, and naming one that was actually fetched beats a fixed example for a track the
# user may not have asked for.
declare -A EXAMPLE_OF=(
  [dragun25]=dragun-repgen [rag25]=rag25-auggen [ragtime25]=ragtime25
  [rag26]=rag26-generation [ragtime26]=ragtime26-repgen
)

usage() { grep '^#' "$0" | sed 's/^#\s\?//'; exit "${1:-0}"; }

TARGETS=()
KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dataset) shift; [ $# -gt 0 ] || { echo "--dataset needs a value" >&2; exit 1; }; TARGETS+=("$1");;
    --keep-archive) KEEP=1;;
    -h|--help) usage 0;;
    *) echo "Unknown argument: $1" >&2; usage 1;;
  esac
  shift
done

if [ -z "$USER_NAME" ] || [ -z "${TREC_AUTOJUDGE_PASSWORD:-}" ]; then
  echo "Error: set both the data-release credentials (HTTP basic auth; ask the organizers, do not commit):" >&2
  echo "  export TREC_AUTOJUDGE_USER=...        # the login (e.g. trec2025)" >&2
  echo "  export TREC_AUTOJUDGE_PASSWORD=..." >&2
  exit 1
fi

# Resolve requested targets into a unique set of track tarballs.
declare -A WANT=()
if [ ${#TARGETS[@]} -eq 0 ]; then
  for track in "${!RELEASE_OF[@]}"; do WANT[$track]=1; done
else
  for t in "${TARGETS[@]}"; do
    track="${TRACK_OF[$t]:-}"
    if [ -z "$track" ]; then
      echo "Unknown dataset/track: $t (known: ${!TRACK_OF[*]})" >&2
      exit 1
    fi
    WANT[$track]=1
  done
fi

mkdir -p "$DEST"
EXAMPLE=""
for track in "${!WANT[@]}"; do
  tarball="anonymized-runs-${track}-${SUFFIX_OF[$track]}.tar.gz"
  url="$BASE_URL/${RELEASE_OF[$track]}/$tarball"
  out="$DEST/$track"
  echo "==> Fetching $tarball"
  rm -rf "$out"; mkdir -p "$out"    # clean re-fetch (avoid stale files from an older release)
  tmp="$(mktemp)"
  curl -fSL --user "$USER_NAME:$TREC_AUTOJUDGE_PASSWORD" -o "$tmp" "$url"
  echo "==> Extracting into $out"
  tar -xzf "$tmp" -C "$out"
  if [ "$KEEP" -eq 1 ]; then
    cp "$tmp" "$DEST/$tarball"
  fi
  rm -f "$tmp"
  EXAMPLE="${EXAMPLE_OF[$track]:-$track}"
  # The archive's own README describes its contents, licence and -- for the 2026 test data -- the
  # anonymization rules. Show it here: it is the one moment we know the reader is looking, and it
  # beats a directory listing they would have to interpret.
  if [ -f "$out/README.md" ]; then
    echo
    echo "----- $track: README.md -----"
    cat "$out/README.md"
    echo "----- end of $track README (extracted to $out) -----"
  else
    echo "Layout:"
    find "$out" -maxdepth 3 -type d | sed 's/^/  /'
  fi
done

echo
echo "Done -> $DEST/. Each <track>/ ships its own datasets.yml; run_all_datasets.py reads it for"
echo "datasets declared with 'from_release: {track, task}'. Try:"
echo "  python run_all_datasets.py --workflow judges/<judge>/workflow.yml --dataset $EXAMPLE --dry-run"
