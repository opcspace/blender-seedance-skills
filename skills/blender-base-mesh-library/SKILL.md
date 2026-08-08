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
5. Validate naming, transforms, material neutrality, topology and collection isolation.
6. Hand the result to `blender-modeling` for scene-specific edits or `blender-white-model-render` for export.

## Important boundary

This Skill creates or selects the editable white model. It does not promise pixel-perfect recovery of hidden geometry from one AI image, and it does not create final Seedance video.
