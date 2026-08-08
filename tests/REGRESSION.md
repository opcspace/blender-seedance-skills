# Regression test record

Environment: Blender 5.2.0 LTS, Blender MCP 1.29.0, macOS, restricted MCP tool list.

## Cases

| Case | Result | Evidence |
| --- | --- | --- |
| Prompt blockout | Pass | Created a four-part robot with stable `CODEX_Model_*` names |
| Targeted edit | Pass | Moved/scaled the head and inspected transforms |
| Modifier pass | Pass | Added Bevel to four mesh objects |
| Camera and light | Pass | Created camera, aimed it, set active camera and configured area light |
| White-model still | Pass | Workbench PNG, 640×640, saved under the allowed home directory |
| Animation | Pass | 24 fps, frames 1–48, body rotation keyframes at 1 and 48 |
| BaseMesh naming fallback | Pass with limitation | Prefix convention works; collection/custom-property writes are unavailable in default MCP |
| Material properties | Partial | `create_material` works; `set_material_property` fails on localized Blender 5.2 node names; `list_shader_nodes` + `set_node_value` works |
| Reference image import | Manual fallback | Default MCP tool list has no image-import/reference-collection tool |
| `.blend` checkpoint | Manual fallback | Default MCP tool list has no save-mainfile tool |
| Jimeng upload | Manual/browser handoff | Uploader add-on loads, `load_config` succeeds, and operators register; GUI submission remains manual |
| Seedance generation | External handoff | Requires Jimeng/Dreamina UI or user-authorized Ark credentials and model ID |

## Reproducible core sequence

Use `create_objects_batch`, `create_material`, `assign_materials_batch`, `add_modifiers_batch`, `transform_object`, `create_objects_batch` for camera/light, `look_at`, `set_active_camera`, `set_render_settings`, `render_image`, `set_fps`, `set_frame_range`, and `insert_keyframe`.

For a white model, prefer `BLENDER_WORKBENCH` and an output path under the allowed home directory. Do not use `/tmp` for MCP render output in this local configuration.

