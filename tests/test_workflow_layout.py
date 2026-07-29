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


def _workflow_files() -> list[pathlib.Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


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
        if ".git" not in path.parts and "node_modules" not in path.parts
    }

    unscanned = expected - scanned
    assert not unscanned, (
        f"requirements files live in {sorted(unscanned)} but Dependabot has no pip "
        f"entry for them (declared: {sorted(scanned)}). Add an entry or remove the file."
    )
