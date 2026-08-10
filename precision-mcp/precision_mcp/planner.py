"""Deterministic routing from asset manifests to backend operations."""

from __future__ import annotations

from typing import Any

from precision_mcp.contracts import validate_document


def _tool_for(source: str, cad_available: bool) -> str:
    if source == "tripo":
        return "external_pending"
    if source == "cad_sketcher":
        return "precision_create_cad_part" if cad_available else "backend_unavailable"
    if source in {"imported", "user"}:
        return "precision_import_asset"
    return "precision_create_part"


def build_plan(
    scene_spec: dict[str, Any],
    manifest: dict[str, Any],
    cad_available: bool,
) -> dict[str, Any]:
    """Build a stable, schema-valid operation plan for one precision job."""
    job_id = scene_spec["job_id"]
    if manifest["job_id"] != job_id:
        raise ValueError("job_id mismatch")

    steps = []
    for index, asset in enumerate(
        sorted(manifest["assets"], key=lambda item: item["asset_id"]), start=1
    ):
        asset_id = asset["asset_id"]
        steps.append(
            {
                "operation_id": f"{index:03d}-{asset_id}",
                "tool": _tool_for(asset["source"], cad_available),
                "asset_id": asset_id,
                "params": dict(asset),
                "preconditions": {},
                "expected": {"asset_id": asset_id},
                "rollback": {"action": "remove_job_asset"},
                "depends_on": [],
            }
        )

    plan = {"spec_version": "2.0", "job_id": job_id, "steps": steps}
    return validate_document("operation_plan", plan, expected_job_id=job_id)
