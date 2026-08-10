"""JSON contract validation for precision workflow documents."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_NAMES = (
    "scene_spec",
    "asset_manifest",
    "operation_plan",
    "qa_report",
)

_SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
_MISSING_PROPERTY = re.compile(r"^'([^']+)' is a required property$")


class ContractError(ValueError):
    """Raised when a precision document violates its named contract."""


@lru_cache(maxsize=len(SCHEMA_NAMES))
def _validator(name: str) -> Draft202012Validator:
    if name not in SCHEMA_NAMES:
        raise ContractError(f"unknown contract: {name}")

    with (_SCHEMA_DIR / f"{name}.schema.json").open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _error_path(error: Any) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "required":
        match = _MISSING_PROPERTY.match(error.message)
        if match:
            parts.append(match.group(1))
    return "/".join(parts) if parts else "$"


def validate_document(
    name: str,
    document: dict[str, Any],
    expected_job_id: str | None = None,
) -> dict[str, Any]:
    """Validate and return *document*, optionally enforcing job identity parity."""
    if name not in SCHEMA_NAMES:
        raise ContractError(f"unknown contract: {name}")

    if expected_job_id is not None and document.get("job_id") != expected_job_id:
        raise ContractError(
            f"job_id mismatch: expected {expected_job_id!r}, "
            f"got {document.get('job_id')!r}"
        )

    errors = sorted(
        _validator(name).iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ContractError(f"{name} {_error_path(error)}: {error.message}")

    return document
