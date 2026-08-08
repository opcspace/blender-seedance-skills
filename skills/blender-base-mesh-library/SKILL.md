---
name: blender-base-mesh-library
description: Select, design, generate, and organize reusable Blender BaseMesh white-model assets. Use when the user asks for a white-model category, reusable modeling library, asset search keywords, base meshes, modular scene parts, rigged body bases, or a catalog of Blender primitives and blockouts.
---

# Blender BaseMesh Library

This Skill defines the reusable white-model vocabulary. It selects the asset family, creates a clean editable BaseMesh through Blender MCP, and records metadata so the asset can be reused by the modeling and rendering Skills.

## Seven categories

Read `references/base-mesh-catalog.md` for the full catalog and search terms.

1. **Character**: realistic male/female/child/elder bodies, stylized/Q-version bodies, head/hands/feet/facial parts, hair/clothing/armor bases, rig-ready mannequins.
2. **Creature**: mammals, birds, fish, reptiles, dragons, beastfolk, monsters, merfolk, elves, claws, wings and horns.
3. **Props and still life**: furniture, utensils, tools, weapons, shields, instruments, ornaments and small objects.
4. **Architecture**: columns, doors, windows, stairs, carved parts, traditional houses, modern buildings, sci-fi buildings, walls and city modules.
5. **Hard-surface and machines**: cars, spacecraft, mechs, robots, industrial parts, equipment shells and mechanical housings.
6. **Environment and terrain**: mountains, rocks, cliffs, stones, ground modules, trunks, branches and vegetation bases.
7. **Abstract forms**: spheres, cubes, rings, cylinders, sculptures, organic blobs and irregular surfaces for later sculpting.

## BaseMesh contract

For the high-precision plan, read `references/high-precision-architecture.md`. The current restricted MCP path is reliable for L0 blockout and partial L1 structured white models; do not label a primitive-only result as L2 high-precision BaseMesh.

Every generated library asset should have:

- a named collection `BASE_<category>_<asset>`;
- a root object named `BASE_<asset>_ROOT`;
- clean transforms and sensible origin;
- white or neutral material only, with no baked texture unless explicitly requested;
- simple, editable topology appropriate to the asset's purpose;
- custom properties: `base_mesh_category`, `base_mesh_purpose`, `reference_confidence`, `rig_ready`, `source_prompt`;
- a preview camera or a thumbnail render when the asset is intended for visual browsing.

If the connected MCP tool set cannot create collections or custom properties, preserve the contract as naming and a report: use the `BASE_<category>_<asset>` and `BASE_<asset>_ROOT` prefixes, keep the asset isolated by object names, and return the metadata fields in the handoff text. Do not claim that Blender custom properties or a library `.blend` checkpoint were written unless those capabilities are available.

## Selection workflow

1. Extract category, subcategory, style, scale, rig requirement and intended camera distance.
2. Search `references/base-mesh-catalog.md` using category terms and Chinese/English synonyms.
3. Prefer an existing compatible BaseMesh and modify it. Create a new one only when no asset fits.
4. Build the lowest useful detail level first; add detail only if it affects the silhouette or intended shot.
5. Normalize scale against `references/scale-policy.md`: measure the generated bounds, scale the root to the target envelope, move the lowest contact point to Z=0, then recalculate the camera from the measured bounding box.
6. Validate naming, transforms, material neutrality, topology and collection isolation.
7. Hand the result to `blender-modeling` for scene-specific edits or `blender-white-model-render` for export.

Never use a fixed camera distance for all categories. A primitive's `scale` is not its final dimensions; query `get_object_info.dimensions` after creation and normalize from measured bounds.

## Category-specific minimum recipes

Use these checks before calling a BaseMesh usable. They are intentionally silhouette-first and work with primitive-only MCP tools.

- **Character**: head, torso, two legs, two arms and a ground/contact plane. Keep the head-to-body ratio explicit; use spheres/cylinders for joints and limbs where possible, and do not accept a featureless rectangular torso as a realistic base. Q-style bodies may exaggerate the head but must keep the feet and shoulder direction readable.
- **Creature**: define a spine/body mass, head direction, four or two contact limbs, tail or wing attachment and a clear ground relationship. Wings must be thin, broad and angled rather than box-like; horns, claws and tails must visibly attach to a parent mass.
- **Props and still life**: model the functional silhouette first. Rotate blades, shields, handles and cylinders to their intended use direction; check that the camera shows the primary face and at least one depth cue. Keep materials neutral and omit textures.
- **Architecture**: establish a ground/foundation, primary enclosure, repeated modules and an entry/opening or circulation cue. Check alignment, scale consistency and an establishing camera before decorative parts.
- **Hard surface and machines**: separate the main shell, functional subassemblies and contact points (wheels, feet, landing gear). Apply bevels after scale is set; keep panel masses simple and avoid pretending that an unverified cube is a complete vehicle shell.
- **Environment and terrain**: include a ground context, one dominant mass and secondary variation. Frame the full height and footprint; do not let a canopy, cliff or mountain be cropped out of the preview.
- **Abstract forms**: use three to five intentional masses with controlled overlap, negative space and a chosen focal axis. Test a second camera angle when the form is meant for later sculpting.

## Quality and fallback rules

- Run a silhouette pass, a proportion/contact pass and a camera/framing pass in that order. A render that technically succeeds but crops the object or merges all masses is a failed BaseMesh preview.
- Keep parent/root naming and object-level metadata in the handoff report when collections or custom properties are unavailable in MCP.
- Rigged bodies, real retopology, sculpt topology, UVs, image-reference import and custom properties require additional Blender tools or a manual GUI step. Do not claim `rig_ready=true` from primitive parenting alone.
- For a category with weak results, preserve the object names and apply a targeted patch: proportions, appendage direction, contact points, camera distance or module spacing. Rebuild only when the silhouette cannot be repaired.

## Important boundary

This Skill creates or selects the editable white model. It does not promise pixel-perfect recovery of hidden geometry from one AI image, and it does not create final Seedance video.
