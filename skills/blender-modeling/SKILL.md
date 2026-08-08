---
name: blender-modeling
description: Build and edit editable Blender scenes from natural-language prompts or uploaded AI reference images using Blender MCP. Use for prompt-driven modeling, reference reconstruction, scene blockouts, proportions, modifiers, materials, cameras, animation, and targeted model revisions. Route BaseMesh category requests to blender-base-mesh-library and white-model/video export requests to the specialized rendering or Seedance skills.
---

# Blender Modeling

This Skill owns the editable 3D scene. It turns a brief or reference image into named Blender objects, collections, modifiers, materials, cameras and keyframes. It does not own final white-model video delivery.

## Choose the modeling mode

- **Prompt mode**: no image is supplied. Convert the request into subject, scale, silhouette, construction strategy, camera, animation and constraints, then build in passes.
- **Reference mode**: an AI image, sketch, screenshot or board is supplied. Inspect it first; separate observed geometry from inferred hidden geometry; keep the source in `CODEX_Reference`; build the editable approximation in `CODEX_Model`; apply later user changes as patches.
- **Library mode**: the user names a BaseMesh category, asset type or search keyword. Read `blender-base-mesh-library` and select the right white-model family before modeling.

## Workflow

1. Check local prerequisites with the canonical environment checker in `blender-seedance-modeling`.
2. Inspect the current Blender scene with Blender MCP. If MCP is unavailable, state that exact blocker and use the local Blender executable only when authorized.
3. Save a checkpoint before destructive changes when a save tool or Blender GUI is available. If the connected MCP tool set has no save operation, do not claim a checkpoint was written; preserve the scene by using targeted edits and report the limitation.
4. Use the `CODEX_Model`, `CODEX_Reference`, `CODEX_Stage` and `CODEX_Exports` names as a convention. If collection-management tools are unavailable, use object prefixes and report that all objects remain in the current collection.
5. Build in this order: silhouette/blockout → proportion check → construction/modifiers → materials → camera/stage → animation.
6. After each pass, inspect object names, transforms, active camera and frame range through MCP.
7. Apply modifications as targeted patches. Preserve named objects and the camera unless the user asks to rebuild.

## Prompt contract

```text
subject: what to build
scale: real-world or relative dimensions
silhouette: primary masses and proportions
construction: primitives, modifiers, curves, Geometry Nodes, or armature
reference: observed facts and inferred parts
camera: shot, lens, angle and movement
animation: poses, actions and timing
constraints: must preserve / must avoid
deliverable: editable .blend or handoff to another Skill
```

## Quality gates

- Use meaningful names; do not leave important objects as `Cube.001`.
- Apply scale before bevels and dimension-sensitive modifiers.
- Keep the subject near the origin and use metric units when dimensions matter.
- Fix silhouette and camera errors before micro-detail.
- Mark inferred geometry with custom properties such as `reference_confidence`.
- Keep unrestricted code execution disabled in Blender MCP.

## Current MCP capability boundary

The validated Blender MCP 1.29 tool set can create, transform, duplicate, delete, inspect, material-assign, add modifiers, set cameras/lights, render stills, and keyframe animation. It does not currently expose collection creation/movement, custom-property editing, saving the active `.blend`, image upload, or Jimeng submission. Treat those as manual GUI or explicitly authorized fallback steps rather than silently claiming automation.

On Blender 5.2 with a Chinese UI, the material node is localized to `原理化 BSDF`. The MCP material helpers that look up the literal English node name may fail. Prefer Workbench for white models; if a shader is necessary, call `list_shader_nodes` and then `set_node_value` using the returned node name and socket name.

## Handoff

When the user asks for white-model rendering, call `blender-white-model-render`. When the user asks for Seedance/即梦 output, call `seedance-white-model-video`. Report the checkpoint path and the exact handoff artifact.
