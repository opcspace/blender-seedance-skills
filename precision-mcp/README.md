# Precision Core V2 for Blender

Precision Core V2 是本地 FastMCP companion，用校准合同、确定性操作计划、Blender 白名单命令和可审计证据支持尺寸驱动白模。它与现有 `127.0.0.1:8400` Blender MCP 并行，不提供任意 Python 执行，也不内置联网资产服务。

## 安装与启动

要求 Python 3.10+；真实运行另需 Blender 5.2、已启用的 `blender_addon/precision_addon.py`，以及可写的本地工作目录。

```bash
python -m pip install "mcp>=1.3,<2" "httpx>=0.24" "jsonschema>=4.23,<5"
export PYTHONPATH="$PWD/precision-mcp"
export PRECISION_WORKDIR="$PWD/tests/assets/precision_v2"
export PRECISION_BLENDER_HOST=127.0.0.1
export PRECISION_BLENDER_PORT=9877
python -m precision_mcp.server
```

FastMCP 使用 stdio 与客户端通信；companion 每次调用新建一个到 add-on 的连接，并使用四字节长度前缀、JSON payload 和 `request_id` 关联的 framed transport。不要把 9877 端口当成 V2 客户端 API，也不要用旧的 raw-socket 脚本作为 V2 证明。

`PRECISION_WORKDIR` 是文件与证据边界。每个安全的 `job_id` 写入：

```text
evidence/<job-id>/
  scene_spec.json
  asset_manifest.json
  operation_plan.json
  assumptions.md
  qa_report.json
  checkpoints/{before,failed,final}.blend
  previews/{orthographic,perspective}.png
```

路径和符号链接不得逃出已解析的工作目录。

## V2 工作流

1. 用 `scene_spec.schema.json` 和 `asset_manifest.schema.json` 声明校准状态、绝对容差、资产来源、显式变换和锚点。
2. `precision_prepare_job` 校验合同并生成稳定排序的 typed operation plan。被阻塞的 CAD/外部步骤只保存计划，不启动 Blender 事务。
3. 按计划调用 `precision_create_part`、`precision_profile_extrude`、`precision_import_asset`、`precision_normalize_asset`、`precision_set_transform`、`precision_align_anchors` 或 `precision_patch_feature`。每个调用都必须携带 `job_id`。
4. `precision_validate_job` 把 Blender 的原始测量值与 SceneSpec 目标按绝对容差比较，写入 `qa_report.json`。
5. 只有合格报告才能由 `precision_finalize_job` 生成两个预览、checksummed final `.blend` 并提交。失败的 required assertion 写 `failed.blend`，且不得 commit。

## 适配器状态

- Blender：phase one 本地执行后端，可用性仍取决于真实 Blender/add-on runtime。
- CAD Sketcher：只接受 runtime 注入的检测状态；没有 solver/extension 报告时不会猜测可用，也不会静默回退。
- Tripo、Seedance：phase one online integration deferred。它们不是已安装集成；Tripo visual shell 计划标记 `external_pending`，Seedance 只能消费下游预览。

## 分级边界

- **L0**：未校准、缺门、视觉推断或 required 测量失败。
- **L1**：global envelope、每个 primary dimension、contact 和 anchor 四类门均有证据且全部通过。
- **L2**：在 L1 上，所有 required assertions、geometry、checkpoint、provenance 全部通过，且无 unresolved assumptions。

精度等级只来自最终 `qa_report.json`。商业 L2 交付还必须包含报告中记录且 SHA-256 匹配的最终 `.blend` 和预览。未运行的 GUI 验收、联网 visual shell 或未校准参考不能支持 L2。

## 验证边界

仓库 CI 安装 Python 依赖、运行全部 `test_precision_*.py`、编译 core/adapters/add-on、解析 JSON Schema 并验证六个 Skills；CI 不启动图形 Blender。真实 MCP-to-Blender 验收命令和当前状态记录在 `tests/PRECISION_MCP.md`。当 Blender executable/runtime 不可用时，状态必须保持 `BLOCKED`，不能用 portable PASS 替代。

## 许可

本 companion 采用 MIT License。CAD Sketcher、Blender、Jimeng/Dreamina/Seedance 及其它第三方项目仍受各自许可证和服务条款约束；本仓库不 vendoring CAD Sketcher、联网服务或第三方二进制。
