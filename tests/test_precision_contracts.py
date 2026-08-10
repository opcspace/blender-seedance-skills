import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.contracts import ContractError, validate_document
from precision_mcp.measurements import evaluate_assertion


JOB_ID = "chair-fit-01"

SCENE_SPEC = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "category": "furniture",
    "requested_grade": "L2",
    "units": "mm",
    "coordinate_system": {"up": "Z", "handedness": "right"},
    "reference_calibrated": True,
    "measurements": [
        {
            "id": "seat-width",
            "kind": "dimension",
            "asset_id": "chair",
            "axis": "X",
            "target": 480.0,
            "tolerance_abs": 1.0,
            "required": True,
            "scope": "seat",
        }
    ],
}

ASSET_MANIFEST = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "assets": [
        {
            "asset_id": "chair",
            "role": "fit_critical",
            "source": "procedural",
            "target_dimensions": [480.0, 520.0, 860.0],
            "location": [0.0, 0.0, 0.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "anchors": ["seat-center", "floor-contact"],
            "provenance": "generated from approved dimensions",
            "checksum": "sha256:0123456789abcdef",
        }
    ],
}

OPERATION_PLAN = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "steps": [
        {
            "operation_id": "create-chair",
            "tool": "create_primitive",
            "asset_id": "chair",
            "params": {"primitive": "cube"},
            "preconditions": {"scene_clean": True},
            "expected": {"asset_exists": True},
            "rollback": {"delete_asset": True},
            "depends_on": [],
        }
    ],
}

QA_REPORT = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "assertions": [
        {
            "id": "seat-width",
            "target": 480.0,
            "actual": 479.5,
            "absolute_error": 0.5,
            "relative_error": 0.0010416667,
            "tolerance_abs": 1.0,
            "passed": True,
            "required": True,
            "scope": "seat",
        }
    ],
    "geometry": True,
    "provenance": True,
    "checkpoint": True,
    "reasons": [],
    "assumptions": [],
    "artifacts": [
        {
            "path": "artifacts/chair.blend",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        }
    ],
    "final_grade": "L2",
}


class PrecisionContractTests(unittest.TestCase):
    def test_valid_scene_spec(self):
        self.assertIs(validate_document("scene_spec", SCENE_SPEC), SCENE_SPEC)

    def test_valid_asset_manifest(self):
        self.assertIs(validate_document("asset_manifest", ASSET_MANIFEST), ASSET_MANIFEST)

    def test_valid_operation_plan(self):
        self.assertIs(validate_document("operation_plan", OPERATION_PLAN), OPERATION_PLAN)

    def test_valid_qa_report(self):
        self.assertIs(validate_document("qa_report", QA_REPORT), QA_REPORT)

    def test_zero_target_assertion_with_null_relative_error_is_valid_qa(self):
        document = copy.deepcopy(QA_REPORT)
        document["assertions"] = [
            evaluate_assertion(
                {
                    "id": "origin-offset",
                    "target": 0.0,
                    "tolerance_abs": 0.1,
                    "required": True,
                    "scope": "anchor",
                },
                0.0,
            )
        ]
        self.assertIs(validate_document("qa_report", document), document)

    def test_missing_measurement_tolerance_reports_field_path(self):
        document = copy.deepcopy(SCENE_SPEC)
        del document["measurements"][0]["tolerance_abs"]

        with self.assertRaisesRegex(
            ContractError, r"measurements/0.*tolerance_abs"
        ):
            validate_document("scene_spec", document)

    def test_expected_job_id_must_match_document(self):
        with self.assertRaisesRegex(ContractError, "job_id mismatch"):
            validate_document(
                "asset_manifest", ASSET_MANIFEST, expected_job_id="different-job"
            )

    def test_unknown_contract_name_is_rejected(self):
        with self.assertRaises(ContractError):
            validate_document("unknown", {})


if __name__ == "__main__":
    unittest.main()
