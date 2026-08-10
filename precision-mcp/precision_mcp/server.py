import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from precision_mcp.contracts import validate_document
from precision_mcp.evidence import EvidenceBundle, JobState
from precision_mcp.measurements import derive_grade, evaluate_assertion
from precision_mcp.planner import build_plan
from precision_mcp.transport import BlenderBridge


HOST = os.getenv("PRECISION_BLENDER_HOST", "127.0.0.1")
PORT = int(os.getenv("PRECISION_BLENDER_PORT", "9877"))
WORKDIR = Path(os.getenv("PRECISION_WORKDIR", os.getcwd())).resolve()
bridge = BlenderBridge(HOST, PORT)
mcp = FastMCP("BlenderPrecisionMCP")
_JOB_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_GRADE_RANK = {"L0": 0, "L1": 1, "L2": 2}
_BLOCKED_TOOLS = {"backend_unavailable", "external_pending"}


@dataclass
class JobRecord:
    state: JobState
    scene_digest: str
    manifest_digest: str
    plan_digest: str
    plan_status: str
    begin_checkpoint: str | None
    qa_report: dict[str, Any] | None = None
    qa_report_digest: str | None = None
    qa_scene_digest: str | None = None
    qa_manifest_digest: str | None = None


_job_records: dict[str, JobRecord] = {}


def _call(name: str, params: dict[str, Any] | None = None) -> str:
    return json.dumps(bridge.call(name, params), ensure_ascii=False, indent=2)


def _json(document: Any) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2)


def _document_digest(document: dict[str, Any]) -> str:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _document_snapshot(document: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(document, ensure_ascii=False))


def _require_job_id(job_id: str) -> str:
    if not isinstance(job_id, str) or _JOB_ID.fullmatch(job_id) is None:
        raise ValueError("job_id must match ^[a-z0-9][a-z0-9-]{0,63}$")
    return job_id


def _require_eligible_record(
    job_id: str, allowed_states: set[str]
) -> JobRecord:
    validated_job_id = _require_job_id(job_id)
    record = _job_records.get(validated_job_id)
    if record is None:
        raise ValueError(f"job is not prepared: {validated_job_id}")
    if record.plan_status != "eligible":
        raise ValueError(f"job plan is blocked: {validated_job_id}")
    if record.state.value not in allowed_states:
        allowed = ", ".join(sorted(allowed_states))
        raise ValueError(
            f"job state is {record.state.value}; expected one of: {allowed}"
        )
    return record


def _require_matching_contracts(
    job_id: str,
    scene_spec: dict[str, Any],
    asset_manifest: dict[str, Any],
    allowed_states: set[str],
) -> JobRecord:
    record = _require_eligible_record(job_id, allowed_states)
    if (
        _document_digest(scene_spec) != record.scene_digest
        or _document_digest(asset_manifest) != record.manifest_digest
    ):
        raise ValueError("supplied contracts do not match prepared contracts")
    return record


def _typed_call(command: str, job_id: str, params: dict[str, Any]) -> str:
    _require_eligible_record(job_id, {"active", "validating"})
    return _call(command, {"job_id": job_id, **params})


def _validated_inputs(
    scene_spec: dict[str, Any], asset_manifest: dict[str, Any]
) -> str:
    validate_document("scene_spec", scene_spec)
    job_id = _require_job_id(scene_spec["job_id"])
    validate_document("asset_manifest", asset_manifest, expected_job_id=job_id)
    return job_id


def _state_for_validation(record: JobRecord) -> JobState:
    state = record.state
    if state.value == "failed_qa":
        state.transition("active")
    state.transition("validating")
    return state


def _report_assertion(assertion: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "target",
        "actual",
        "absolute_error",
        "relative_error",
        "tolerance_abs",
        "passed",
        "required",
        "scope",
    )
    return {field: assertion[field] for field in fields}


def _replace_artifact(
    report: dict[str, Any], bundle: EvidenceBundle, path: Path
) -> None:
    relative_path = path.relative_to(bundle.root).as_posix()
    artifact = {"path": relative_path, "sha256": bundle.sha256(path)}
    report["artifacts"] = [
        existing
        for existing in report["artifacts"]
        if existing["path"] != relative_path
    ]
    report["artifacts"].append(artifact)


