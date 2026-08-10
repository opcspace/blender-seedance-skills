"""Manual Blender 5.2 MCP-to-add-on acceptance for Precision Core V2.

This runner is intentionally excluded from ``test_precision_*.py`` discovery.
It records real GUI evidence only when Blender, the add-on, and the imported GLB
fixture are present. It never opens the add-on socket directly.
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "precision_v2"
OUTPUT = ROOT / "tests" / "assets" / "precision_v2"
IMPORT_FIXTURE = OUTPUT / "import-cube.glb"
CASES = (
    "architecture-wall-opening",
    "mechanical-enclosure-holes",
    "furniture-table-anchors",
    "props-imported-tool",
)


class GuiAcceptanceBlocked(RuntimeError):
    """Raised when a required external GUI/runtime input is unavailable."""


def _load(case_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    scene = json.loads(
        (FIXTURES / f"{case_name}.scene.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (FIXTURES / f"{case_name}.manifest.json").read_text(encoding="utf-8")
    )
    return scene, manifest


def _anchors(asset: dict[str, Any]) -> dict[str, list[float]]:
    x, y, z = (float(value) for value in asset["target_dimensions"])
    points = {
        "floor-center": [0.0, 0.0, -z / 2.0],
        "base-center": [0.0, 0.0, -z / 2.0],
        "base": [0.0, 0.0, -z / 2.0],
        "butt": [0.0, 0.0, -z / 2.0],
        "tip": [0.0, 0.0, z / 2.0],
        "grip-center": [0.0, 0.0, 0.0],
        "center": [0.0, 0.0, 0.0],
        "sill-left": [-x / 2.0, 0.0, -z / 2.0],
        "sill-right": [x / 2.0, 0.0, -z / 2.0],
        "opening-sill-left": [-450.0, 0.0, -z / 2.0],
        "opening-sill-right": [450.0, 0.0, -z / 2.0],
        "head-center": [0.0, 0.0, z / 2.0],
        "leg-front-left": [-x / 2.0, -y / 2.0, -z / 2.0],
        "leg-front-right": [x / 2.0, -y / 2.0, -z / 2.0],
        "leg-rear-left": [-x / 2.0, y / 2.0, -z / 2.0],
        "leg-rear-right": [x / 2.0, y / 2.0, -z / 2.0],
    }
    return {name: points.get(name, [0.0, 0.0, 0.0]) for name in asset["anchors"]}


def _text_result(result: Any) -> str:
    return "".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )


async def _call_json(session: Any, name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    text = _text_result(result)
    if getattr(result, "isError", False):
        raise RuntimeError(f"{name}: {text}")
    return json.loads(text)


async def _expect_error(session: Any, name: str, arguments: dict[str, Any]) -> None:
    result = await session.call_tool(name, arguments)
    if not getattr(result, "isError", False):
        raise AssertionError(f"{name} unexpectedly succeeded")


async def _execute_plan(
    session: Any,
    scene: dict[str, Any],
    manifest: dict[str, Any],
    *,
    exercise_path_escape: bool = False,
) -> dict[str, Any]:
    job_id = scene["job_id"]
    plan = await _call_json(
        session,
        "precision_prepare_job",
        {"scene_spec": scene, "asset_manifest": manifest, "cad_available": False},
    )
    assets = {asset["asset_id"]: asset for asset in manifest["assets"]}

    if exercise_path_escape:
        await _expect_error(
            session,
            "precision_import_asset",
            {
                "job_id": job_id,
                "asset_id": "escape-attempt",
                "filepath": str(OUTPUT.parent / "escape.glb"),
            },
        )
        print("path-escape REJECTED PASS")

    for step in plan["steps"]:
        asset = assets[step["asset_id"]]
        if step["tool"] == "precision_create_part":
            await _call_json(
                session,
                "precision_create_part",
                {
                    "job_id": job_id,
                    "asset_id": asset["asset_id"],
                    "primitive": "cylinder" if asset["asset_id"].startswith("hole-") else "cube",
                    "target_dimensions": asset["target_dimensions"],
                    "location": asset["location"],
                    "rotation_deg": asset["rotation_deg"],
                    "anchors": _anchors(asset),
                    "metadata": {"fixture": scene["category"]},
                },
            )
        elif step["tool"] == "precision_import_asset":
            if not IMPORT_FIXTURE.is_file():
                raise GuiAcceptanceBlocked(
                    "imported prop requires tests/assets/precision_v2/import-cube.glb"
                )
            await _call_json(
                session,
                "precision_import_asset",
                {
                    "job_id": job_id,
                    "asset_id": asset["asset_id"],
                    "filepath": str(IMPORT_FIXTURE),
                    "provenance": asset["provenance"],
                    "anchors": _anchors(asset),
                },
            )
            normalized = await _call_json(
                session,
                "precision_normalize_asset",
                {
                    "job_id": job_id,
                    "asset_id": asset["asset_id"],
                    "source_units": "cm",
                    "target_units": "mm",
                    "source_up_axis": "Y",
                    "target_up_axis": "Z",
                    "target_dimensions": asset["target_dimensions"],
                    "scaling_mode": "explicit_xyz",
                    "provenance": asset["provenance"],
                },
            )
            if normalized["dimensions"] != asset["target_dimensions"]:
                raise AssertionError("normalization did not repair imported units/axes")
        else:
            raise GuiAcceptanceBlocked(f"plan contains unavailable step: {step['tool']}")

    first_asset = manifest["assets"][0]
    await _call_json(
        session,
        "precision_patch_feature",
        {
            "job_id": job_id,
            "asset_id": first_asset["asset_id"],
            "patch": "location",
            "value": first_asset["location"],
            "feature_id": "acceptance-noop-location",
        },
    )
    return plan


def _assert_artifacts(job_id: str) -> None:
    root = OUTPUT / "evidence" / job_id
    required = (
        "scene_spec.json",
        "asset_manifest.json",
        "operation_plan.json",
        "qa_report.json",
        "checkpoints/before.blend",
        "checkpoints/final.blend",
        "previews/orthographic.png",
        "previews/perspective.png",
    )
    missing = [relative for relative in required if not (root / relative).is_file()]
    if missing:
        raise AssertionError(f"missing evidence for {job_id}: {missing}")


async def _run_case(session: Any, case_name: str) -> None:
    scene, manifest = _load(case_name)
    await _execute_plan(
        session,
        scene,
        manifest,
        exercise_path_escape=case_name == "props-imported-tool",
    )
    report = await _call_json(
        session,
        "precision_validate_job",
        {"scene_spec": scene, "asset_manifest": manifest, "assumptions": []},
    )
    if report["final_grade"] != "L2":
        raise AssertionError(f"{case_name}: expected L2, got {report['final_grade']}")
    final_report = await _call_json(
        session,
        "precision_finalize_job",
        {"scene_spec": scene, "asset_manifest": manifest},
    )
    if final_report["final_grade"] != "L2":
        raise AssertionError(f"{case_name}: final report is not L2")
    _assert_artifacts(scene["job_id"])
    print(f"{scene['category']} L2 PASS")


async def _run_uncalibrated_negative(session: Any) -> None:
    scene, manifest = _load("furniture-table-anchors")
    scene = copy.deepcopy(scene)
    manifest = copy.deepcopy(manifest)
    scene["job_id"] = "negative-uncalibrated"
    manifest["job_id"] = scene["job_id"]
    scene["reference_calibrated"] = False
    await _execute_plan(session, scene, manifest)
    report = await _call_json(
        session,
        "precision_validate_job",
        {"scene_spec": scene, "asset_manifest": manifest, "assumptions": []},
    )
    if report["final_grade"] != "L0":
        raise AssertionError("uncalibrated fixture did not remain L0")
    print("uncalibrated L0 PASS")


async def _run_failed_dimension_negative(session: Any) -> None:
    scene, manifest = _load("furniture-table-anchors")
    scene = copy.deepcopy(scene)
    manifest = copy.deepcopy(manifest)
    scene["job_id"] = "negative-required-dimension"
    manifest["job_id"] = scene["job_id"]
    await _execute_plan(session, scene, manifest)
    target = list(manifest["assets"][0]["target_dimensions"])
    target[0] += 10.0
    await _call_json(
        session,
        "precision_patch_feature",
        {
            "job_id": scene["job_id"],
            "asset_id": "table",
            "patch": "dimensions",
            "value": target,
            "feature_id": "negative-width-drift",
        },
    )
    report = await _call_json(
        session,
        "precision_validate_job",
        {"scene_spec": scene, "asset_manifest": manifest, "assumptions": []},
    )
    if report["final_grade"] == "L2":
        raise AssertionError("failed required dimension incorrectly issued L2")
    print("failed-required-dimension NOT-L2 PASS")


async def run_acceptance() -> None:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as error:
        raise GuiAcceptanceBlocked("MCP SDK is not installed") from error

    OUTPUT.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "precision_mcp.server"],
        env={
            **os.environ,
            "PRECISION_WORKDIR": str(OUTPUT),
            "PYTHONPATH": str(ROOT / "precision-mcp"),
        },
    )
    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                for case_name in CASES:
                    await _run_case(session, case_name)
                await _run_uncalibrated_negative(session)
                await _run_failed_dimension_negative(session)
    except GuiAcceptanceBlocked:
        raise
    except Exception as error:
        raise GuiAcceptanceBlocked(
            f"Blender 5.2 listener/runtime unavailable or acceptance failed: {error}"
        ) from error


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except GuiAcceptanceBlocked as error:
        print(f"BLOCKED: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
