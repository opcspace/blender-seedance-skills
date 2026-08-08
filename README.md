# Blender Seedance Skills

一组面向 Codex 的 Blender 建模与白模视频工作流 Skills，覆盖“提示词建模”和“参考图 + 提示词建模”两条入口，并支持把 Blender 白模交给 Jimeng/Dreamina 或可选的火山引擎 Ark API 继续生成视频。

## 包含内容

- `blender-seedance-modeling`：总路由，负责按任务组合其它 Skill。
- `blender-modeling`：通过提示词创建、修改和检查可编辑的 Blender 场景；支持 AI 参考图补建模。
- `blender-base-mesh-library`：角色、生物、道具、建筑、机械、环境、抽象形体七类 BaseMesh 设计与复用。
- `blender-white-model-render`：白模材质、灯光、相机、预览图/视频和导出检查。
- `seedance-white-model-video`：白模到 Seedance 视频的提示词、Jimeng 交接和可选 Ark API 流程。

## 安装

将 `skills/` 下的五个目录复制到 Codex Skills 目录，例如：

```bash
cp -R skills/* ~/.codex/skills/
```

使用前需要在本机安装 Blender，并运行 Blender MCP add-on。Jimeng 上传面板和火山引擎 API 是可选的外部依赖，本仓库不包含第三方插件、账号信息或 API 密钥。详细环境说明见 `skills/blender-seedance-modeling/references/local-setup.md`。

## 两种建模入口

1. 直接提示词：描述对象、风格、比例、部件、镜头和交付格式，Skill 在 Blender 中创建可继续编辑的场景。
2. 参考图 + 提示词：提供 AI 生成图或草图，先提取轮廓、比例和关键结构，再用补充提示词约束 Blender 几何、镜头和白模交付。

## 商用许可与署名要求

本项目采用 [MIT License](LICENSE)，允许商业使用、修改、复制和分发。

商业使用时请保留原版权声明和 MIT License 文本；如果在产品、文档或发布页中展示本项目来源，请注明 `OPCspace / Blender Seedance Skills` 并链接到本仓库。Blender、Jimeng、Dreamina、Seedance、Volcengine/Ark 等名称和服务属于其各自权利人；第三方插件、模型、示例素材和 API 仍受其自身许可及服务条款约束。

## 免责声明

本项目只提供本地工作流编排和辅助脚本，不保证第三方服务的可用性、模型输出结果、账号权限或 API 价格。请在公开发布模型、视频和素材前自行确认版权、肖像权、商标和平台规则。

