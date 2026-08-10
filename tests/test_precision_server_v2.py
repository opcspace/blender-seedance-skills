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
    def __init__(
        self,
        *,
        measurements=None,
        geometry_ok=True,
        provenance_ok=True,
        cad_status=None,
        cad_error=None,
    ):
        self.calls = []
        self.measurements = dict(measurements or PASSING_MEASUREMENTS)
        self.geometry_ok = geometry_ok
        self.provenance_ok = provenance_ok
        self.cad_status = dict(cad_status or {})
        self.cad_error = cad_error

    def call(self, command, params=None):
        payload = dict(params or {})
        self.calls.append((command, payload))
        if command == "precision_cad_status":
            if self.cad_error is not None:
                raise self.cad_error
            return self.cad_status
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
        server._job_records.clear()

    def _context(self, fake, directory):
        return (
            patch.object(server, "bridge", fake),
            patch.object(server, "WORKDIR", Path(directory).resolve()),
        )

    def _prepare(
        self,
        fake,
        directory,
        *,
        scene=None,
        manifest=None,
        cad_available=False,
    ):
        bridge_patch, workdir_patch = self._context(fake, directory)
        with bridge_patch, workdir_patch:
            return json.loads(
                server.precision_prepare_job(
                    copy.deepcopy(scene or SCENE),
                    copy.deepcopy(manifest or MANIFEST),
                    cad_available=cad_available,
                )
            )

    def _validate(
        self,
        fake,
        directory,
        assumptions=None,
        *,
        scene=None,
        manifest=None,
        checkpoint_exists=True,
    ):
        bridge_patch, workdir_patch = self._context(fake, directory)
        with bridge_patch, workdir_patch:
            return json.loads(
                server.precision_validate_job(
                    copy.deepcopy(scene or SCENE),
                    copy.deepcopy(manifest or MANIFEST),
                    checkpoint_exists=checkpoint_exists,
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
            record = server._job_records[JOB_ID]
            self.assertEqual(record.state.value, "active")
            self.assertEqual(record.plan_status, "eligible")
            self.assertEqual(len(record.scene_digest), 64)
            self.assertEqual(len(record.manifest_digest), 64)
            self.assertEqual(len(record.plan_digest), 64)

    def test_prepare_rejects_duplicate_active_job_before_second_begin(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            with self.assertRaisesRegex(ValueError, "already active"):
                self._prepare(fake, directory)
            self.assertEqual(
                [command for command, _ in fake.calls], ["precision_begin_job"]
            )

    def test_blocked_cad_and_tripo_plans_persist_without_begin_and_reject_execution(self):
        for source, expected_tool in (
            ("cad_sketcher", "backend_unavailable"),
            ("tripo", "external_pending"),
        ):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                server._job_records.clear()
                fake = FakeBridge()
                manifest = copy.deepcopy(MANIFEST)
                manifest["assets"][0]["source"] = source
                plan = self._prepare(fake, directory, manifest=manifest)

                self.assertEqual(plan["steps"][0]["tool"], expected_tool)
                expected_calls = (
                    [("precision_cad_status", {})]
                    if source == "cad_sketcher"
                    else []
                )
                self.assertEqual(fake.calls, expected_calls)
                record = server._job_records[JOB_ID]
                self.assertEqual(record.plan_status, "blocked")
                self.assertEqual(record.state.value, "planned")
                self.assertEqual(len(record.backend_status_digest), 64)
                bundle = Path(directory).resolve() / "evidence" / JOB_ID
                self.assertTrue((bundle / "scene_spec.json").is_file())
                self.assertTrue((bundle / "asset_manifest.json").is_file())
                self.assertTrue((bundle / "operation_plan.json").is_file())

                bridge_patch, workdir_patch = self._context(fake, directory)
                with bridge_patch, workdir_patch:
                    with self.assertRaisesRegex(ValueError, "blocked"):
                        server.precision_create_part(
                            JOB_ID, "desk", "cube", [1.0, 1.0, 1.0]
                        )
                    with self.assertRaisesRegex(ValueError, "blocked"):
                        server.precision_validate_job(SCENE, manifest)
                    with self.assertRaisesRegex(ValueError, "blocked"):
                        server.precision_finalize_job(SCENE, manifest)
                self.assertEqual(fake.calls, expected_calls)
                server._job_records.clear()

    def test_caller_cannot_override_runtime_cad_status(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["assets"][0]["source"] = "cad_sketcher"
        for label, status in (
            (
                "runtime unavailable",
                {
                    "available": False,
                    "solver_available": True,
                    "operator_available": True,
                    "solver_registered": True,
                },
            ),
            (
                "solver unavailable",
                {
                    "available": True,
                    "solver_available": False,
                    "operator_available": True,
                    "solver_registered": True,
                },
            ),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                server._job_records.clear()
                fake = FakeBridge(cad_status=status)
                plan = self._prepare(
                    fake,
                    directory,
                    manifest=manifest,
                    cad_available=True,
                )
                self.assertEqual(plan["steps"][0]["tool"], "backend_unavailable")
                self.assertEqual(fake.calls, [("precision_cad_status", {})])
                self.assertEqual(
                    server._job_records[JOB_ID].plan_status, "blocked"
                )
                server._job_records.clear()

    def test_fully_healthy_runtime_cad_status_is_eligible(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["assets"][0]["source"] = "cad_sketcher"
        healthy = {
            "available": True,
            "solver_available": True,
            "operator_available": True,
            "solver_registered": True,
        }
        fake = FakeBridge(cad_status=healthy)
        with tempfile.TemporaryDirectory() as directory:
            plan = self._prepare(fake, directory, manifest=manifest)
            self.assertEqual(
                plan["steps"][0]["tool"], "precision_create_cad_part"
            )
            self.assertEqual(
                [command for command, _ in fake.calls],
                ["precision_cad_status", "precision_begin_job"],
            )
            record = server._job_records[JOB_ID]
            self.assertEqual(record.plan_status, "eligible")
            self.assertEqual(dict(record.backend_status), healthy)
            self.assertEqual(len(record.backend_status_digest), 64)

    def test_runtime_cad_status_failure_blocks_prepare(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["assets"][0]["source"] = "cad_sketcher"
        fake = FakeBridge(cad_error=RuntimeError("CAD probe failed"))
        with tempfile.TemporaryDirectory() as directory:
            plan = self._prepare(fake, directory, manifest=manifest)
            self.assertEqual(plan["steps"][0]["tool"], "backend_unavailable")
            self.assertEqual(fake.calls, [("precision_cad_status", {})])
            self.assertEqual(
                server._job_records[JOB_ID].plan_status, "blocked"
            )

    def test_blocked_job_can_be_reprepared_with_locally_eligible_manifest(self):
        fake = FakeBridge()
        blocked = copy.deepcopy(MANIFEST)
        blocked["assets"][0]["source"] = "tripo"
        eligible = copy.deepcopy(MANIFEST)
        eligible["assets"][0]["source"] = "imported"
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory, manifest=blocked)
            plan = self._prepare(fake, directory, manifest=eligible)
            self.assertEqual(plan["steps"][0]["tool"], "precision_import_asset")
            self.assertEqual(
                [command for command, _ in fake.calls], ["precision_begin_job"]
            )
            self.assertEqual(
                server._job_records[JOB_ID].plan_status, "eligible"
            )

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
            self._prepare(fake, directory)
            fake.calls.clear()
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
            record = server._job_records[JOB_ID]
            self.assertEqual(record.state.value, "validating")
            self.assertEqual(len(record.qa_report_digest), 64)

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
            self.assertEqual(
                server._job_records[JOB_ID].state.value, "failed_qa"
            )
            self.assertIs(validate_document("qa_report", report), report)

    def test_unresolved_assumptions_prevent_l2(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            report = self._validate(fake, directory, assumptions=["rear unseen"])
            self.assertEqual(report["final_grade"], "L1")
            self.assertIn("unresolved assumptions remain", report["reasons"])
            self.assertEqual(
                server._job_records[JOB_ID].state.value, "failed_qa"
            )

    def test_validate_rejects_unprepared_job_before_bridge_call(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch, self.assertRaisesRegex(
                ValueError, "not prepared"
            ):
                server.precision_validate_job(SCENE, MANIFEST)
        self.assertEqual(fake.calls, [])

    def test_checkpoint_argument_cannot_bypass_missing_prepared_checkpoint(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            checkpoint = (
                Path(directory).resolve()
                / "evidence"
                / JOB_ID
                / "checkpoints"
                / "before.blend"
            )
            checkpoint.unlink()
            report = self._validate(
                fake, directory, checkpoint_exists=True
            )
            self.assertFalse(report["checkpoint"])
            self.assertNotEqual(report["final_grade"], "L2")
            self.assertIn("final checkpoint missing", report["reasons"])

    def test_validate_rejects_same_id_altered_scene_or_manifest(self):
        for changed_document in ("scene", "manifest"):
            with self.subTest(changed_document=changed_document), tempfile.TemporaryDirectory() as directory:
                fake = FakeBridge()
                self._prepare(fake, directory)
                fake.calls.clear()
                scene = copy.deepcopy(SCENE)
                manifest = copy.deepcopy(MANIFEST)
                if changed_document == "scene":
                    scene["measurements"][0]["target"] += 1.0
                else:
                    manifest["assets"][0]["location"][0] += 1.0
                with self.assertRaisesRegex(ValueError, "prepared contracts"):
                    self._validate(
                        fake,
                        directory,
                        scene=scene,
                        manifest=manifest,
                    )
                self.assertEqual(fake.calls, [])
                server._job_records.clear()

    def test_validate_accepts_whitespace_only_changes_to_persisted_contracts(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            bundle = Path(directory).resolve() / "evidence" / JOB_ID
            for name in ("scene_spec", "asset_manifest", "operation_plan"):
                path = bundle / f"{name}.json"
                document = json.loads(path.read_text(encoding="utf-8"))
                path.write_text(
                    json.dumps(document, ensure_ascii=False, indent=6) + "\n\n",
                    encoding="utf-8",
                )
            report = self._validate(fake, directory)
            self.assertEqual(report["final_grade"], "L2")

    def test_tampered_persisted_plan_rejects_validate_and_finalize(self):
        for phase in ("validate", "finalize"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                server._job_records.clear()
                fake = FakeBridge()
                self._prepare(fake, directory)
                if phase == "finalize":
                    self._validate(fake, directory)
                fake.calls.clear()
                plan_path = (
                    Path(directory).resolve()
                    / "evidence"
                    / JOB_ID
                    / "operation_plan.json"
                )
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["steps"] = []
                plan_path.write_text(json.dumps(plan), encoding="utf-8")

                bridge_patch, workdir_patch = self._context(fake, directory)
                with bridge_patch, workdir_patch, self.assertRaisesRegex(
                    ValueError, "bound evidence"
                ):
                    if phase == "validate":
                        server.precision_validate_job(SCENE, MANIFEST)
                    else:
                        server.precision_finalize_job(SCENE, MANIFEST)
                self.assertEqual(fake.calls, [])
                server._job_records.clear()

    def test_tampered_persisted_scene_or_manifest_rejects_validate_and_finalize(self):
        for phase in ("validate", "finalize"):
            for contract_name in ("scene_spec", "asset_manifest"):
                with self.subTest(
                    phase=phase, contract=contract_name
                ), tempfile.TemporaryDirectory() as directory:
                    server._job_records.clear()
                    fake = FakeBridge()
                    self._prepare(fake, directory)
                    if phase == "finalize":
                        self._validate(fake, directory)
                    fake.calls.clear()
                    path = (
                        Path(directory).resolve()
                        / "evidence"
                        / JOB_ID
                        / f"{contract_name}.json"
                    )
                    document = json.loads(path.read_text(encoding="utf-8"))
                    if contract_name == "scene_spec":
                        document["measurements"][0]["target"] += 1.0
                    else:
                        document["assets"][0]["location"][0] += 1.0
                    path.write_text(json.dumps(document), encoding="utf-8")

                    bridge_patch, workdir_patch = self._context(fake, directory)
                    with bridge_patch, workdir_patch, self.assertRaisesRegex(
                        ValueError, "bound evidence"
                    ):
                        if phase == "validate":
                            server.precision_validate_job(SCENE, MANIFEST)
                        else:
                            server.precision_finalize_job(SCENE, MANIFEST)
                    self.assertEqual(fake.calls, [])
                    server._job_records.clear()

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
            self.assertEqual(
                server._job_records[JOB_ID].state.value, "committed"
            )
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
            self.assertEqual(
                server._job_records[JOB_ID].state.value, "failed_qa"
            )
            self.assertIs(validate_document("qa_report", report), report)

    def test_finalize_rejects_changed_contracts_and_tampered_bound_report(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory:
            self._prepare(fake, directory)
            self._validate(fake, directory)
            fake.calls.clear()
            bridge_patch, workdir_patch = self._context(fake, directory)
            with bridge_patch, workdir_patch:
                changed_scene = copy.deepcopy(SCENE)
                changed_scene["measurements"][0]["target"] += 1.0
                changed_manifest = copy.deepcopy(MANIFEST)
                changed_manifest["assets"][0]["location"][0] += 1.0
                for scene, manifest in (
                    (changed_scene, MANIFEST),
                    (SCENE, changed_manifest),
                ):
                    with self.assertRaisesRegex(
                        ValueError, "prepared contracts"
                    ):
                        server.precision_finalize_job(scene, manifest)
                record = server._job_records[JOB_ID]
                record.qa_report["reasons"].append("tampered")
                with self.assertRaisesRegex(ValueError, "QA report binding"):
                    server.precision_finalize_job(SCENE, MANIFEST)
            self.assertNotIn(
                "precision_commit_job", [command for command, _ in fake.calls]
            )

    def test_server_contains_no_production_scene_or_manifest_fixtures(self):
        source = Path(server.__file__).read_text(encoding="utf-8")
        self.assertNotIn("SCENE =", source)
        self.assertNotIn("MANIFEST =", source)


if __name__ == "__main__":
    unittest.main()