@mcp.tool()
def precision_prepare_job(
    scene_spec: dict[str, Any],
    asset_manifest: dict[str, Any],
    cad_available: bool = False,
) -> str:
    """Validate V2 contracts, persist a deterministic plan and begin a job."""
    job_id = _validated_inputs(scene_spec, asset_manifest)
    existing = _job_records.get(job_id)
    if existing is not None and not (
        existing.plan_status == "blocked" and existing.state.value == "planned"
    ):
        if existing.state.value in {"active", "validating"}:
            raise ValueError(f"job is already active: {job_id}")
        raise ValueError(
            f"job cannot be prepared from state: {existing.state.value}"
        )
    plan = build_plan(scene_spec, asset_manifest, bool(cad_available))
    validate_document("operation_plan", plan, expected_job_id=job_id)
    scene_digest = _document_digest(scene_spec)
    manifest_digest = _document_digest(asset_manifest)
    plan_digest = _document_digest(plan)
    blocked = any(step["tool"] in _BLOCKED_TOOLS for step in plan["steps"])
    plan_status = "blocked" if blocked else "eligible"

    bundle = EvidenceBundle(WORKDIR, job_id)
    bundle.write_contract("scene_spec", scene_spec)
    bundle.write_contract("asset_manifest", asset_manifest)
    bundle.write_contract("operation_plan", plan)
    checkpoint = bundle.checkpoint_path("before")
    state = JobState(job_id)
    if blocked:
        _job_records[job_id] = JobRecord(
            state=state,
            scene_digest=scene_digest,
            manifest_digest=manifest_digest,
            plan_digest=plan_digest,
            plan_status=plan_status,
            begin_checkpoint=None,
        )
        return _json(plan)

    bridge.call(
        "precision_begin_job",
        {"job_id": job_id, "checkpoint": str(checkpoint)},
    )
    state.transition("active")
    _job_records[job_id] = JobRecord(
        state=state,
        scene_digest=scene_digest,
        manifest_digest=manifest_digest,
        plan_digest=plan_digest,
        plan_status=plan_status,
        begin_checkpoint=str(checkpoint),
    )
    return _json(plan)


