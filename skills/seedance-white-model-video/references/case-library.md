# Seedance case library

These are paraphrased from Dreamina's official Seedance 2.5 3D blockout-to-video examples: <https://dreamina.capcut.com/seedance/seedance-2-5-3d-blockout-to-video>

| Alias | Blender preparation | Seedance intention |
|---|---|---|
| `grey_city_cyberpunk` | Modular city, alley, road, camera dolly | Grey urban blockout becomes a rainy cyberpunk alley; preserve layout and camera path |
| `white_castle_fantasy` | Castle massing, towers, gate, terrain, establishing camera | White castle becomes a fantasy kingdom establishing shot |
| `low_poly_car_chase` | Low-poly vehicle, road spline, chase camera and safe spacing | Low-poly previs becomes a realistic/high-energy chase |
| `white_interior_walkthrough` | Room shell, openings, furniture proxies and path camera | White interior becomes a luxury walkthrough |
| `character_pose_hero` | Mannequin/pose proxy, hero prop, floor contact and push-in camera | Simple pose becomes a dramatic hero shot |
| `blockout_board_final` | Storyboard cards, shot cameras and timeline beat markers | Blockout board becomes a final-video concept montage |

For all cases, write the reference, preservation constraints, action beats, camera movement, look transformation and final use. Iterate with localized changes instead of regenerating the entire concept for every small adjustment.

## Dreamina URL prompt extraction: `white_castle_fantasy`

The supplied Dreamina URL carries this prompt in its URL-encoded `prompt` query parameter:

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'White Castle Model to Fantasy Shot', showing a white model castle blockout becoming a fantasy kingdom establishing shot. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### Reusable prompt slots

```text
Create a <duration>-second Dreamina Seedance 2.5 AI video scene for '<case title>', showing <white-model/blockout subject> becoming <target visual outcome>. Use the provided <reference types> as a multimodal reference. Preserve <composition and subject constraints>, add <camera movement>, <timeline pacing>, <lighting/look transformation>, <localized refinements>, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

The stable core is: duration + named transformation + multimodal reference + preservation constraints + camera movement + timeline pacing + lighting + localized iteration + negative constraints + professional finishing. Replace the subject-specific title and transformation, but keep this structure when the user asks for an official Dreamina-style prompt.

## Official page prompt set

The official page lists six copy-ready prompts. Preserve these as the canonical case seeds and only customize them when the user changes the subject or desired output.

### `grey_city_cyberpunk`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'Grey City Blockout to Cyberpunk', showing a grey urban blockout becoming a rainy cyberpunk alley shot. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### `white_castle_fantasy`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'White Castle Model to Fantasy Shot', showing a white model castle blockout becoming a fantasy kingdom establishing shot. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### `low_poly_car_chase`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'Low-Poly Car Chase Previs', showing a low-poly vehicle blockout becoming a realistic car chase frame. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### `white_interior_walkthrough`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'White Model Interior Walkthrough', showing a white model interior blockout becoming a luxury apartment walkthrough. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### `character_pose_hero`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'Character Pose to Hero Shot', showing a simple character pose blockout becoming a dramatic cinematic hero shot. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

### `blockout_board_final`

```text
Create a 30-second Dreamina Seedance 2.5 AI video scene for 'Blockout Board to Final Video', showing a creator screen with blockout boards and final AI video frames. Use the provided reference image, render, green-screen plate, white model, product photo, or storyboard as a multimodal reference. Preserve the core composition and subject intent, add cinematic camera movement, controlled timeline pacing, realistic lighting, localized refinements, no readable text, no watermark, and a polished result suitable for a professional creator workflow.
```

Source: [Dreamina Seedance 2.5 3D Blockout to Video](https://dreamina.capcut.com/seedance/seedance-2-5-3d-blockout-to-video). The page labels this section “Copy and Paste Seedance 2.5 3D Blockout to Video Prompts”; a login may still be required when opening a “Create Similar Video” button.
