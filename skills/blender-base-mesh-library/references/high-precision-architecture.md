# Codex + Blender MCP high-precision modeling architecture

## 1. Core principle

Codex should not improvise Blender operations one primitive at a time. It first produces a structured `model_spec` with units, target dimensions, anchors, parts, construction operations, camera intent and QA thresholds. Blender MCP then executes that spec deterministically and returns measurements. Codex compares the measurements against the spec and applies targeted patches.

The current restricted MCP list is a blockout adapter, not a high-precision mesh adapter. It can create primitives, transform objects, add modifiers, set cameras/lights, render and keyframe, but it cannot create arbitrary vertices/faces, apply scale, edit topology, import reference images, write custom properties, create collections, or save the active file. High precision therefore requires a safe typed extension layer.

## 2. Two modeling entrances

### Prompt entrance

1. Parse the brief into `model_spec`.
2. Select a category template and scale policy.
3. Build a low-detail silhouette.
4. Measure the result and normalize dimensions/contact points.
5. Add construction detail: symmetry, mirror, arrays, booleans, curves, bevels and controlled topology.
6. Run QA and render a white-model checkpoint.

### Reference-image entrance

1. Inspect the image and record observed geometry separately from inferred hidden geometry.
2. Import the image into `CODEX_Reference` or keep an explicit external reference path.
3. Calibrate one known dimension or camera cue; never infer absolute scale from pixels alone.
4. Extract landmarks, silhouette contour, symmetry axis and part boundaries.
5. Build the editable model from those constraints, not by blindly copying pixels.
6. Render the same camera and compare silhouette/landmarks; patch the largest mismatch first.

## 3. Required precision tool layer

Implement these as typed, allow-listed MCP tools or a companion Blender add-on. Do not enable unrestricted `execute_python` for normal workflows.

- `scene.begin_transaction` / `scene.rollback_transaction`
- `collection.ensure` / `collection.move_objects`
- `mesh.create_from_vertices_faces`
- `mesh.inspect` (bounds, vertex/face counts, non-manifold edges, normals)
- `object.set_dimensions` and `object.apply_scale`
- `modifier.add/configure/apply` for Mirror, Array, Boolean, Bevel, Solidify and Subdivision
- `mesh.symmetrize`, `mesh.boolean`, `mesh.merge_by_distance`
- `reference.import_image` and `reference.set_camera_plane`
- `metadata.set_properties`
- `camera.frame_bounds`
- `scene.save_checkpoint`

Each tool should validate arguments, operate only on named objects, return before/after measurements, and reject paths outside an approved workspace.

## 4. Seven category templates

- **Character**: landmarks for head, shoulders, pelvis, elbows, knees and feet; mirror first; separate proportions from pose; rig only after the neutral base passes.
- **Creature**: spine chain, head direction, contact limbs, tail/wing anchors and mass-to-limb ratios; verify feet/hooves/claws touch the ground.
- **Props**: functional dimensions, assembly hierarchy, primary/secondary silhouette, rotation axis and contact surface; no texture until geometry passes.
- **Architecture**: metric grid, module dimensions, openings, floor heights, repeated elements and camera scale cue.
- **Hard surface**: shell volumes, panel boundaries, functional gaps, wheel/hinge/landing contacts, symmetry and bevel width relative to part size.
- **Environment**: terrain envelope, dominant mass, scatter rules, path/camera route and scale references such as a character or doorway.
- **Abstract**: profile/symmetry/negative-space parameters, controlled primitive overlap and at least two camera angles for sculptability.

## 5. Acceptance gates

- Explicit dimensions: within ±2% after normalization.
- Symmetric parts: mirrored within the chosen tolerance.
- Ground/contact objects: lowest support at Z=0 within tolerance.
- Camera: full silhouette visible, 55–85% frame occupancy, no accidental crop.
- Structure: meaningful names, stable root, no unexplained default objects.
- Geometry: no unverified claim of rig-ready, watertight or production topology.
- Delivery: checkpoint path, preview image, spec, measurements and unresolved issues are all reported.

## 6. Quality levels

- **L0**: primitive blockout and composition.
- **L1**: structured white model with measured proportions, parts, modifiers and camera QA.
- **L2**: high-precision editable BaseMesh with arbitrary mesh construction, topology inspection, reference comparison and checkpoint save.

The existing MCP workflow currently reaches L0 reliably and parts of L1. It should not claim L2 until the precision tool layer is installed and the acceptance gates pass.

