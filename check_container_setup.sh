#!/usr/bin/env bash
#
# Container-runtime preflight for TIRA code submissions.
#
# tira-cli code-submission builds and test-runs a Docker image on your
# machine, so Docker or podman must be able to build and run containers.
# This script diagnoses the common failure modes and prints the exact fix
# for each. By default it is read-only and never changes your system; with
# --fix it applies the one safe repair it can do itself (podman system
# migrate, only when the ID-mapping check fails).
#
# Usage:  ./check_container_setup.sh [--fix]
#
# Setup at a glance -- the checks below tell you which of these you need:
#
# Docker:
#   $ sudo systemctl enable --now docker          # start the daemon
#   $ sudo usermod -aG docker $USER               # socket access (log out and back in)
#
# Podman (rootless / "headless"):
#   $ systemctl --user enable --now podman.socket                                  # docker-compatible API endpoint
#   $ export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock                # only if `docker` is not podman
#   $ sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER   # subordinate IDs for image unpacking
#   $ podman system migrate                                                        # apply new ID ranges / discard a stale session mapping
#   $ mkdir -p ~/.config/containers                                                # signature policy location
#   $ printf '{\n  "default": [{"type": "insecureAcceptAnything"}]\n}\n' > ~/.config/containers/policy.json
#
# After every check passes, run the authoritative end-to-end check (the
# --task/--team scoping is required for a fully valid result; without it the
# upload check reports the installation as not valid):
#   tira-cli verify-installation --task trec-auto-judge --team <your-team>

set -u

FIX=0
for arg in "$@"; do
    case "$arg" in
        --fix) FIX=1 ;;
        *) echo "Usage: $0 [--fix]" >&2; exit 2 ;;
    esac
done

FAILURES=0

ok()   { printf 'OK    %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; printf '      fix: %s\n' "$2"; FAILURES=$((FAILURES + 1)); }

# --- 1. Which engine is installed? -----------------------------------------

ENGINE=""
if command -v docker >/dev/null 2>&1; then
    # podman often ships a `docker` compatibility shim; the version banner
    # names the real engine.
    if docker version 2>/dev/null | grep -qi "podman"; then
        ENGINE="podman"
        ok "container engine: podman (behind a docker compatibility shim)"
    else
        ENGINE="docker"
        ok "container engine: Docker"
    fi
elif command -v podman >/dev/null 2>&1; then
    ENGINE="podman"
    ok "container engine: podman (no docker shim; tira-cli needs DOCKER_HOST, see socket check)"
else
    fail "no container engine found (neither docker nor podman on PATH)" \
         "install Docker (https://docs.docker.com/engine/install/) or podman (https://podman.io/docs/installation)"
    echo
    echo "1 check failed. Fix it and re-run this script."
    exit 1
fi

# --- 2. Engine-specific checks ---------------------------------------------

if [ "$ENGINE" = "docker" ]; then

    # Daemon running?
    if docker info >/dev/null 2>&1; then
        ok "docker daemon reachable (docker info)"
    elif systemctl is-active --quiet docker 2>/dev/null; then
        # Daemon runs but we cannot talk to it: almost always a permission issue.
        fail "docker daemon is running but not reachable (permission denied on the socket?)" \
             "add yourself to the docker group: sudo usermod -aG docker \$USER   (then log out and back in)"
    else
        fail "docker daemon is not running" \
             "sudo systemctl enable --now docker"
    fi

else  # podman

    # Rootless podman needs subordinate UID/GID ranges to unpack images.
    SUBID_OK=1
    if command -v getsubids >/dev/null 2>&1; then
        getsubids "$(id -un)" >/dev/null 2>&1 || SUBID_OK=0
        getsubids -g "$(id -un)" >/dev/null 2>&1 || SUBID_OK=0
    else
        for f in /etc/subuid /etc/subgid; do
            if ! grep -q "^$(id -un):" "$f" 2>/dev/null && ! grep -q "^$(id -u):" "$f" 2>/dev/null; then
                SUBID_OK=0
            fi
        done
    fi
    if [ "$SUBID_OK" = 1 ]; then
        ok "subordinate UID/GID ranges configured (/etc/subuid, /etc/subgid)"
    else
        fail "no subordinate UID/GID range for $(id -un) -- image unpacking will fail with 'potentially insufficient UIDs or GIDs available in user namespace'" \
             "sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 \$USER   (then: podman system migrate)"
    fi

    # The ranges must also be USABLE: activating them needs the setuid
    # newuidmap/newgidmap helpers, which e.g. nix dev shells can shadow with
    # non-setuid copies. A working mapping has 2+ lines; a collapsed one has 1
    # and image unpacking fails with 'lchown ...: invalid argument'.
    MAP_LINES="$(podman unshare cat /proc/self/uid_map 2>/dev/null | wc -l)"
    if [ "$MAP_LINES" -lt 2 ] && [ "$FIX" = 1 ]; then
        echo "fix   mapping is collapsed; running: podman system migrate"
        podman system migrate
        MAP_LINES="$(podman unshare cat /proc/self/uid_map 2>/dev/null | wc -l)"
    fi
    if [ "$MAP_LINES" -ge 2 ]; then
        ok "user namespace mapping works (podman unshare)"
    else
        fail "subordinate ID mapping is not usable here (this shell's uid_map: $(tr -s ' \n' ' ;' < /proc/self/uid_map 2>/dev/null)). Pulling/unpacking NEW images will fail ('lchown ...: invalid argument'); builds from already-unpacked images may still succeed" \
             "run 'podman system migrate' (or re-run this script with --fix) -- rootless podman keeps its namespace alive in a per-session pause process, and migrate discards a stale one. If it still fails: newuidmap/newgidmap may be non-setuid in this environment, or this shell may itself run inside a user namespace -- find an environment where this check passes and run container builds there"
    fi

    # Signature policy (podman-only; Docker never needs it).
    if [ -f "$HOME/.config/containers/policy.json" ] || [ -f /etc/containers/policy.json ]; then
        ok "signature policy present (policy.json)"
    else
        fail "no containers policy.json -- builds fail at the first FROM step with 'no policy.json file found'" \
             "mkdir -p ~/.config/containers && printf '{\\n  \"default\": [{\"type\": \"insecureAcceptAnything\"}]\\n}\\n' > ~/.config/containers/policy.json"
    fi

    # tira-cli talks to the docker-compatible API socket.
    SOCKET="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
    if [ -S "$SOCKET" ]; then
        ok "podman user socket active ($SOCKET)"
    else
        fail "podman user socket not running -- tira-cli cannot reach the container API" \
             "systemctl --user enable --now podman.socket"
    fi
    if [ -z "${DOCKER_HOST:-}" ] && ! docker version >/dev/null 2>&1; then
        fail "no docker shim and DOCKER_HOST is unset -- tira-cli will look for a Docker socket that does not exist" \
             "export DOCKER_HOST=unix://$SOCKET"
    fi

    # Proof the endpoint answers.
    if podman info >/dev/null 2>&1; then
        ok "podman endpoint answers (podman info)"
    else
        fail "podman info failed -- see the messages above" \
             "resolve the failed checks above, then re-run this script"
    fi

fi

# --- 3. Verdict -------------------------------------------------------------

echo
if [ "$FAILURES" = 0 ]; then
    echo "All checks passed. Now run the end-to-end check (after tira-cli login):"
    echo "  tira-cli verify-installation --task trec-auto-judge --team <your-team>"
else
    echo "$FAILURES check(s) failed. Apply the printed fixes and re-run this script."
    exit 1
fi
