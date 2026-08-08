# Local setup

This reference describes the local prerequisites for the skill. Re-run the environment checker rather than assuming paths on another machine.

## Blender MCP

- Blender executable: configure the path for your operating system
- Blender version validated during development: 5.2.0 LTS; other recent versions may work
- Blender MCP add-on: install and enable it in the Blender user add-ons directory
- Blender MCP HTTP endpoint: `http://127.0.0.1:8400/mcp`
- Codex stdio bridge: configure a local launcher that reads the MCP token
- Codex MCP registration: your Codex configuration, section `[mcp_servers.blender]`

Blender must be running with the add-on enabled before the stdio bridge can reach the HTTP endpoint. The add-on creates a token at `~/.config/blender-mcp/token`; the launcher reads it automatically.

## Jimeng uploader

The supplied zip is `jimeng_blender_uploader-mac-cn-1.0.0.zip`. It provides the Blender panel `View3D > Sidebar > Jimeng` and two modes:

1. `相机渲染`: export a camera preview, encode H.264 MP4 with the bundled FFmpeg, then create a local bridge link.
2. `本地上传`: use an existing video and create the same handoff link.

The target page is Jimeng/Dreamina. The bridge returns video metadata and the prompt to the web page; it does not itself click the Seedance generate button or download the final generated video.

## Optional Volcengine Ark branch

The Skill includes `scripts/volcengine_seedance.py`, which uses the Ark asynchronous contents-generation API. Configure these only when direct API generation is enabled for the account:

```bash
export VOLCENGINE_API_KEY='...'
export VOLCENGINE_SEEDANCE_MODEL='model-id-or-endpoint-id-from-console'
```

The public API documentation confirms the task submission/query mechanism, but the exact Seedance 2.5 model ID is not safely inferable from public documentation. Treat the console-provided ID as authoritative. The helper accepts HTTPS reference image URLs; it does not upload local files or expose a local Blender path.

## Verification

Run from the installed Skill directory:

```bash
python3 skills/blender-seedance-modeling/scripts/check_environment.py
```

For a Blender-side check, open Blender and confirm the add-ons are enabled. For a Codex-side check, restart Codex after changes to `~/.codex/config.toml` and confirm the Blender MCP tools are listed.
