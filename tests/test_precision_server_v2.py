import copy
import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

try:
    from mcp.server.fastmcp import FastMCP as _FastMCP  # noqa: F401
except ModuleNotFoundError:
    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class FastMCP:
        def __init__(self, _name):
            pass

        def tool(self):
            return lambda function: function

        def run(self):
            pass

    fastmcp_module.FastMCP = FastMCP
    sys.modules.update(
        {
            "mcp": mcp_module,
            "mcp.server": server_module,
            "mcp.server.fastmcp": fastmcp_module,
        }
    )

import precision_mcp.server as server
from precision_mcp.contracts import ContractError, validate_document
from precision_mcp.planner import build_plan


JOB_ID = "desk-001"

SCENE = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "category": "furniture",
    "requested_grade": "L2",
    "units": "mm",
    "coordinate_system": {"up": "Z", "handedness": "right"},
    "reference_calibrated": True,
    "measurements": [
        {
            "id": "overall-width",
            "kind": "global_envelope",
            "asset_id": "desk",
            "axis": "X",
            "target": 1200.0,
            "tolerance_abs": 1.0,
            "required": True,
            "scope": "global",
        },
        {
            "id": "desktop-depth",
            "kind": "dimension",
            "asset_id": "desk",
            "axis": "Y",
            "target": 600.0,
            "tolerance_abs": 1.0,
            "required": True,
            "scope": "primary",
        },
        {
            "id": "floor-contact",
            "kind": "contact",
            "asset_id": "desk",
            "target": 0.0,
            "tolerance_abs": 0.1,
            "required": True,
            "scope": "contact",
        },
        {
            "id": "leg-anchor-distance",
            "kind": "distance",
            "asset_id": "desk",
            "target": 450.0,
            "tolerance_abs": 0.5,
            "required": True,
            "scope": "anchor",
        },
        {
            "id": "drawer-gap",
            "kind": "gap",
            "asset_id": "desk",
            "target": 3.0,
            "tolerance_abs": 0.25,
            "required": True,
            "scope": "fit",
        },
    ],
}

