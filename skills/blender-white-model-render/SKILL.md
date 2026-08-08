---
name: blender-white-model-render
description: Turn an editable Blender scene or BaseMesh into a clean white-model still, turntable, storyboard or H.264 preview video. Use Blender Workbench/material preview, camera and timeline settings, and the installed jimeng_blender_uploader add-on for 即梦 handoff.
---

# Blender White-Model Render

This Skill owns neutral white-model presentation and preview export. It does not build the model's detailed geometry and does not claim that Jimeng has completed final Seedance generation.

## Render modes

- **Still**: one clean white-model camera frame for reference upload.
- **Turntable**: 360-degree rotation around an empty/root object.
- **Storyboard**: one active camera with deliberate keyframes or shot cameras.
- **Existing video**: pass an already rendered MP4/MOV/WEBM/AVI to the Jimeng uploader.

## Workflow

1. Inspect the scene and save a checkpoint.
2. Select the model collection and active camera. Hide construction helpers unless they affect the shot.
3. Use a neutral white/gray material, Workbench or material preview, simple ground and readable lighting. Do not add final textures unless requested.
4. Set 24 fps, a valid frame range, 16:9 unless the user chooses another ratio, and a preview resolution. Jimeng's protocol requires at least 44 frames for camera export.
5. Render a still first. Check silhouette, clipping, exposure, object visibility and camera continuity.
6. In Blender GUI (not `--background`, because the add-on uses OpenGL viewport rendering), open `View3D > Sidebar > Jimeng` and choose `相机渲染`.
7. Select the camera, frame range, resolution (`360P`, `480P`, `720P`, `1080P` or `Origin`), output directory and prompt, then click `渲染`.
8. For an existing file choose `本地上传` and click `上传至即梦生成`.
9. Verify the MP4 exists and record the generated Dreamina link as a handoff artifact.

## MCP-safe rendering

- In the validated local setup, MCP render paths must be under the allowed home directory (for example `~/project/blender/exports/asset_camera.png`); `/tmp` may be rejected even though it is writable by the operating system.
- Workbench is the reliable default for a white model and avoids shader-node localization problems.
- On Blender 5.2 Chinese UI, `set_material_property` may fail because the add-on searches for the English node name `Principled BSDF`. If a material property is needed, call `list_shader_nodes`, find the returned `BSDF_PRINCIPLED` node, and use `set_node_value` with its returned node name and socket name.
- The current MCP tool set can render stills but does not save the active `.blend` or invoke the Jimeng operator. A `.blend` checkpoint and Jimeng upload therefore remain explicit GUI steps unless additional tools are enabled.

## White-model quality rules

- Preserve the model's silhouette and proportions; avoid dramatic materials that obscure form.
- Use neutral color, moderate roughness and soft directional light.
- Keep the camera and timing intentional because Seedance uses them as reference logic.
- Name exports with asset, camera, frame range and timestamp.
- Keep the `.blend` as source of truth; the MP4 is a derivative preview.

## Failure handling

- Less than 44 frames: extend the range or report the exact protocol blocker.
- Background mode/OpenGL failure: restart Blender in GUI mode and repeat.
- FFmpeg failure: preserve the `.blend`, try a supported resolution or use an existing MP4.
- Link expires: rerun the local bridge; it is not permanent hosting.
