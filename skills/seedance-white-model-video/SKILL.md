---
name: seedance-white-model-video
description: Convert Blender white-model previews, BaseMesh scenes, reference images and camera storyboards into Seedance 2.5-ready prompts and video handoffs. Use the official Dreamina case templates, the installed Jimeng uploader, or the optional Volcengine Ark asynchronous API.
---

# Seedance White-Model Video

This Skill owns the handoff from Blender white model to Seedance. Read `references/case-library.md` for built-in official case aliases.

Accept a precision-labeled asset only as a downstream, QA-approved committed model with its Precision Core V2 report. Seedance cannot measure geometry, add or upgrade L0/L1/L2, resolve failed assertions, or replace Blender evidence from `$blender-precision-modeling`.

When the user supplies a Dreamina URL, extract and decode its `prompt` query parameter before writing a new prompt. Preserve the URL-provided subject and constraints; use the case library only to structure Blender preparation and action beats. The helper script is `scripts/extract_dreamina_prompt.py`.

## Select a case

Supported aliases:

- `grey_city_cyberpunk`
- `white_castle_fantasy`
- `low_poly_car_chase`
- `white_interior_walkthrough`
- `character_pose_hero`
- `blockout_board_final`

If the user names a case, use its Blender scene grammar, camera movement and prompt template. Preserve the user's subject rather than copying the example literally.

## Prompt contract

```text
[reference] Blender white-model/blockout of <subject, scene and shot>.
[preserve] Keep <silhouette, proportions, layout, identity, camera composition and timing> stable.
[action] <ordered action beats with seconds>.
[camera] <shot size, lens feeling, movement, start/end framing>.
[look] Add <materials, lighting, atmosphere, environment and style>.
[constraints] no extra objects, no anatomy errors, no unreadable text, no watermark.
[use] <previs, client pitch, ecommerce, architecture presentation, social concept>.
```

Do not use vague prompts such as “make it cinematic” alone. State what the uploaded white model is, what must remain unchanged and what Seedance may transform.

## Delivery branches

### Jimeng / Dreamina

Use `blender-white-model-render` first to create the MP4. In Blender GUI open the Jimeng panel, choose camera render or local upload, then use the generated short-lived link. The plugin fills the video and prompt into the web page; it does not click the final generation button or download the final video.

### Volcengine Ark

Use only with a user-provided API key and a confirmed model/Endpoint ID:

```bash
export VOLCENGINE_API_KEY='...'
export VOLCENGINE_SEEDANCE_MODEL='model-or-endpoint-id'
python3 scripts/volcengine_seedance.py --prompt '...' --image-url 'https://...' --ratio 16:9 --duration 5
```

Never guess the model ID or expose a local Blender file without approval. The helper submits an asynchronous task, polls it, and prints the result URL. No direct API task is sent when credentials are absent.

## Report

Return the selected case, Blender checkpoint, white-model still/MP4, prompt, branch used, Jimeng handoff URL or Ark task ID/video URL, and any unverified step.
