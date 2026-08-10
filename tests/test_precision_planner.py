import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.adapters.base import AdapterStatus
from precision_mcp.adapters.blender import BlenderAdapter
from precision_mcp.adapters.cad_sketcher import CadSketcherAdapter
from precision_mcp.adapters.seedance import SeedanceAdapter
from precision_mcp.adapters.tripo import TripoAdapter
from precision_mcp.contracts import validate_document
from precision_mcp.planner import build_plan


DEFERRED_REASON = "online integration is deferred in Precision Core V2 phase one"


def _asset(asset_id, role, source):
    return {"asset_id": asset_id, "role": role, "source": source}


class PrecisionPlannerTests(unittest.TestCase):
    def setUp(self):
        self.scene = {"spec_version": "2.0", "job_id": "fixture-1"}

    def _plan(self, assets, cad_available=False):
        manifest = {
            "spec_version": "2.0",
            "job_id": "fixture-1",
            "assets": assets,
        }
        return build_plan(self.scene, manifest, cad_available)

    def test_fit_critical_procedural_assets_use_blender(self):
        plan = self._plan([_asset("panel", "fit_critical", "procedural")])
        self.assertEqual(plan["steps"][0]["tool"], "precision_create_part")

    def test_visual_shell_tripo_is_external_pending(self):
        plan = self._plan([_asset("ornament", "visual_shell", "tripo")])
        self.assertEqual(plan["steps"][0]["tool"], "external_pending")

    def test_cad_request_does_not_silently_fall_back(self):
        plan = self._plan([_asset("profile", "fit_critical", "cad_sketcher")])
        self.assertEqual(plan["steps"][0]["tool"], "backend_unavailable")

    def test_available_cad_request_uses_cad_backend(self):
        plan = self._plan(
            [_asset("profile", "fit_critical", "cad_sketcher")],
            cad_available=True,
        )
        self.assertEqual(plan["steps"][0]["tool"], "precision_create_cad_part")

    def test_imported_and_user_assets_are_imported(self):
        plan = self._plan(
            [
                _asset("reference", "stage", "imported"),
                _asset("user-mesh", "visual_shell", "user"),
            ]
        )
        self.assertEqual(
            [step["tool"] for step in plan["steps"]],
            ["precision_import_asset", "precision_import_asset"],
        )

    def test_manifest_job_mismatch_is_rejected(self):
        manifest = {"spec_version": "2.0", "job_id": "other", "assets": []}
        with self.assertRaisesRegex(ValueError, "job_id mismatch"):
            build_plan(self.scene, manifest, False)

    def test_asset_order_does_not_change_contract_valid_plan(self):
        assets = [
            _asset("b", "fit_critical", "procedural"),
            _asset("a", "fit_critical", "procedural"),
        ]
        first = self._plan(copy.deepcopy(assets))
        second = self._plan(list(reversed(copy.deepcopy(assets))))
        self.assertEqual(first, second)
        self.assertEqual(
            [step["operation_id"] for step in first["steps"]],
            ["001-a", "002-b"],
        )
        self.assertIs(validate_document("operation_plan", first), first)

    def test_adapter_statuses_are_explicit(self):
        self.assertEqual(BlenderAdapter().status(), AdapterStatus(True))
        self.assertEqual(TripoAdapter().status().reason, DEFERRED_REASON)
        self.assertEqual(SeedanceAdapter().status().reason, DEFERRED_REASON)
        runtime_status = AdapterStatus(False, "extension disabled", {"version": "0.27"})
        self.assertIs(CadSketcherAdapter(runtime_status).status(), runtime_status)


if __name__ == "__main__":
    unittest.main()
