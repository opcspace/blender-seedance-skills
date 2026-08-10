"""Measurement helpers for both precision API generations.

V1 ``check_measurement`` compares three dimensions with relative tolerance.
V2 ``evaluate_assertion`` evaluates declared evidence with absolute tolerance;
grading must use the V2 result rather than the legacy relative calculation.
"""

from __future__ import annotations

from typing import Any


def check_measurement(actual: list[float], expected: list[float], tolerance: float) -> dict[str, Any]:
    """Return the V1 three-axis relative-tolerance result shape."""
    if len(actual) != 3 or len(expected) != 3:
        raise ValueError("actual and expected must each contain three dimensions")
    if not 0 < tolerance < 1:
        raise ValueError("tolerance must be between 0 and 1")

    errors: list[dict[str, Any]] = []
    relative_errors: list[float] = []
    for axis, (got, want) in enumerate(zip(actual, expected)):
        if want <= 0:
            raise ValueError("expected dimensions must be positive")
        relative_error = abs(got - want) / want
        relative_errors.append(relative_error)
        if relative_error > tolerance:
            errors.append(
                {
                    "axis": axis,
                    "actual": got,
                    "expected": want,
                    "relative_error": relative_error,
                }
            )
    return {"passed": not errors, "relative_errors": relative_errors, "errors": errors}


def evaluate_assertion(assertion: dict[str, Any], actual: float) -> dict[str, Any]:
    """Evaluate one V2 assertion using its absolute tolerance."""
    target = float(assertion["target"])
    tolerance = float(assertion["tolerance_abs"])
    if tolerance < 0:
        raise ValueError("tolerance_abs must be non-negative")

    actual_value = float(actual)
    absolute_error = abs(actual_value - target)
    relative_error = absolute_error / abs(target) if target else None
    return {
        **assertion,
        "actual": actual_value,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "passed": absolute_error <= tolerance,
    }


def derive_grade(
    reference_calibrated: bool,
    assertions: list[dict[str, Any]],
    geometry_ok: bool,
    checkpoint_ok: bool,
    provenance_ok: bool,
) -> dict[str, Any]:
    """Derive an L0/L1/L2 grade and explicit downgrade reasons."""
    if not reference_calibrated:
        return {"grade": "L0", "reasons": ["reference is not calibrated"]}

    reasons: list[str] = []
    failed_required = [
        assertion
        for assertion in assertions
        if assertion.get("required") and not assertion.get("passed")
    ]
    reasons.extend(
        f"failed required measurement: {assertion['id']}"
        for assertion in failed_required
    )

    primary = [
        assertion
        for assertion in assertions
        if assertion.get("scope") in {"global", "primary", "anchor"}
    ]
    l1_ok = bool(primary) and all(assertion.get("passed") for assertion in primary)
    l2_ok = (
        not failed_required
        and bool(assertions)
        and geometry_ok
        and checkpoint_ok
        and provenance_ok
    )
    if l2_ok:
        return {"grade": "L2", "reasons": []}

    if not geometry_ok:
        reasons.append("geometry QA failed")
    if not checkpoint_ok:
        reasons.append("final checkpoint missing")
    if not provenance_ok:
        reasons.append("asset provenance incomplete")
    return {"grade": "L1" if l1_ok else "L0", "reasons": reasons}
