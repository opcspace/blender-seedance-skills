# Commercial use and Precision Core V2 delivery policy

The OPCspace Skills and `precision-mcp` source are released under the repository MIT License. Commercial users may run, modify, integrate, and redistribute this code while preserving the copyright notice and license text. That license does not grant rights to reference images, scans, trademarks, likenesses, downloaded models, Blender, CAD Sketcher, Jimeng/Dreamina/Seedance, Volcengine services, or other third-party assets and runtimes.

## Precision claims

Only the validated V2 `qa_report.json` may assign a grade:

- **L0 — unverified/blockout:** the reference is uncalibrated, required evidence is missing, any L1 gate is absent or failed, or the result is visual-only.
- **L1 — measured structured white model:** the global envelope gate, every primary-dimension gate, every contact gate, and every anchor gate are present and pass their declared absolute tolerances.
- **L2 — evidence-complete precision model:** all L1 gates and all required assertions pass; geometry, checkpoint, and provenance gates pass; there are no unresolved assumptions; and the finalized evidence is complete.

Appearance, primitive count, an image-only reconstruction, a Tripo visual shell, multiple uncalibrated views, or a portable unit-test result cannot raise the grade. A blocked or unexecuted Blender GUI acceptance cannot support L2. Do not describe such work as “CAD-level,” “watertight,” or “production topology.” CAD claims additionally require an actual CAD Sketcher runtime/solver report; the adapter never assumes availability.

## Minimum handoff evidence

An L2 commercial handoff must include:

1. The canonical `scene_spec.json`, `asset_manifest.json`, and `operation_plan.json` with matching `job_id`.
2. The final validated `qa_report.json`, including every assertion, downgrade reason, assumption, final grade, and artifact record.
3. A committed editable `.blend` whose SHA-256 matches the artifact entry in `qa_report.json`.
4. The `before.blend` and final checkpoint, plus orthographic and perspective previews with matching recorded checksums where listed.
5. `assumptions.md`, provenance, calibration source, absolute tolerances, and a third-party asset/license inventory.

If a required assertion fails, the workflow may preserve `failed.blend` for diagnosis, but it must not present that file as a committed L2 result. If GUI evidence is blocked, report the blocker alongside portable results rather than substituting one for the other.

## Third-party boundaries

- CAD Sketcher is an external GPL-3.0-or-later dependency and is not vendored here.
- Blender and bundled components retain their own licenses.
- Jimeng/Dreamina/Seedance, Volcengine APIs, accounts, uploads, and generated outputs retain their provider terms.
- Reference and imported GLB/FBX assets require independent provenance and redistribution review.

The repository license does not relicense or certify any of those dependencies or assets.
