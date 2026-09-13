"""Repo-local declarations for tests/test_env_contract.py (atrium-project#60).

Never vendored, never in para-drift, never in docs/templates/ruff.toml's [format]
exclude — unlike test_env_contract.py itself, this file's SHAPE is per-repo by
design. See the canonical test's module docstring for the full rationale.
"""

from __future__ import annotations

# Read by shipped code but deliberately absent from .env.example, each with a
# reason. All four are batch/tools-layer scripts the api entrypoint
# (service/text_api.py -> text_inference, utils, document_hook) never imports.
NOT_PUBLISHED: dict[str, str] = {
    "DOCUMENT_SOURCE_ORIGIN": "batch-pipeline knob read by page_split.py; not reachable from the service entrypoint",
    "KOREKTOR_URL": "read only by tools/quality_model/correct.py, a batch/tools-layer script; not reachable from the service entrypoint",
    "LANGID_TEXT_DIR": "batch-pipeline knob read by classify_TEXT.py and run_pipeline.py; not reachable from the service entrypoint",
    "MAX_WORKERS": "batch-pipeline knob read by extract_ALTO_2_TXT.py and extract_JSON_2_TXT.py; not reachable from the service entrypoint",
}

# In .env.example but read by no Python in this repo — each with a reason.
CONSUMED_ELSEWHERE: dict[str, str] = {
    "ATRIUM_VERSION": "read only by docker-compose.yml to pick the image tag; no Python here reads it",
    "HF_HOME": "read by huggingface_hub itself, set by the Dockerfile and docker-compose.yml",
}

# service/README.md or .env.example cells whose value is prose rather than a literal
# the code-default resolver can compare against.
PROSE_DEFAULTS: dict[str, str] = {
    "GPT2_MODEL_NAME": "README gives the default in prose ('see below', explained just under the table) rather than repeating the literal",
    "MODEL_DIR": "README gives the default in prose ('see below') rather than repeating the computed path",
}
