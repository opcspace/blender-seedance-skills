import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.measurements import derive_grade, evaluate_assertion


def passing(scope="global", *, assertion_id=None, kind=None):
    assertion = {
        "id": assertion_id or scope,
        "scope": scope,
        "target": 10.0,
        "actual": 10.0,
        "absolute_error": 0.0,
        "tolerance_abs": 0.1,
        "required": True,
        "passed": True,
    }
    if kind is not None:
        assertion["kind"] = kind
    return assertion


def full_l1_evidence():
    return [
        passing("global"),
        passing("primary"),
        passing("contact"),
        passing("anchor"),
    ]


class PrecisionMeasurementTests(unittest.TestCase):
    def test_absolute_tolerance_passes_at_both_boundaries(self):
        upper_result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 1000.5)
        self.assertTrue(upper_result["passed"])
        self.assertEqual(upper_result["absolute_error"], 0.5)

        lower_result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 999.5)
        self.assertTrue(lower_result["passed"])
        self.assertEqual(lower_result["absolute_error"], 0.5)

    def test_absolute_tolerance_rejects_large_error(self):
        result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 1000.51)
        self.assertFalse(result["passed"])

    def test_absolute_tolerance_rejects_large_negative_error(self):
        result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 999.49)
        self.assertFalse(result["passed"])

    def test_absolute_tolerance_rejects_negative_tolerance(self):
        with self.assertRaisesRegex(ValueError, "tolerance_abs must be non-negative"):
            evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": -0.5, "required": True}, 1000.0)

    def test_zero_target_has_no_relative_error_and_preserves_assertion_fields(self):
        result = evaluate_assertion(
            {"id": "origin", "scope": "anchor", "target": 0.0, "tolerance_abs": 0.1, "required": False},
            0.05,
        )
        self.assertIsNone(result["relative_error"])
        self.assertEqual(result["scope"], "anchor")
        self.assertFalse(result["required"])


class PrecisionGradeTests(unittest.TestCase):
    def test_uncalibrated_reference_is_l0_with_reason(self):
        result = derive_grade(False, [passing()], True, True, True)
        self.assertEqual(result["grade"], "L0")
        self.assertIn("reference is not calibrated", result["reasons"])

    def test_primary_measurements_can_issue_l1(self):
        result = derive_grade(True, full_l1_evidence(), False, True, True)
        self.assertEqual(result["grade"], "L1")

    def test_all_required_gates_issue_l2(self):
        result = derive_grade(
            True,
            [*full_l1_evidence(), passing("fit")],
            True,
            True,
            True,
            assumptions_ok=True,
        )
        self.assertEqual(result["grade"], "L2")

    def test_failed_required_measurement_prevents_l2(self):
        failed = {**passing("fit"), "passed": False, "absolute_error": 0.2}
        result = derive_grade(
            True,
            [*full_l1_evidence(), failed],
            True,
            True,
            True,
            assumptions_ok=True,
        )
        self.assertNotEqual(result["grade"], "L2")
        self.assertIn("failed required measurement: fit", result["reasons"])

    def test_fit_only_evidence_cannot_issue_l2(self):
        result = derive_grade(
            True,
            [passing("fit")],
            True,
            True,
            True,
            assumptions_ok=True,
        )
        self.assertEqual(result["grade"], "L0")

    def test_missing_any_l1_gate_cannot_issue_l1(self):
        evidence = full_l1_evidence()
        for missing_scope in ("global", "primary", "contact", "anchor"):
            with self.subTest(missing_scope=missing_scope):
                result = derive_grade(
                    True,
                    [item for item in evidence if item["scope"] != missing_scope],
                    True,
                    True,
                    True,
                    assumptions_ok=True,
                )
                self.assertEqual(result["grade"], "L0")

    def test_all_assertions_contributing_to_l1_gate_must_pass(self):
        failed_global = {
            **passing("fit", assertion_id="envelope", kind="global_envelope"),
            "passed": False,
        }
        result = derive_grade(
            True,
            [*full_l1_evidence(), failed_global],
            False,
            True,
            True,
        )
        self.assertEqual(result["grade"], "L0")

    def test_kind_can_supply_global_envelope_and_contact_gates(self):
        evidence = [
            passing("fit", assertion_id="envelope", kind="global_envelope"),
            passing("primary"),
            passing("fit", assertion_id="ground", kind="contact"),
            passing("anchor"),
        ]
        self.assertEqual(
            derive_grade(True, evidence, False, True, True)["grade"],
            "L1",
        )

    def test_unresolved_assumptions_prevent_l2_with_reason(self):
        result = derive_grade(
            True,
            full_l1_evidence(),
            True,
            True,
            True,
            assumptions_ok=False,
        )
        self.assertEqual(result["grade"], "L1")
        self.assertIn("unresolved assumptions remain", result["reasons"])


if __name__ == "__main__":
    unittest.main()
