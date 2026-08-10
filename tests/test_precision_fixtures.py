import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "precision_v2"
sys.path.insert(0, str(ROOT / "precision-mcp"))

from precision_mcp.contracts import ContractError, validate_document
from precision_mcp.planner import build_plan


CASES = {
    "architecture-wall-opening": ("architecture", 1.0),
    "mechanical-enclosure-holes": ("mechanical", 0.5),
    "furniture-table-anchors": ("furniture", 1.0),
    "props-imported-tool": ("props", 1.0),
}


def load_pair(case_name):
    scene = json.loads((FIXTURES / f"{case_name}.scene.json").read_text())
    manifest = json.loads((FIXTURES / f"{case_name}.manifest.json").read_text())
    return scene, manifest


class PrecisionV2FixtureTests(unittest.TestCase):
    def test_all_fixture_pairs_validate_and_build_stable_contract_plans(self):
        self.assertEqual(len(list(FIXTURES.glob("*.json"))), 8)
        for case_name, (category, tolerance) in CASES.items():
            with self.subTest(case=case_name):
                scene, manifest = load_pair(case_name)
                job_id = scene["job_id"]
                self.assertEqual(scene["category"], category)
                self.assertEqual(scene["requested_grade"], "L1")
                self.assertTrue(scene["reference_calibrated"])
                self.assertEqual(scene["units"], "mm")
                self.assertEqual(scene["coordinate_system"], {"up": "Z", "handedness": "right"})
                self.assertEqual(manifest["job_id"], job_id)
                self.assertIs(validate_document("scene_spec", scene), scene)
                self.assertIs(validate_document("asset_manifest", manifest), manifest)

                measurements = scene["measurements"]
                ids = [item["id"] for item in measurements]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(item["required"] for item in measurements))
                self.assertTrue(all(item["tolerance_abs"] == tolerance for item in measurements))
                self.assertTrue(any(item["kind"] == "global_envelope" and item["scope"] == "global" for item in measurements))
                self.assertTrue(any(item["kind"] == "dimension" and item["scope"] == "primary" for item in measurements))
                self.assertTrue(any(item["kind"] == "contact" and item["scope"] == "contact" for item in measurements))
                self.assertTrue(any(item["kind"] == "distance" and item["scope"] == "anchor" for item in measurements))

                for asset in manifest["assets"]:
                    self.assertEqual(len(asset["target_dimensions"]), 3)
                    self.assertEqual(len(asset["location"]), 3)
                    self.assertEqual(len(asset["rotation_deg"]), 3)
                    self.assertTrue(asset["anchors"])
                    self.assertTrue(asset["provenance"])

                first = build_plan(scene, manifest, cad_available=False)
                second = build_plan(copy.deepcopy(scene), copy.deepcopy(manifest), cad_available=False)
                self.assertEqual(first, second)
                self.assertEqual(first["job_id"], job_id)
                self.assertEqual(len(first["steps"]), len(manifest["assets"]))
                self.assertIs(validate_document("operation_plan", first), first)

    def test_fixture_dimensions_and_named_features_are_exact(self):
        architecture, architecture_manifest = load_pair("architecture-wall-opening")
        self.assertEqual(architecture_manifest["assets"][0]["target_dimensions"], [4000.0, 200.0, 2800.0])
        self.assertEqual({item["id"]: item["target"] for item in architecture["measurements"]}["opening-width"], 900.0)
        self.assertEqual({item["id"]: item["target"] for item in architecture["measurements"]}["opening-height"], 2000.0)

        mechanical, mechanical_manifest = load_pair("mechanical-enclosure-holes")
        self.assertEqual(mechanical_manifest["assets"][0]["target_dimensions"], [600.0, 400.0, 250.0])
        hole_measurements = [item for item in mechanical["measurements"] if item["id"].startswith("hole-") and item["id"].endswith("-diameter")]
        self.assertEqual(len(hole_measurements), 4)
        self.assertTrue(all(item["target"] == 8.0 for item in hole_measurements))
        self.assertEqual(mechanical_manifest["assets"][0]["anchors"], ["base-center", "hole-01-center", "hole-02-center", "hole-03-center", "hole-04-center"])

        _, furniture_manifest = load_pair("furniture-table-anchors")
        self.assertEqual(furniture_manifest["assets"][0]["target_dimensions"], [1200.0, 600.0, 750.0])
        self.assertEqual(furniture_manifest["assets"][0]["anchors"], ["floor-center", "leg-front-left", "leg-front-right", "leg-rear-left", "leg-rear-right"])

    def test_imported_prop_routes_to_import_and_has_no_invented_filepath_field(self):
        scene, manifest = load_pair("props-imported-tool")
        asset = manifest["assets"][0]
        self.assertEqual(asset["source"], "imported")
        self.assertNotIn("filepath", asset)
        self.assertEqual(asset["target_dimensions"][2], 1000.0)
        self.assertEqual(asset["rotation_deg"], [0.0, 0.0, 0.0])
        plan = build_plan(scene, manifest, cad_available=False)
        self.assertEqual([step["tool"] for step in plan["steps"]], ["precision_import_asset"])

    def test_schema_rejects_a_filepath_added_to_import_manifest(self):
        _, manifest = load_pair("props-imported-tool")
        invalid = copy.deepcopy(manifest)
        invalid["assets"][0]["filepath"] = "import-cube.glb"
        with self.assertRaises(ContractError):
            validate_document("asset_manifest", invalid)


if __name__ == "__main__":
    unittest.main()
