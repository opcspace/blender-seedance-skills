import ast
import unittest
from pathlib import Path


ADDON = (
    Path(__file__).parents[1]
    / "precision-mcp"
    / "blender_addon"
    / "precision_addon.py"
)


class PrecisionAddonSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ADDON.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_addon_has_no_arbitrary_execution_command(self):
        self.assertNotIn("execute_blender_code", self.source)
        self.assertNotIn("exec(", self.source)

    def test_addon_parses_and_defines_v2_job_commands(self):
        self.assertIsNotNone(self.tree)
        for command in (
            "precision_begin_job",
            "precision_abort_job",
            "precision_commit_job",
        ):
            self.assertIn(command, self.source)

    def test_network_requests_are_framed_and_correlated(self):
        for marker in ("struct.unpack", '"!I"', "_recv_exact", "request_id"):
            self.assertIn(marker, self.source)
        self.assertIn("MAX_FRAME_BYTES", self.source)

    def test_blender_execution_is_queued_on_application_timer(self):
        self.assertIn("bpy.app.timers.register", self.source)
        self.assertIn("_execute_queued", self.source)
        handle = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_handle"
        )
        called_names = {
            node.func.id
            for node in ast.walk(handle)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("execute", called_names)

    def test_addon_defines_v2_creation_and_import_commands(self):
        for command in (
            "precision_create_part",
            "precision_import_asset",
            "precision_normalize_asset",
            "precision_profile_extrude",
        ):
            self.assertIn(command, self.source)

    def test_import_and_normalization_are_explicit_and_job_scoped(self):
        for marker in (
            "UNIT_TO_METERS",
            "source_units",
            "target_units",
            "source_up_axis",
            "scaling_mode",
            "provenance",
            "checksum",
            "bpy.ops.import_scene.gltf",
            "bpy.ops.wm.fbx_import",
            "bpy.ops.import_scene.fbx",
            "_safe_work_path",
            "_track_created",
        ):
            self.assertIn(marker, self.source)

    def test_profile_extrusion_rejects_self_intersections(self):
        self.assertIn("_validate_simple_polygon", self.source)
        self.assertIn("self-intersecting", self.source)


if __name__ == "__main__":
    unittest.main()
