# Official Seedance 2.5 Case Library

Use these aliases when the user asks to “套用官方案例”, “按 Dreamina 白模案例做”, or names one of the cases below. The case is a production starting point, not a rigid copy: preserve the user's subject and constraints while borrowing the scene grammar.

Source: Dreamina's official [Seedance 2.5 3D Blockout to Video workflow](https://dreamina.capcut.com/seedance/seedance-2-5-3d-blockout-to-video), which presents six examples and describes white-model/low-poly references, camera direction, timeline control, multimodal inputs and localized iteration.

## Case selection

| Alias | Official case | Blender build recipe | Default output direction |
|---|---|---|---|
| `grey_city_cyberpunk` | Grey City Blockout to Cyberpunk | modular buildings, road planes, alley props, volumetric-light placeholder, forward dolly or crane camera | rainy cyberpunk alley, preserve street layout and camera path |
| `white_castle_fantasy` | White Castle Model to Fantasy Shot | castle massing, towers, walls, gate, terrain plane, establishing camera | fantasy kingdom establishing shot, preserve castle silhouette and spatial hierarchy |
| `low_poly_car_chase` | Low-Poly Car Chase Previs | low-poly vehicle, road spline, chase vehicle empties, collision-safe spacing, tracking camera | realistic/high-energy car chase, preserve vehicle route and shot timing |
| `white_interior_walkthrough` | White Model Interior Walkthrough | room shell, openings, stairs, furniture proxies, path camera, door-height framing | luxury interior walkthrough, preserve room proportions and camera route |
| `character_pose_hero` | Character Pose to Hero Shot | pose proxy or mannequin, hero prop, floor contact, three-point light, push-in camera | dramatic hero shot, preserve pose direction and framing |
| `blockout_board_final` | Blockout Board to Final Video | storyboard cards, numbered cameras, simple stage blocks, shot markers and timeline beats | concept-board-to-final montage, preserve sequence order and beat timing |

## How to use a case

1. Select the alias from the user's wording. If no alias is clear, ask whether the work is city, architecture, vehicle, interior, character, or storyboard.
2. Build the Blender white model according to the recipe. Keep geometry intentionally simple but make the camera and movement explicit.
3. Create a reference package: one hero still, the white-model MP4, and optional per-shot stills. Do not upload every construction helper unless it affects composition.
4. Use the prompt template below, replacing only the subject-specific fields:

```text
Official case: <alias>.
Input: Blender white-model/blockout reference of <subject>.
Preserve: <silhouette, spatial layout, object identity, camera composition, route and timeline beats>.
Transform: add <materials, lighting, weather, environment, atmosphere> while keeping the reference logic.
Action: <ordered action beats with approximate seconds>.
Camera: <shot size, lens feeling, camera movement, start/end framing>.
Finish: cinematic but physically coherent, no extra objects, no readable text, no watermark.
Use: <previs, client pitch, product concept, social clip, architecture presentation>.
```

## Case-specific checks

- **City**: validate road/building occlusion, scale cues and a clear camera path.
- **Castle**: validate the establishing silhouette and keep towers/gate in consistent screen positions.
- **Car chase**: validate lane direction, vehicle spacing, wheel contact and action beats before export.
- **Interior**: validate camera height, doorway clearance, room scale and exposure transitions.
- **Character**: validate feet/contact points, prop placement, face direction and a readable hero contour.
- **Board**: validate camera order, shot labels, frame ranges and transitions before creating the montage.

The official page describes these as reference-driven creative workflows; it does not guarantee that a generated video will preserve every hidden 3D surface. Keep the Blender `.blend` as the editable source of truth and use Seedance output as a visual iteration.
