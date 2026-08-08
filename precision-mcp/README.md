# Precision MCP for Blender

一个面向高精度白模和 Seedance 参考镜头的本地 Blender MCP companion。

它参考 [MCPBlender/blender-mcp](https://github.com/MCPBlender/blender-mcp) 的
MCP + socket bridge 结构，但不直接启用上游的任意 Python 执行工具，也不包含上游的
遥测、Poly Haven、Sketchfab、Hyper3D 或 Hunyuan3D 网络集成。

## 目标

- 用 `model_spec` 描述尺寸、比例、部件和约束，而不是把最终尺寸误当成 primitive scale。
- 用 Blender 原生网格生成和检查保证尺寸、原点、地面、法线、非流形和相机占幅可验证。
- 为 CAD Sketcher 保留可选适配点；只有收到约束求解报告时，才允许 Skill 宣称 CAD 级精度。
- 支持七类 BaseMesh：角色、生物、道具、建筑、硬表面机械、环境地形、抽象形体。
- 通过白模渲染工具生成可交给 Jimeng/Seedance 的参考图；上传和最终生成仍属于外部服务交接。

## 安全边界

默认没有 `execute_blender_code`。所有命令都经过固定的 command allow-list，文件路径只允许写入
显式配置的工作目录。外部 API、图片上传、账号登录和 Jimeng 点击不在这个 MCP 的默认权限内。

## 当前状态

这是第一阶段 companion MVP，先与现有 Blender MCP 并行运行，不覆盖现有插件。安装前请确认：

1. Blender 5.2 LTS 已安装并可启动。
2. 当前 Blender MCP 仍使用 `127.0.0.1:8400`。
3. 本 precision addon 使用独立端口 `127.0.0.1:9877`。
4. `uv` 或 Python 3.10+ 可用。

安装 `blender_addon/precision_addon.py` 后，在 Blender 的 Add-ons 中启用它；然后运行：

```bash
cd precision-mcp
uv run --with "mcp>=1.3,<2" --with "httpx>=0.24" python -m precision_mcp.server
```

也可以设置：

```bash
export PRECISION_BLENDER_HOST=127.0.0.1
export PRECISION_BLENDER_PORT=9877
export PRECISION_WORKDIR=/absolute/path/to/your/blender/project
```

## 工具路线

1. `precision_begin`：建立本次建模事务；默认不删除已有对象，只有显式传入 `clean_existing=true` 才清理前缀对象。MVP 运行前仍建议由上层 Skill 写入 `.blend` 检查点。
2. `precision_create_mesh` / `precision_create_primitive`：按显式网格或原生参数体生成命名对象，并写入目标尺寸。
3. `precision_set_dimensions`：按世界尺寸修正对象，避免 scale 语义混乱。
4. `precision_inspect_geometry` / `precision_validate_scene`：返回尺寸、包围盒、拓扑和接地 QA。
5. `precision_frame_camera`：按对象包围盒和目标占幅自动构图。
6. `precision_save_checkpoint`：在工作目录内写入 `.blend` 检查点。
7. `precision_render_white_model`：使用 Workbench 白模渲染预览。
8. `precision_commit` / `precision_abort`：提交事务或删除本事务新建对象；已有对象不会被 Abort 自动恢复，跨文件恢复仍依赖检查点。

后续阶段会增加 `precision_create_sketch`、`precision_add_constraint` 和
`precision_solver_report`，对接 CAD Sketcher；这部分不会把 GPL-3.0 的 CAD Sketcher 源码复制进本 MIT 仓库。

## 许可

本 companion 代码采用 MIT License，与父仓库一致。上游 MCPBlender/blender-mcp 也标注为 MIT，
但其代码、条款和数据政策仍应以其仓库当前版本为准。CAD Sketcher、Blender、Jimeng、Seedance
及其它第三方服务分别受其自身许可证和服务条款约束。