MANIFEST = {
    "spec_version": "2.0",
    "job_id": JOB_ID,
    "assets": [
        {
            "asset_id": "desk",
            "role": "fit_critical",
            "source": "procedural",
            "target_dimensions": [1200.0, 600.0, 750.0],
            "location": [0.0, 0.0, 375.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "anchors": ["floor", "front-left-leg"],
            "provenance": "calibrated user dimensions",
            "checksum": "sha256:fixture",
        }
    ],
}

PASSING_MEASUREMENTS = {
    "overall-width": 1200.4,
    "desktop-depth": 599.5,
    "floor-contact": 0.05,
    "leg-anchor-distance": 449.75,
    "drawer-gap": 3.1,
}


class FakeBridge:
    def __init__(self, *, measurements=None, geometry_ok=True, provenance_ok=True):
        self.calls = []
        self.measurements = dict(measurements or PASSING_MEASUREMENTS)
        self.geometry_ok = geometry_ok
        self.provenance_ok = provenance_ok

    def call(self, command, params=None):
        payload = dict(params or {})
        self.calls.append((command, payload))
        if command == "precision_inspect_job":
            return {
                "job_id": payload["job_id"],
                "measurements": self.measurements,
                "geometry_ok": self.geometry_ok,
                "provenance_ok": self.provenance_ok,
            }
        if command in {
            "precision_begin_job",
            "precision_render_white_model",
            "precision_save_checkpoint",
            "precision_commit_job",
        }:
            filepath = payload.get("filepath") or payload.get("checkpoint")
            if filepath:
                path = Path(filepath)
                path.parent.mkdir(parents=True, exist_ok=True)
                if command != "precision_commit_job" or not path.exists():
                    path.write_bytes(f"{command}:{path.name}".encode())
        return {"ok": True, "command": command, "params": payload}


class PrecisionServerV2Tests(unittest.TestCase):
    def setUp(self):
        server._job_states.clear()
        server._qa_reports.clear()

    def _context(self, fake, directory):
        return (
            patch.object(server, "bridge", fake),
            patch.object(server, "WORKDIR", Path(directory).resolve()),
        )

    def _prepare(self, fake, directory):
        bridge_patch, workdir_patch = self._context(fake, directory)
        with bridge_patch, workdir_patch:
            return json.loads(
                server.precision_prepare_job(
                    copy.deepcopy(SCENE), copy.deepcopy(MANIFEST)
                )
            )

    def _validate(self, fake, directory, assumptions=None):
        bridge_patch, workdir_patch = self._context(fake, directory)
        with bridge_patch, workdir_patch:
            return json.loads(
                server.precision_validate_job(
                    copy.deepcopy(SCENE),
                    copy.deepcopy(MANIFEST),
                    checkpoint_exists=True,
                    assumptions=assumptions,
                )
            )

    def test_prepare_validates_persists_contracts_begins_and_returns_stable_plan(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            result = self._prepare(fake, directory)
            bundle = Path(directory).resolve() / "evidence" / JOB_ID

            self.assertEqual(result, build_plan(SCENE, MANIFEST, False))
            for name, expected_contract in (
                ("scene_spec", SCENE),
                ("asset_manifest", MANIFEST),
                ("operation_plan", result),
            ):
                path = bundle / f"{name}.json"
                self.assertTrue(path.is_file())
                persisted = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(persisted, expected_contract)
                validate_document(name, persisted, expected_job_id=JOB_ID)

            self.assertEqual(
                fake.calls,
                [
                    (
                        "precision_begin_job",
                        {
                            "job_id": JOB_ID,
                            "checkpoint": str(
                                bundle / "checkpoints" / "before.blend"
                            ),
                        },
                    )
                ],
            )
            self.assertEqual(server._job_states[JOB_ID].value, "active")

    def test_prepare_rejects_mismatched_job_ids_before_bridge_call(self):
        fake = FakeBridge()
        manifest = copy.deepcopy(MANIFEST)
        manifest["job_id"] = "different-job"
        with tempfile.TemporaryDirectory() as directory:
            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch, self.assertRaisesRegex(
                ContractError, "job_id mismatch"
            ):
                server.precision_prepare_job(copy.deepcopy(SCENE), manifest)
        self.assertEqual(fake.calls, [])

    def test_typed_wrappers_require_job_id_and_forward_exact_commands_and_params(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch:
                cases = [
                    (
                        server.precision_create_part,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "desk",
                            "primitive": "cube",
                            "target_dimensions": [1.0, 2.0, 3.0],
                            "location": [4.0, 5.0, 6.0],
                            "rotation_deg": [0.0, 0.0, 90.0],
                            "anchors": {"origin": [0.0, 0.0, 0.0]},
                            "metadata": {"role": "fit_critical"},
                        },
                    ),
                    (
                        server.precision_profile_extrude,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "rail",
                            "points": [[0.0, 0.0], [2.0, 0.0], [0.0, 1.0]],
                            "depth": 5.0,
                            "target_dimensions": [2.0, 1.0, 5.0],
                            "location": [0.0, 0.0, 0.0],
                            "rotation_deg": [0.0, 0.0, 0.0],
                            "anchors": {"tip": [0.0, 0.0, 5.0]},
                        },
                    ),
                    (
                        server.precision_import_asset,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "lamp",
                            "filepath": str(Path(directory).resolve() / "lamp.glb"),
                            "checksum": "sha256:abc",
                            "provenance": "user upload",
                            "anchors": {"base": [0.0, 0.0, 0.0]},
                        },
                    ),
                    (
                        server.precision_normalize_asset,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "lamp",
                            "source_units": "cm",
                            "target_units": "mm",
                            "source_up_axis": "Y",
                            "target_up_axis": "Z",
                            "target_dimensions": [200.0, 200.0, 500.0],
                            "scaling_mode": "uniform",
                            "provenance": "user upload",
                            "checksum": "sha256:abc",
                            "name": "PRECISION_desk-001_lamp_ROOT",
                        },
                    ),
                    (
                        server.precision_set_transform,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "lamp",
                            "name": None,
                            "location": [1.0, 2.0, 3.0],
                            "rotation_deg": [0.0, 0.0, 45.0],
                            "scale": [1.0, 1.0, 1.0],
                        },
                    ),
                    (
                        server.precision_align_anchors,
                        {
                            "job_id": JOB_ID,
                            "moving_asset_id": "lamp",
                            "target_asset_id": "desk",
                            "moving_anchor": "base",
                            "target_anchor": "top",
                            "moving_name": None,
                            "target_name": None,
                        },
                    ),
                    (
                        server.precision_patch_feature,
                        {
                            "job_id": JOB_ID,
                            "asset_id": "desk",
                            "name": None,
                            "patch": "dimensions",
                            "value": [1200.0, 600.0, 750.0],
                            "feature_id": None,
                        },
                    ),
                    (
                        server.precision_inspect_job,
                        {
                            "job_id": JOB_ID,
                            "measurements": copy.deepcopy(SCENE["measurements"]),
                        },
                    ),
                ]

                for function, params in cases:
                    with self.subTest(command=function.__name__):
                        fake.calls.clear()
                        decoded = json.loads(function(**params))
                        self.assertEqual(
                            fake.calls,
                            [(function.__name__, params)],
                        )
                        if function is not server.precision_inspect_job:
                            self.assertEqual(decoded["command"], function.__name__)

                for function, params in cases:
                    with self.subTest(invalid_job=function.__name__):
                        fake.calls.clear()
                        invalid = dict(params, job_id="")
                        with self.assertRaisesRegex(ValueError, "job_id"):
                            function(**invalid)
                        self.assertEqual(fake.calls, [])

    def test_validate_uses_raw_measurements_and_strict_gates_to_issue_l2(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            fake.calls.clear()
            with patch.object(
                server, "derive_grade", wraps=server.derive_grade
            ) as derive:
                report = self._validate(fake, directory)

            self.assertEqual(
                fake.calls,
                [
                    (
                        "precision_inspect_job",
                        {
                            "job_id": JOB_ID,
                            "measurements": SCENE["measurements"],
                        },
                    )
                ],
            )
            self.assertEqual(
                {item["id"]: item["actual"] for item in report["assertions"]},
                PASSING_MEASUREMENTS,
            )
            self.assertTrue(all(item["passed"] for item in report["assertions"]))
            self.assertIsNone(
                next(
                    item
                    for item in report["assertions"]
                    if item["id"] == "floor-contact"
                )["relative_error"]
            )
            self.assertEqual(report["final_grade"], "L2")
            self.assertEqual(report["reasons"], [])
            self.assertEqual(report["assumptions"], [])
            self.assertEqual(report["artifacts"], [])
            self.assertIs(validate_document("qa_report", report), report)
            self.assertEqual(server._job_states[JOB_ID].value, "validating")

            args = derive.call_args.args
            kwargs = derive.call_args.kwargs
            self.assertTrue(args[2])
            self.assertTrue(args[3])
            self.assertTrue(args[4])
            self.assertTrue(kwargs["assumptions_ok"])

            bundle = Path(directory).resolve() / "evidence" / JOB_ID
            self.assertEqual(
                json.loads((bundle / "qa_report.json").read_text()), report
            )
            self.assertEqual(
                (bundle / "assumptions.md").read_text(encoding="utf-8"),
                "# Unresolved assumptions\n\n",
            )

    def test_validate_missing_or_failed_required_measurement_never_false_passes(self):
        measurements = dict(PASSING_MEASUREMENTS)
        measurements.pop("leg-anchor-distance")
        measurements["overall-width"] = 1210.0
        fake = FakeBridge(measurements=measurements)
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            report = self._validate(fake, directory)

            assertions = {item["id"]: item for item in report["assertions"]}
            self.assertFalse(assertions["overall-width"]["passed"])
            self.assertFalse(assertions["leg-anchor-distance"]["passed"])
            self.assertNotEqual(report["final_grade"], "L2")
            self.assertIn(
                "missing Blender measurement: leg-anchor-distance",
                report["reasons"],
            )
            self.assertEqual(server._job_states[JOB_ID].value, "failed_qa")
            self.assertIs(validate_document("qa_report", report), report)

    def test_unresolved_assumptions_prevent_l2(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            report = self._validate(fake, directory, assumptions=["rear unseen"])
            self.assertEqual(report["final_grade"], "L1")
            self.assertIn("unresolved assumptions remain", report["reasons"])
            self.assertEqual(server._job_states[JOB_ID].value, "failed_qa")

    def test_finalize_passing_qa_writes_checksummed_artifacts_then_commits(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            self._validate(fake, directory)
            fake.calls.clear()
            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch:
                report = json.loads(
                    server.precision_finalize_job(
                        copy.deepcopy(SCENE), copy.deepcopy(MANIFEST)
                    )
                )

            bundle = Path(directory).resolve() / "evidence" / JOB_ID
            orthographic = bundle / "previews" / "orthographic.png"
            perspective = bundle / "previews" / "perspective.png"
            final_checkpoint = bundle / "checkpoints" / "final.blend"
            self.assertEqual(
                fake.calls,
                [
                    (
                        "precision_render_white_model",
                        {
                            "job_id": JOB_ID,
                            "filepath": str(orthographic),
                            "view": "orthographic",
                            "resolution_x": 640,
                            "resolution_y": 360,
                        },
                    ),
                    (
                        "precision_render_white_model",
                        {
                            "job_id": JOB_ID,
                            "filepath": str(perspective),
                            "view": "perspective",
                            "resolution_x": 640,
                            "resolution_y": 360,
                        },
                    ),
                    (
                        "precision_save_checkpoint",
                        {"job_id": JOB_ID, "filepath": str(final_checkpoint)},
                    ),
                    (
                        "precision_commit_job",
                        {"job_id": JOB_ID, "filepath": str(final_checkpoint)},
                    ),
                ],
            )
            self.assertEqual(server._job_states[JOB_ID].value, "committed")
            self.assertEqual(report["final_grade"], "L2")
            self.assertEqual(
                [item["path"] for item in report["artifacts"]],
                [
                    "previews/orthographic.png",
                    "previews/perspective.png",
                    "checkpoints/final.blend",
                ],
            )
            for artifact in report["artifacts"]:
                path = bundle / artifact["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(
                    artifact["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
                )
            self.assertIs(validate_document("qa_report", report), report)
            self.assertEqual(
                json.loads((bundle / "qa_report.json").read_text()), report
            )

    def test_finalize_failed_required_saves_failure_without_commit(self):
        measurements = dict(PASSING_MEASUREMENTS, **{"drawer-gap": 9.0})
        fake = FakeBridge(measurements=measurements)
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            failed_report = self._validate(fake, directory)
            self.assertNotEqual(failed_report["final_grade"], "L2")
            fake.calls.clear()

            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch:
                report = json.loads(
                    server.precision_finalize_job(
                        copy.deepcopy(SCENE), copy.deepcopy(MANIFEST)
                    )
                )

            failed_path = (
                Path(directory).resolve()
                / "evidence"
                / JOB_ID
                / "checkpoints"
                / "failed.blend"
            )
            self.assertEqual(
                fake.calls,
                [
                    (
                        "precision_save_checkpoint",
                        {"job_id": JOB_ID, "filepath": str(failed_path)},
                    )
                ],
            )
            self.assertNotIn(
                "precision_commit_job", [command for command, _ in fake.calls]
            )
            self.assertTrue(failed_path.is_file())
            self.assertNotEqual(report["final_grade"], "L2")
            self.assertEqual(server._job_states[JOB_ID].value, "failed_qa")
            self.assertIs(validate_document("qa_report", report), report)

    def test_server_contains_no_production_scene_or_manifest_fixtures(self):
        source = Path(server.__file__).read_text(encoding="utf-8")
        self.assertNotIn("SCENE =", source)
        self.assertNotIn("MANIFEST =", source)


if __name__ == "__main__":
    unittest.main()
