"""
tests/test_workflow_layout.py

Layout guards for `.github/`, catching config files that are syntactically fine
but live in the wrong directory.

GitHub Actions parses **every** file under `.github/workflows/` as a workflow
definition. A Dependabot config put there is valid YAML and a valid Dependabot
file, so nothing local complains — but Actions rejects it with:

    Invalid workflow file
    (Line: 1, Col: 1): Unexpected value 'version'
    (Line: 2, Col: 1): Unexpected value 'updates'
    (Line: 1, Col: 1): Required property is missing: jobs

and Dependabot ignores it, because Dependabot only ever reads
`.github/dependabot.yml`. The failure is therefore invisible until a push, and
its silent half (dependency scanning quietly not happening) stays invisible
after that. This module moves both halves of the check to where they fail in a
second.

A note on ``on:`` — PyYAML follows YAML 1.1 and resolves the bare key ``on`` to
the boolean ``True``, so a workflow's trigger block shows up as the key
``True`` rather than ``"on"``. Both spellings are accepted below.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml", reason="pyyaml is required to parse the CI configuration")

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
ROOT_REQUIREMENTS_TEST = REPO_ROOT / "requirements-test.txt"
CANONICAL_REQUIREMENTS_TEST = "setup/requirements-test.txt"


def _workflow_files() -> list[pathlib.Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def _requirement_lines(path: pathlib.Path) -> list[str]:
    """Non-blank, non-comment lines of a requirements file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _is_include_only(path: pathlib.Path) -> bool:
    """True when a requirements file only forwards to others (`-r other.txt`).

    Such a file pins nothing itself, so Dependabot has nothing to scan in its
    directory — it follows the include to the real file instead.
    """
    lines = _requirement_lines(path)
    return bool(lines) and all(line.startswith(("-r", "--requirement")) for line in lines)


def test_workflows_directory_is_not_empty():
    """Guards the guard: a bad glob here would make every check below vacuous."""
    assert _workflow_files(), f"no workflow files found under {WORKFLOWS_DIR}"


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_file_is_a_workflow(path: pathlib.Path):
    """Every file in .github/workflows/ must actually be a workflow.

    This is the check GitHub runs server-side, run locally instead.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{path.name}: not a YAML mapping"

    # `on` parses as the boolean True under YAML 1.1; accept either spelling.
    has_trigger = True in doc or "on" in doc
    assert has_trigger, f"{path.name}: no `on:` trigger block — is this a workflow file?"
    assert "jobs" in doc, (
        f"{path.name}: no `jobs:` key. GitHub Actions parses everything in "
        f".github/workflows/ as a workflow, so a non-workflow config placed here "
        f"fails the whole run. Dependabot config belongs at .github/dependabot.yml."
    )
    assert doc["jobs"], f"{path.name}: `jobs:` is empty"


def test_no_dependabot_config_inside_workflows():
    """A Dependabot config under .github/workflows/ breaks Actions AND is ignored.

    Named separately from the generic check above so the failure message points
    straight at the fix rather than at 'missing jobs key'.
    """
    misfiled = []
    for path in _workflow_files():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "updates" in doc and "jobs" not in doc:
            misfiled.append(path.name)
    assert not misfiled, (
        f"Dependabot config found in .github/workflows/: {misfiled}. "
        f"Move it to .github/dependabot.yml — Actions rejects it where it is, and "
        f"Dependabot never reads that path."
    )


def test_dependabot_config_is_present_and_well_formed():
    """`.github/dependabot.yml` must exist and be a Dependabot config, not a workflow."""
    assert DEPENDABOT_PATH.is_file(), f"missing {DEPENDABOT_PATH.relative_to(REPO_ROOT)}"

    doc = yaml.safe_load(DEPENDABOT_PATH.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), "dependabot.yml: not a YAML mapping"
    assert doc.get("version") == 2, f"dependabot.yml: expected version 2, got {doc.get('version')!r}"
    assert "jobs" not in doc, "dependabot.yml looks like a workflow — wrong file in this path?"

    updates = doc.get("updates")
    assert isinstance(updates, list) and updates, "dependabot.yml: `updates:` must be a non-empty list"
    for entry in updates:
        assert "package-ecosystem" in entry, f"dependabot.yml: entry without package-ecosystem: {entry}"
        assert "directory" in entry, f"dependabot.yml: entry without directory: {entry}"


def test_dependabot_scans_every_requirements_directory():
    """Every directory holding a requirements file must have a pip entry.

    The original config declared a single pip entry at `/`, where the only
    requirements file was a duplicate of setup/requirements-test.txt — so
    setup/ and service/, the ones the Dockerfile and CI actually install, were
    never scanned. A stale dependency set does not announce itself, which is
    why this needs a test rather than a comment.
    """
    doc = yaml.safe_load(DEPENDABOT_PATH.read_text(encoding="utf-8"))
    scanned = {"/" + entry["directory"].strip("/") for entry in doc["updates"] if entry["package-ecosystem"] == "pip"}

    expected = {
        "/" + str(path.parent.relative_to(REPO_ROOT)).strip(".").strip("/")
        for path in REPO_ROOT.glob("**/requirements*.txt")
        if ".git" not in path.parts
        and "node_modules" not in path.parts
        # Include-only files (`-r other.txt`) declare no dependencies of their own.
        and not _is_include_only(path)
    }

    unscanned = expected - scanned
    assert not unscanned, (
        f"requirements files live in {sorted(unscanned)} but Dependabot has no pip "
        f"entry for them (declared: {sorted(scanned)}). Add an entry or remove the file."
    )


def test_root_requirements_test_is_an_include_of_setup():
    """The root requirements-test.txt must exist and forward to setup/.

    Both halves are load-bearing, and both have already gone wrong once:

    * **Deleting it breaks CI.** The hub's api-contract.reusable.yml runs
      ``[ -f requirements-test.txt ] && pip install -r requirements-test.txt``.
      That hardcodes this root path, and the ``[ -f ]`` guard makes a missing
      file install nothing *silently* — the job then dies at ``pytest: command
      not found`` (exit 127), which points nowhere near the cause.
    * **Copying the real list into it creates drift.** Two dependency lists that
      must stay in sync will not.

    An include satisfies the hub's check while keeping one source of truth.
    """
    assert ROOT_REQUIREMENTS_TEST.is_file(), (
        "requirements-test.txt is missing from the repo root. The hub's "
        "api-contract.reusable.yml installs test deps from this exact path and "
        "silently installs nothing when it is absent, so removing it turns the "
        "API Meta-Contract job into 'pytest: command not found'. Restore it as "
        f"an include of {CANONICAL_REQUIREMENTS_TEST}."
    )

    lines = _requirement_lines(ROOT_REQUIREMENTS_TEST)
    assert _is_include_only(ROOT_REQUIREMENTS_TEST), (
        f"requirements-test.txt must only forward to {CANONICAL_REQUIREMENTS_TEST}, "
        f"not declare packages itself (found: {lines}). Two copies of the same "
        f"dependency list drift; edit setup/requirements-test.txt instead."
    )
    assert any(CANONICAL_REQUIREMENTS_TEST in line for line in lines), (
        f"requirements-test.txt forwards to {lines}, expected an include of {CANONICAL_REQUIREMENTS_TEST}."
    )
