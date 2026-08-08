# Blender Seedance Skills

一组面向 Codex 的 Blender 建模与白模视频工作流 Skills，覆盖“提示词建模”和“参考图 + 提示词建模”两条入口，并支持把 Blender 白模交给 Jimeng/Dreamina 或可选的火山引擎 Ark API 继续生成视频。

## 包含内容

- `blender-seedance-modeling`：总路由，负责按任务组合其它 Skill。
- `blender-modeling`：通过提示词创建、修改和检查可编辑的 Blender 场景；支持 AI 参考图补建模。
- `blender-base-mesh-library`：角色、生物、道具、建筑、机械、环境、抽象形体七类 BaseMesh 设计与复用。
- `blender-white-model-render`：白模材质、灯光、相机、预览图/视频和导出检查。
- `seedance-white-model-video`：白模到 Seedance 视频的提示词、Jimeng 交接和可选 Ark API 流程。
- `precision-mcp/`：参考 MCPBlender/blender-mcp 自建的高精度 Blender MCP companion；以白名单工具提供尺寸驱动网格、几何 QA、自动构图和白模渲染，不替换现有 8400 MCP。

## 安装

将 `skills/` 下的五个目录复制到 Codex Skills 目录，例如：

```bash
cp -R skills/* ~/.codex/skills/
```

使用前需要在本机安装 Blender，并运行 Blender MCP add-on。Jimeng 上传面板和火山引擎 API 是可选的外部依赖，本仓库不包含第三方插件、账号信息或 API 密钥。详细环境说明见 `skills/blender-seedance-modeling/references/local-setup.md`。

## 已验证能力与边界

在 Blender 5.2.0 LTS + Blender MCP 1.29.0 上，已验证基础体块创建、批量建模、定向修改、Bevel、相机/灯光、Workbench 白模静帧和变换关键帧。默认受限 MCP 工具集目前没有创建/移动 Collection、写入自定义属性、保存当前 `.blend`、上传图片或点击 Jimeng 面板的工具；这些步骤会被明确报告为 GUI/外部交接，而不会被伪装成自动完成。完整矩阵见 `skills/blender-seedance-modeling/references/mcp-capability-matrix.md`。

六个官方 Dreamina 白模案例的真实 Blender 回归结果见 [`tests/SEEDANCE_CASES.md`](tests/SEEDANCE_CASES.md)，包括每个案例的白模截图和机器可读 prompt 记录。

## 两种建模入口

1. 直接提示词：描述对象、风格、比例、部件、镜头和交付格式，Skill 在 Blender 中创建可继续编辑的场景。
2. 参考图 + 提示词：提供 AI 生成图或草图，先提取轮廓、比例和关键结构，再用补充提示词约束 Blender 几何、镜头和白模交付。

## 商用许可与署名要求

本项目采用 [MIT License](LICENSE)，允许商业使用、修改、复制和分发。

商业使用时请保留原版权声明和 MIT License 文本；如果在产品、文档或发布页中展示本项目来源，请注明 `OPCspace / Blender Seedance Skills` 并链接到本仓库。Blender、Jimeng、Dreamina、Seedance、Volcengine/Ark 等名称和服务属于其各自权利人；第三方插件、模型、示例素材和 API 仍受其自身许可及服务条款约束。

## 免责声明

本项目只提供本地工作流编排和辅助脚本，不保证第三方服务的可用性、模型输出结果、账号权限或 API 价格。请在公开发布模型、视频和素材前自行确认版权、肖像权、商标和平台规则。
