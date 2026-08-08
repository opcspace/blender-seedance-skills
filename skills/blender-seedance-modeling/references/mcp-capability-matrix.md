# Blender MCP capability matrix

Validated against Blender 5.2.0 LTS, Blender MCP 1.29.0 and the local restricted tool list.

| Area | Result | Notes |
| --- | --- | --- |
| Scene/object inspection | Pass | `list_scenes`, `list_objects`, `get_scene_info`, `get_object_info` |
| Prompt blockout | Pass | Batch primitive creation, naming and transforms |
| Targeted model edits | Pass | Transform, duplicate, delete and modifier operations |
| White-model material | Partial | Workbench passes; Blender 5.2 Chinese node names require `list_shader_nodes` + `set_node_value` |
| Camera and lighting | Pass | Camera aim, active camera and area-light setup |
| Still render | Pass | PNG render passes; output path must be under the allowed home directory |
| Animation timing | Pass | FPS, frame range and transform keyframes |
| Collection organization | Manual fallback | No collection create/move tool in the default MCP list |
| Custom metadata | Manual fallback | No custom-property tool in the default MCP list |
| `.blend` checkpoint | Manual fallback | No save-mainfile tool in the default MCP list |
| Jimeng upload | Manual/browser handoff | The uploader add-on loads and registers operators, but MCP cannot click its GUI panel |
| Seedance generation | External handoff | Jimeng final generation or Ark API requires user credentials/authorization |

## Minimal regression case

Create a four-part robot blockout, assign a neutral material, add Bevel modifiers, move the head, create a camera and area light, render a 640×640 Workbench still, and keyframe the body rotation from frame 1 to 48 at 24 fps. The case should return named objects, no batch errors, a PNG artifact, and a frame range of 1–48.

