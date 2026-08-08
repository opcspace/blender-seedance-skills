---
name: blender-seedance-modeling
description: Orchestrate the local Blender white-model production stack. Route prompt/reference modeling to blender-modeling, BaseMesh and seven-category asset requests to blender-base-mesh-library, white-model rendering and Jimeng export to blender-white-model-render, and Seedance 2.5 video handoff/API work to seedance-white-model-video.
---

# Blender White-Model Production Router

This is the top-level workflow Skill. It keeps the production chain coherent while specialized Skills own their own procedures.

## Route the request

| User intent | Skill to use | Output |
|---|---|---|
| “按提示词建模”, “根据参考图建模”, “修改 Blender 模型” | `blender-modeling` | Editable `.blend` scene |
| “做一个人体/动物/道具/建筑/机械白模”, “找 BaseMesh”, “整理白模资源库” | `blender-base-mesh-library` | Categorized reusable BaseMesh |
| “渲染白模”, “生成白模 MP4”, “用 Jimeng 上传” | `blender-white-model-render` | Still, MP4, Jimeng handoff |
| “白模转 Seedance 2.5”, “套用官方案例”, “火山引擎生成视频” | `seedance-white-model-video` | Prompt, Jimeng link or Ark task result |
| “从建模一直做到视频” | Use all four in order | `.blend` → white-model MP4 → Seedance handoff |

## End-to-end order

1. Run the canonical environment check from the original Skill resources.
2. Use `blender-base-mesh-library` if a reusable asset family is needed.
3. Use `blender-modeling` to build or revise the editable scene through Blender MCP.
4. Use `blender-white-model-render` to prepare the neutral reference and MP4.
5. Use `seedance-white-model-video` to select a case, write the prompt and deliver through Jimeng or Volcengine.
6. Report every artifact and clearly distinguish completed local work from an external generation still awaiting user/browser/API completion.

## Shared invariants

- The `.blend` file is the source of truth.
- Keep `CODEX_Model`, `CODEX_Reference`, `CODEX_Stage` and `CODEX_Exports` collections stable.
- Preserve camera composition, object identity, spatial layout and timeline when handing off to Seedance.
- Do not enable unrestricted Blender MCP code execution unless explicitly requested.
- Never guess a Volcengine model ID or expose a local file publicly without approval.

## Tested capability boundary

The local Blender MCP 1.29 workflow has been tested for primitive blockout, targeted transforms, Bevel modifiers, camera/light setup, Workbench still rendering and transform keyframes. It has no native collection-management, active-file-save, image-upload or Jimeng-submit tool in the default restricted tool list. The router must report those as pending/manual handoff steps.

## Canonical local references

- Local setup and environment checker: `references/local-setup.md` and `scripts/check_environment.py`.
- Official Seedance case library: `references/official-case-library.md`.
- White-model research: `references/research-white-model-seedance.md`.
- Volcengine helper: `scripts/volcengine_seedance.py`.
