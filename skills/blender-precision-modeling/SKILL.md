---
name: blender-precision-modeling
description: Build, import, assemble, patch, measure, validate, and deliver dimension-driven Blender white models through Precision Core V2. Use for calibrated prompt/reference modeling, architecture, mechanical assets, furniture, props, GLB/FBX normalization, absolute tolerances, CAD-constrained profiles, commercial evidence bundles, or any request claiming high precision.
---

# Blender Precision Modeling

Treat Precision Core V2 contracts, measurements, assertions, and evidence as the only authority for a precision grade. Read [references/precision-contract.md](references/precision-contract.md) before every job. For image-derived work, also read [references/reference-calibration.md](references/reference-calibration.md).

## Mandatory workflow

1. **Calibrate input.** Record known dimensions, units, scale, camera/view calibration, and observed versus inferred facts. Carry unresolved inferences into QA `assumptions` and missing-input explanations into QA `reasons`. Missing a known dimension or scale and either a calibrated camera or dimensional drawing means **L0 only**. A single view or multiple uncalibrated views never raises the grade.
2. **Write contracts.** Create the V2 `SceneSpec` and `AssetManifest`, then the deterministic typed operation plan. Declare every required measurement and absolute tolerance before geometry work.
3. **Prepare.** Call `precision_prepare_job` with runtime `cad_available`. Stop on contract, asset, or capability errors. If a `cad_sketcher` asset plans a `backend_unavailable` step, stop; never silently fall back. Tripo is optional only as an AssetManifest `visual_shell` source and cannot issue or upgrade precision.
4. **Execute typed operations.** Execute only the validated operation plan through Precision Core V2 operations. Never use raw code execution. Preserve operation IDs, parameters, checkpoints, and provenance.
5. **Inspect and patch.** Call `precision_inspect_job`; resolve failures with named, typed patches, then inspect again. Use absolute tolerances for every fit-critical envelope, primary dimension, contact, anchor, clearance, alignment, and interface check.
6. **Validate.** Call `precision_validate_job`. L1 requires a passing global envelope, every primary dimension, every contact check, and every anchor check. L2 requires every required measurement plus geometry, checkpoint, and provenance checks, no unresolved assumptions, and complete evidence. Any failed required assertion prevents commit and L2.
7. **Finalize.** Call `precision_finalize_job` only after `qa_report.json` records L2 with no failed required assertion. Deliver the four canonical JSON files, `assumptions.md`, committed model, checkpoints, assertions, provenance, artifact hashes, and rendered evidence listed in the contract. Lower grades remain uncommitted.

Seedance is a downstream preview only. It cannot validate geometry, replace Blender evidence, or add a precision grade.

## Grade boundary

- **L0:** uncalibrated, incomplete, assumed, visual-only, or failed-gate work.
- **L1:** all required L1 gates pass with evidence.
- **L2:** the complete L2 contract passes with no failed required assertion or unresolved assumption.

Do not improvise alternate “precision gates,” infer a higher grade from appearance, or issue a grade outside the V2 final report.
