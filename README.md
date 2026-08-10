# Blender Seedance Skills

一组面向 Codex 的 Blender 建模与白模视频工作流 Skills，覆盖“提示词建模”和“参考图 + 提示词建模”两条入口，并支持把 Blender 白模交给 Jimeng/Dreamina 或可选的火山引擎 Ark API 继续生成视频。

## 包含内容

- `blender-seedance-modeling`：总路由，负责按任务组合其它 Skill。
- `blender-modeling`：通过提示词创建、修改和检查可编辑的 Blender 场景；支持 AI 参考图补建模。
- `blender-base-mesh-library`：角色、生物、道具、建筑、机械、环境、抽象形体七类 BaseMesh 设计与复用。
- `blender-white-model-render`：白模材质、灯光、相机、预览图/视频和导出检查。
- `seedance-white-model-video`：白模到 Seedance 视频的提示词、Jimeng 交接和可选 Ark API 流程。
- `blender-precision-modeling`：Precision Core V2 路由；把校准参考、绝对容差、Typed 操作、证据包和 L0/L1/L2 交付绑定在一起。
- `precision-mcp/`：独立的本地 FastMCP companion；通过 `127.0.0.1:9877` 的长度前缀 framed transport 调用 Blender 白名单工具，不替换现有 8400 MCP。

## 安装

将 `skills/` 下的六个目录复制到 Codex Skills 目录，例如：

```bash
cp -R skills/* ~/.codex/skills/
```

使用前需要在本机安装 Blender，并运行 Blender MCP add-on。Jimeng 上传面板和火山引擎 API 是可选的外部依赖，本仓库不包含第三方插件、账号信息或 API 密钥。详细环境说明见 `skills/blender-seedance-modeling/references/local-setup.md`。

高精度任务请显式调用 `$blender-precision-modeling`，安装并启用
`precision-mcp/blender_addon/precision_addon.py`，再以仓库内目录启动服务：

```bash
export PRECISION_WORKDIR="$PWD/tests/assets/precision_v2"
PYTHONPATH="$PWD/precision-mcp" python -m precision_mcp.server
```

服务通过 stdio 暴露 FastMCP 工具，并由 companion 连接 Blender add-on 的 framed
`127.0.0.1:9877` 端口。`PRECISION_WORKDIR` 是证据和 `.blend` 文件的安全边界，不应指向不受控目录。

## 已验证能力与边界

在 Blender 5.2.0 LTS + Blender MCP 1.29.0 上，已验证基础体块创建、批量建模、定向修改、Bevel、相机/灯光、Workbench 白模静帧和变换关键帧。默认受限 MCP 工具集目前没有创建/移动 Collection、写入自定义属性、保存当前 `.blend`、上传图片或点击 Jimeng 面板的工具；这些步骤会被明确报告为 GUI/外部交接，而不会被伪装成自动完成。完整矩阵见 `skills/blender-seedance-modeling/references/mcp-capability-matrix.md`。

六个官方 Dreamina 白模案例的真实 Blender 回归结果见 [`tests/SEEDANCE_CASES.md`](tests/SEEDANCE_CASES.md)，包括每个案例的白模截图和机器可读 prompt 记录。

Precision Core V2 的可移植合同、规划、分级和安全测试结果，以及当前 Blender 5.2 GUI
验收阻塞状态见 [`tests/PRECISION_MCP.md`](tests/PRECISION_MCP.md)。GUI 未执行时不会把
可移植测试写成真实 Blender 运行证明。

现有五个 Skill 仍是兼容入口：`blender-seedance-modeling` 负责总路由，
`blender-modeling` 和 `blender-base-mesh-library` 处理非精度建模，
`blender-white-model-render` 与 `seedance-white-model-video` 只消费已提交的精度产物。
凡涉及校准尺寸、绝对容差或商业精度声明，都会转交 `blender-precision-modeling`。

## 两种建模入口

1. 直接提示词：描述对象、风格、比例、部件、镜头和交付格式，Skill 在 Blender 中创建可继续编辑的场景。
2. 参考图 + 提示词：提供 AI 生成图或草图，先提取轮廓、比例和关键结构，再用补充提示词约束 Blender 几何、镜头和白模交付。

## 商用许可与署名要求

本项目采用 [MIT License](LICENSE)，允许商业使用、修改、复制和分发。

商业使用时请保留原版权声明和 MIT License 文本；如果在产品、文档或发布页中展示本项目来源，请注明 `OPCspace / Blender Seedance Skills` 并链接到本仓库。Blender、Jimeng、Dreamina、Seedance、Volcengine/Ark 等名称和服务属于其各自权利人；第三方插件、模型、示例素材和 API 仍受其自身许可及服务条款约束。

高精度白模的商业交付分级、证据包和第三方许可边界见 [`COMMERCIAL_USE.md`](COMMERCIAL_USE.md)。

## 免责声明

本项目只提供本地工作流编排和辅助脚本，不保证第三方服务的可用性、模型输出结果、账号权限或 API 价格。请在公开发布模型、视频和素材前自行确认版权、肖像权、商标和平台规则。
