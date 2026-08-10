# Reference Calibration

Calibrate before creating a precision plan. Keep measured observations separate from inferences throughout the contracts and evidence.

## Accepted calibration sources

Accept at least one known dimension or explicit real-world scale together with one of:

- a dimensional drawing with labeled dimensions and units;
- calibrated camera parameters and a resolvable scale reference;
- camera-matching data with sensor size, focal length, image resolution, pose/extrinsics, and a known scene dimension;
- a scan, survey, CAD file, or measured source geometry whose units and provenance are verified.

Record the source as an AssetManifest `calibration` or `dimensional_drawing` asset, including checksum, units, provenance, uncertainty, `assumptions`, and `reasons`.

## Observed versus inferred

Put directly visible/measured facts in `observed`. Put occluded geometry, guessed lens/pose, assumed symmetry, estimated thickness, or derived dimensions in `inferred` and repeat unresolved items in `assumptions`. Inferred values cannot satisfy a required calibration or L2 measurement.

Label every image with a stable `view_id` and a view label such as `front`, `rear`, `left`, `right`, `top`, `bottom`, `perspective`, or `detail`. Label camera data as `calibrated`, `estimated`, or `unknown`; only `calibrated` camera data counts toward a precision gate.

## Grade boundary

An uncalibrated single image is unequivocally L0. Multiple images improve visual reconstruction but do not raise the grade unless their camera relationships and scale are calibrated or they are backed by a dimensional drawing. Orthographic-looking, AI-generated, cropped, or perspective-corrected images are not calibrated merely by appearance.

## Request missing input

State the current grade as L0 and ask specifically for:

1. one authoritative dimension and its unit;
2. a dimensional drawing, calibrated camera data, or verified CAD/scan source;
3. view labels and which surfaces/features correspond across views;
4. tolerances for fit-critical dimensions, contacts, anchors, clearances, and interfaces;
5. provenance and permission for imported or generated assets.

Do not invent camera values, scale, hidden dimensions, or an improvised precision workflow while waiting.