@mcp.tool()
def precision_create_part(
    job_id: str,
    asset_id: str,
    primitive: str,
    target_dimensions: list[float],
    location: list[float] | None = None,
    rotation_deg: list[float] | None = None,
    anchors: dict[str, list[float]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Create one exact primitive owned by a V2 job."""
    return _typed_call(
        "precision_create_part",
        job_id,
        {
            "asset_id": asset_id,
            "primitive": primitive,
            "target_dimensions": target_dimensions,
            "location": location,
            "rotation_deg": rotation_deg,
            "anchors": anchors,
            "metadata": metadata,
        },
    )


@mcp.tool()
def precision_profile_extrude(
    job_id: str,
    asset_id: str,
    points: list[list[float]],
    depth: float,
    target_dimensions: list[float] | None = None,
    location: list[float] | None = None,
    rotation_deg: list[float] | None = None,
    anchors: dict[str, list[float]] | None = None,
) -> str:
    """Extrude one simple profile inside a V2 job."""
    return _typed_call(
        "precision_profile_extrude",
        job_id,
        {
            "asset_id": asset_id,
            "points": points,
            "depth": depth,
            "target_dimensions": target_dimensions,
            "location": location,
            "rotation_deg": rotation_deg,
            "anchors": anchors,
        },
    )


@mcp.tool()
def precision_import_asset(
    job_id: str,
    asset_id: str,
    filepath: str,
    checksum: str | None = None,
    provenance: str | None = None,
    anchors: dict[str, list[float]] | None = None,
) -> str:
    """Import one allow-listed asset path into a V2 job."""
    validated_job_id = _require_job_id(job_id)
    return _typed_call(
        "precision_import_asset",
        validated_job_id,
        {
            "asset_id": asset_id,
            "filepath": _safe_path(filepath),
            "checksum": checksum,
            "provenance": provenance,
            "anchors": anchors,
        },
    )


@mcp.tool()
def precision_normalize_asset(
    job_id: str,
    asset_id: str,
    source_units: str = "m",
    target_units: str = "m",
    source_up_axis: str = "Z",
    target_up_axis: str = "Z",
    target_dimensions: list[float] | None = None,
    scaling_mode: str = "explicit_xyz",
    provenance: str | None = None,
    checksum: str | None = None,
    name: str | None = None,
) -> str:
    """Normalize units, axes and dimensions for one imported V2 asset."""
    return _typed_call(
        "precision_normalize_asset",
        job_id,
        {
            "asset_id": asset_id,
            "source_units": source_units,
            "target_units": target_units,
            "source_up_axis": source_up_axis,
            "target_up_axis": target_up_axis,
            "target_dimensions": target_dimensions,
            "scaling_mode": scaling_mode,
            "provenance": provenance,
            "checksum": checksum,
            "name": name,
        },
    )


@mcp.tool()
def precision_set_transform(
    job_id: str,
    asset_id: str | None = None,
    name: str | None = None,
    location: list[float] | None = None,
    rotation_deg: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Set an explicit transform on a named V2 job asset."""
    return _typed_call(
        "precision_set_transform",
        job_id,
        {
            "asset_id": asset_id,
            "name": name,
            "location": location,
            "rotation_deg": rotation_deg,
            "scale": scale,
        },
    )


@mcp.tool()
def precision_align_anchors(
    job_id: str,
    moving_asset_id: str | None = None,
    target_asset_id: str | None = None,
    moving_anchor: str | list[float] | None = None,
    target_anchor: str | list[float] | None = None,
    moving_name: str | None = None,
    target_name: str | None = None,
) -> str:
    """Align two declared local anchors inside one V2 job."""
    return _typed_call(
        "precision_align_anchors",
        job_id,
        {
            "moving_asset_id": moving_asset_id,
            "target_asset_id": target_asset_id,
            "moving_anchor": moving_anchor,
            "target_anchor": target_anchor,
            "moving_name": moving_name,
            "target_name": target_name,
        },
    )


@mcp.tool()
def precision_patch_feature(
    job_id: str,
    asset_id: str | None = None,
    name: str | None = None,
    patch: str = "dimensions",
    value: Any = None,
    feature_id: str | None = None,
) -> str:
    """Patch one allow-listed V2 dimension, transform or named feature."""
    return _typed_call(
        "precision_patch_feature",
        job_id,
        {
            "asset_id": asset_id,
            "name": name,
            "patch": patch,
            "value": value,
            "feature_id": feature_id,
        },
    )


@mcp.tool()
def precision_inspect_job(
    job_id: str, measurements: list[dict[str, Any]] | None = None
) -> str:
    """Return raw Blender geometry and declared V2 measurements for one job."""
    return _typed_call(
        "precision_inspect_job",
        job_id,
        {"measurements": measurements},
    )


@mcp.tool()
def precision_validate_job(
    scene_spec: dict[str, Any],
    asset_manifest: dict[str, Any],
    checkpoint_exists: bool | None = None,
    assumptions: list[str] | None = None,
) -> str:
    """Evaluate V2 QA; deprecated checkpoint_exists is ignored for safety."""
    job_id = _validated_inputs(scene_spec, asset_manifest)
    record = _require_matching_contracts(
        job_id,
        scene_spec,
        asset_manifest,
        {"active", "failed_qa"},
    )
    unresolved = list(assumptions or [])
    state = _state_for_validation(record)
    bundle = EvidenceBundle(WORKDIR, job_id)
    before_checkpoint = bundle.checkpoint_path("before")
    checkpoint_ok = (
        record.begin_checkpoint == str(before_checkpoint)
        and before_checkpoint.is_file()
    )
    inspection = bridge.call(
        "precision_inspect_job",
        {"job_id": job_id, "measurements": scene_spec["measurements"]},
    )
    raw_measurements = inspection.get("measurements") or {}
    evaluated: list[dict[str, Any]] = []
    missing_reasons: list[str] = []
    for assertion in scene_spec["measurements"]:
        measurement_id = assertion["id"]
        if measurement_id not in raw_measurements:
            result = evaluate_assertion(assertion, assertion["target"])
            result["passed"] = False
            missing_reasons.append(
                f"missing Blender measurement: {measurement_id}"
            )
        else:
            result = evaluate_assertion(
                assertion, raw_measurements[measurement_id]
            )
        evaluated.append(result)

    grade = derive_grade(
        bool(scene_spec["reference_calibrated"]),
        evaluated,
        bool(inspection.get("geometry_ok", False)),
        checkpoint_ok,
        bool(inspection.get("provenance_ok", False)),
        assumptions_ok=len(unresolved) == 0,
    )
    reasons = list(dict.fromkeys([*grade["reasons"], *missing_reasons]))
    report = {
        "spec_version": "2.0",
        "job_id": job_id,
        "assertions": [_report_assertion(item) for item in evaluated],
        "geometry": bool(inspection.get("geometry_ok", False)),
        "provenance": bool(inspection.get("provenance_ok", False)),
        "checkpoint": checkpoint_ok,
        "reasons": reasons,
        "assumptions": unresolved,
        "artifacts": [],
        "final_grade": grade["grade"],
    }
    validate_document("qa_report", report, expected_job_id=job_id)
    bundle.write_contract("qa_report", report)
    bundle.write_assumptions(unresolved)
    record.qa_report = _document_snapshot(report)
    record.qa_report_digest = _document_digest(record.qa_report)
    record.qa_scene_digest = record.scene_digest
    record.qa_manifest_digest = record.manifest_digest

    failed_required = any(
        assertion["required"] and not assertion["passed"]
        for assertion in report["assertions"]
    )
    below_requested = _GRADE_RANK[report["final_grade"]] < _GRADE_RANK[
        scene_spec["requested_grade"]
    ]
    if failed_required or below_requested:
        state.transition("failed_qa")
    return _json(report)


@mcp.tool()
def precision_finalize_job(
    scene_spec: dict[str, Any], asset_manifest: dict[str, Any]
) -> str:
    """Finalize current V2 QA evidence, committing only a strict passing L2 job."""
    job_id = _validated_inputs(scene_spec, asset_manifest)
    record = _require_matching_contracts(
        job_id,
        scene_spec,
        asset_manifest,
        {"validating", "failed_qa"},
    )
    if record.qa_report is None or record.qa_report_digest is None:
        raise ValueError("job has no validated QA report")
    if (
        record.qa_scene_digest != record.scene_digest
        or record.qa_manifest_digest != record.manifest_digest
        or _document_digest(record.qa_report) != record.qa_report_digest
    ):
        raise ValueError("QA report binding does not match prepared evidence")
    report = _document_snapshot(record.qa_report)
    validate_document("qa_report", report, expected_job_id=job_id)
    state = record.state
    bundle = EvidenceBundle(WORKDIR, job_id)
    failed_required = any(
        assertion["required"] and not assertion["passed"]
        for assertion in report["assertions"]
    )

    if report["final_grade"] != "L2" or failed_required:
        if state.value == "validating":
            state.transition("failed_qa")
        elif state.value != "failed_qa":
            raise ValueError(f"failed QA cannot finalize from state: {state.value}")
        failed_path = bundle.checkpoint_path("failed")
        bridge.call(
            "precision_save_checkpoint",
            {"job_id": job_id, "filepath": str(failed_path)},
        )
        if failed_path.is_file():
            _replace_artifact(report, bundle, failed_path)
        validate_document("qa_report", report, expected_job_id=job_id)
        bundle.write_contract("qa_report", report)
        record.qa_report = _document_snapshot(report)
        record.qa_report_digest = _document_digest(record.qa_report)
        return _json(report)

    if state.value != "validating":
        raise ValueError(f"passing QA cannot finalize from state: {state.value}")
    preview_paths = [
        ("orthographic", bundle.preview_path("orthographic")),
        ("perspective", bundle.preview_path("perspective")),
    ]
    for view, path in preview_paths:
        bridge.call(
            "precision_render_white_model",
            {
                "job_id": job_id,
                "filepath": str(path),
                "view": view,
                "resolution_x": 640,
                "resolution_y": 360,
            },
        )
    final_path = bundle.checkpoint_path("final")
    bridge.call(
        "precision_save_checkpoint",
        {"job_id": job_id, "filepath": str(final_path)},
    )
    for _, path in preview_paths:
        if not path.is_file():
            raise FileNotFoundError(f"preview was not created: {path}")
        _replace_artifact(report, bundle, path)
    if not final_path.is_file():
        raise FileNotFoundError(f"checkpoint was not created: {final_path}")
    _replace_artifact(report, bundle, final_path)
    validate_document("qa_report", report, expected_job_id=job_id)
    bundle.write_contract("qa_report", report)
    bridge.call(
        "precision_commit_job",
        {"job_id": job_id, "filepath": str(final_path)},
    )
    state.transition("committed")
    record.qa_report = _document_snapshot(report)
    record.qa_report_digest = _document_digest(record.qa_report)
    return _json(report)


def _safe_path(filepath: str) -> str:
    path = Path(filepath).expanduser().resolve()
    resolved_workdir = WORKDIR.resolve()
    if path != resolved_workdir and resolved_workdir not in path.parents:
        raise ValueError(
            f"path must be inside PRECISION_WORKDIR: {resolved_workdir}"
        )
    return str(path)


@mcp.tool()
def precision_begin(prefix: str = "PRECISION_", clean_existing: bool = False) -> str:
    """Start a transaction; existing objects are preserved unless clean_existing is explicitly true."""
    return _call("precision_begin", {"prefix": prefix, "clean_existing": clean_existing})


@mcp.tool()
def precision_create_mesh(name: str, vertices: list[list[float]], faces: list[list[int]], dimensions: list[float] | None = None, prefix: str = "PRECISION_") -> str:
    """Create a mesh from explicit vertices/faces, optionally normalized to exact XYZ dimensions."""
    return _call("precision_create_mesh", {"name": name, "vertices": vertices, "faces": faces, "dimensions": dimensions, "prefix": prefix})


@mcp.tool()
def precision_create_primitive(name: str, primitive: str, dimensions: list[float], location: list[float] | None = None, metadata: dict[str, Any] | None = None) -> str:
    """Create a named cube, cylinder, cone, UV sphere or plane with exact dimensions."""
    return _call("precision_create_primitive", {"name": name, "primitive": primitive, "dimensions": dimensions, "location": location, "metadata": metadata or {}})


@mcp.tool()
def precision_cad_status() -> str:
    """Report whether CAD Sketcher and its solver are available in the connected Blender session."""
    return _call("precision_cad_status")


@mcp.tool()
def precision_create_cad_rectangle(name: str, width: float, height: float) -> str:
    """Create and solve a CAD Sketcher rectangle with fixed origin and dimensional constraints."""
    return _call("precision_create_cad_rectangle", {"name": name, "width": width, "height": height})


@mcp.tool()
def precision_build_model_spec(spec: dict[str, Any]) -> str:
    """Build a repeatable named asset from a validated model_spec parts list."""
    return _call("precision_build_model_spec", {"spec": spec})


@mcp.tool()
def precision_set_dimensions(name: str, dimensions: list[float], apply_scale: bool = True) -> str:
    """Set exact world dimensions and optionally apply scale."""
    return _call("precision_set_dimensions", {"name": name, "dimensions": dimensions, "apply_scale": apply_scale})


@mcp.tool()
def precision_inspect_geometry(name: str | None = None) -> str:
    """Return measurable geometry QA for one object or all precision objects."""
    return _call("precision_inspect_geometry", {"name": name})


@mcp.tool()
def precision_validate_scene(tolerance: float = 0.01, require_ground_contact: bool = True) -> str:
    """Run compatibility-only V1 relative QA; this path cannot issue V2 L2."""
    return _call("precision_validate_scene", {"tolerance": tolerance, "require_ground_contact": require_ground_contact})


@mcp.tool()
def precision_frame_camera(name: str, target_fill: float = 0.72, lens_mm: float = 50.0) -> str:
    """Frame a camera from the object world bounding box at a target occupancy."""
    return _call("precision_frame_camera", {"name": name, "target_fill": target_fill, "lens_mm": lens_mm})


@mcp.tool()
def precision_render_white_model(filepath: str, resolution_x: int = 640, resolution_y: int = 360) -> str:
    """Render a neutral Workbench white-model preview to an explicit path."""
    return _call("precision_render_white_model", {"filepath": _safe_path(filepath), "resolution_x": resolution_x, "resolution_y": resolution_y})


@mcp.tool()
def precision_save_checkpoint(filepath: str) -> str:
    """Save a Blender checkpoint inside PRECISION_WORKDIR before destructive edits."""
    return _call("precision_save_checkpoint", {"filepath": _safe_path(filepath)})


@mcp.tool()
def precision_commit() -> str:
    """Commit the current modeling transaction."""
    return _call("precision_commit")


@mcp.tool()
def precision_abort() -> str:
    """Stop the current modeling transaction; restore from the Skill checkpoint if needed."""
    return _call("precision_abort")


if __name__ == "__main__":
    mcp.run()
