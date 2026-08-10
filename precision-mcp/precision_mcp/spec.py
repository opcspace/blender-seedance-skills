"""Pure-Python validation and V1 compatibility for precision specifications.

V1 dimension checks use relative tolerance. V2 evidence uses absolute tolerance
through :func:`precision_mcp.measurements.evaluate_assertion` instead.
"""

from __future__ import annotations

from typing import Any

from precision_mcp.measurements import check_measurement


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
