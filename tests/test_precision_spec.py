import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.spec import check_measurement, validate_spec


class PrecisionSpecTests(unittest.TestCase):
    def test_valid_spec(self):
        self.assertEqual(validate_spec({"category": "architecture", "dimensions": [10, 8, 6], "parts": [{"name": "body"}]}), [])

    def test_invalid_spec_reports_missing_parts_and_dimensions(self):
        errors = validate_spec({"category": "unknown", "dimensions": [0, 2], "parts": []})
        self.assertIn("category", errors[0])
        self.assertTrue(any("dimensions" in error for error in errors))
        self.assertTrue(any("parts" in error for error in errors))

    def test_measurement_tolerance(self):
        self.assertTrue(check_measurement([10.05, 8, 6], [10, 8, 6], 0.01)["passed"])
        self.assertFalse(check_measurement([10.2, 8, 6], [10, 8, 6], 0.01)["passed"])


if __name__ == "__main__":
    unittest.main()
