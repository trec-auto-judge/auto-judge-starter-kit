"""Checks that the installed framework packages are new enough.

Covers `autojudge-base` and `tira`, in two layers each:
1. against this repo's own pyproject pin (always runs), and
2. against the pin in the upstream template — read from the `starterkit`
   (or `upstream`) git remote that the setup guide has you keep — so a clone
   notices when the template has moved to a newer framework requirement.
   Skipped when no such remote/ref is available (e.g. offline, or inside the
   template itself).
"""

import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest
from packaging.version import Version

REPO = Path(__file__).parent.parent
PACKAGES = ("autojudge-base", "tira")


def _installed(package: str) -> Version:
    try:
        return Version(version(package))
    except PackageNotFoundError:
        pytest.fail(f"{package} is not installed — run: uv pip install -e '.[all]'")


def _pin_from(text: str, package: str) -> Version:
    m = re.search(rf'"{re.escape(package)}\s*>=\s*([0-9][0-9a-zA-Z.]*)"', text)
    assert m, f"no {package}>=X pin found in pyproject.toml"
    return Version(m.group(1))


@pytest.mark.parametrize("package", PACKAGES)
def test_installed_meets_local_pin(package):
    """Installed package satisfies this repo's own minimum pin."""
    pin = _pin_from((REPO / "pyproject.toml").read_text(encoding="utf-8"), package)
    installed = _installed(package)
    assert installed >= pin, (
        f"installed {package} {installed} < pinned {pin} — "
        "run: uv pip install -e '.[all]' --refresh"
    )


def _upstream_pyproject() -> str:
    """pyproject.toml from the upstream template's remote ref, or '' if unavailable."""
    for remote in ("starterkit", "upstream"):
        try:
            subprocess.run(
                ["git", "fetch", "--quiet", remote, "main"],
                cwd=REPO, capture_output=True, timeout=10, check=False,
            )  # best effort: offline is fine if a previously fetched ref exists
            out = subprocess.run(
                ["git", "show", f"{remote}/main:pyproject.toml"],
                cwd=REPO, capture_output=True, text=True, check=True,
            ).stdout
            if out:
                return out
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, OSError):
            continue
    return ""


@pytest.mark.parametrize("package", PACKAGES)
def test_installed_meets_upstream_template_pin(package):
    """Installed package is the same or later than the upstream template requires."""
    upstream = _upstream_pyproject()
    if not upstream:
        pytest.skip(
            "no starterkit/upstream remote ref — add one to enable this check: "
            "git remote add starterkit git@github.com:trec-auto-judge/auto-judge-starter-kit.git"
        )
    pin = _pin_from(upstream, package)
    installed = _installed(package)
    assert installed >= pin, (
        f"installed {package} {installed} < {pin} required by the upstream "
        f"template — the framework moved on; run: uv pip install --upgrade {package} "
        "(and consider pulling template changes: git fetch starterkit && git merge starterkit/main)"
    )
