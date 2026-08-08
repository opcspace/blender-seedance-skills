# Installed Blender plugins

The local test machine has these add-ons installed and validated:

| Add-on | Version | Blender | Status |
| --- | --- | --- | --- |
| Blender MCP Server | server 1.29.0; add-on metadata 0.5.1 | 4.0+ | MCP initialize, tools/list and modeling calls passed |
| 即梦 Seedance 2.5 预览渲染上传器 | 1.0.0 | 3.6+ | Add-on load and `jimeng.load_config` passed; GUI upload remains manual |

## Why the add-on binaries are not vendored

This repository records the tested versions and installation contract, but does not redistribute the installed add-on directories or the bundled FFmpeg runtime. The installed uploader package does not include a clear standalone open-source license, and third-party runtime components retain their own licenses. This avoids accidentally relicensing or redistributing software without permission.

## Installation

### Blender MCP Server

Install the Blender MCP add-on from its upstream distribution, enable it in Blender, and configure Codex with a local stdio bridge that points to the add-on's HTTP endpoint. The default local endpoint is `http://127.0.0.1:8400/mcp`. Keep the MCP token local; never commit it.

### Jimeng uploader

Install the separately obtained `jimeng_blender_uploader` ZIP through `Edit > Preferences > Add-ons > Install...`, enable `即梦 Seedance 2.5 预览渲染上传器`, then open `View3D > Sidebar > Jimeng`. The uploader creates a short-lived local bridge link; it does not automatically click the final Seedance generation button.

The original package name used in the local test was `jimeng_blender_uploader-mac-cn-1.0.0.zip`. Obtain it from an authorized source and verify its license before redistribution.

