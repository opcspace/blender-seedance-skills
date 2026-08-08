"""Pure-Python validation for commercial precision model specifications."""

from __future__ import annotations

from typing import Any


CATEGORIES = {
    "character",
    "creature",
    "props",
    "architecture",
    "hard_surface",
    "environment",
    "abstract",
}


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if spec.get("category") not in CATEGORIES:
        errors.append("category must be one of character, creature, props, architecture, hard_surface, environment, abstract")
    dimensions = spec.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 3 or any(not isinstance(v, (int, float)) or v <= 0 for v in dimensions):
        errors.append("dimensions must contain three positive numbers")
    tolerance = spec.get("tolerance", 0.01)
    if not isinstance(tolerance, (int, float)) or not 0 < tolerance < 1:
        errors.append("tolerance must be between 0 and 1")
    parts = spec.get("parts", [])
    if not isinstance(parts, list) or not parts:
        errors.append("parts must contain at least one named part")
    else:
        for index, part in enumerate(parts):
            if not isinstance(part, dict) or not part.get("name"):
                errors.append(f"parts[{index}] must have a name")
            if isinstance(part, dict) and part.get("dimensions") is not None:
                dims = part["dimensions"]
                if not isinstance(dims, list) or len(dims) != 3 or any(not isinstance(v, (int, float)) or v <= 0 for v in dims):
                    errors.append(f"parts[{index}].dimensions must contain three positive numbers")
    return errors


def check_measurement(actual: list[float], expected: list[float], tolerance: float) -> dict[str, Any]:
    if len(actual) != 3 or len(expected) != 3:
        raise ValueError("actual and expected must each contain three dimensions")
    if not 0 < tolerance < 1:
        raise ValueError("tolerance must be between 0 and 1")
    errors = []
    relative_errors = []
    for axis, (got, want) in enumerate(zip(actual, expected)):
        if want <= 0:
            raise ValueError("expected dimensions must be positive")
        relative = abs(got - want) / want
        relative_errors.append(relative)
        if relative > tolerance:
            errors.append({"axis": axis, "actual": got, "expected": want, "relative_error": relative})
    return {"passed": not errors, "relative_errors": relative_errors, "errors": errors}
