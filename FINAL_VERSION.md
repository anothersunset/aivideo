# Kage Studio — 最终版本与验收（Notion AI 接手交付）

> 接手工程师：Notion AI　｜　交付日期：2026-06-03（Asia/Shanghai）
> 仓库：`anothersunset/aivideo`　｜　分支：`main`
> 本文件是本次接手的**权威最终状态 + 验收标准 + 本地最终化 runbook**。

---

## 0. 一句话结论

- **模拟链 + 本地管线：已达到可验收的最终版本。** 限动原型、HQ provider 回流模拟链（TASK-058~061）、MCP 视频网关与本地桥接彩排（TASK-062）全部在 GitHub 中，且代码层已加固（见第 4 节）。
- **真实外部 provider 渲染：按设计仍未执行、且默认被阻断。** submit gate 放行 provider 数 = 0，全程无外部 API 调用，master preview 锁在 `needs_director_review`。
- **诚实边界：** 实际渲染、跑链、跑 verify 需要本地 Python + FFmpeg 环境。Notion 侧无法执行二进制，本文件交付的是源码层最终版 + 状态固化 + 操作手册，不代表在 Notion 内重新渲染过任何产物。

---

## 1. 任务台账真实状态（共 62 个任务）

- `TASK-001` ~ `TASK-061`：全部 `status: Approved` / `review: Approved`。
- `TASK-062`：`status: Completed` / `review: Needs review`（real provider 接入获批前保持待审）。

关键尾段：

| Task | Agent | 状态 | 产物 / 说明 |
| --- | --- | --- | --- |
| TASK-055 | CurrentDemoPromotionAgent | Approved | 反复评审的 v02 升级为 current demo |
| TASK-056 | HighQualityProviderLaunchAgent | Approved | HQ provider 启动包（不外发） |
| TASK-057 | HighQualityProviderHandoffPackageAgent | Approved | HQ provider 操作员交接 zip |
| TASK-058 | HQProviderReturnSimAgent | Approved | 模拟 HQ 回流 MP4，无外部 API |
| TASK-059 | ExternalResultIngestAgent | Approved | 校验：accepted≥2 / rejected0 / unknown0 |
| TASK-060 | ExternalResultReviewAgent | Approved | 接受项审查通过 |
| TASK-061 | ShotReplacementAgent | Approved | 替换重建 master，**status: needs_director_review** |
| TASK-062 | MCPVideoGatewayAgent | Completed / Needs review | 15 条 dispatch payload；3 个 Kling 本地分片实跑；submit gate 复位 blocked |

---

## 2. 不可逾越的安全红线

1. `anime_project/pipeline/submit_gate/external_submit_gate_manifest.json` 中 `allowed_provider_count == 0`——默认阻断全部商业 provider。
2. 无任何真实外部 API 调用；以下开关默认全部关闭：
   - `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC`
   - `KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC`
   - `KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_SUBMIT` / `KAGE_EXTERNAL_VIDEO_ENABLE_HTTP_POLL`
3. master preview 永远保持 `needs_director_review`，未经导演/制片人审批不得标记 `final_release_ready`。
4. 不提交任何真实 secret、`.env`、cookie、provider endpoint 或 API token。

---

## 3. 最终产物坐标（GitHub / LFS）

可播放证据：

- `anime_project/deliverables/current_demo/video/kage_current_demo.mp4`
- `anime_project/deliverables/producer_demo_v02/video/kage_preview_with_local_polish.mp4`
- `anime_project/deliverables/hq_provider_return_sim_v01/video/kage_preview_with_hq_sim_replacements.mp4`
- `anime_project/episode_segments/act2_01_sample/final/act2_01_sample_limited_animation.mp4`
- `anime_project/episode_segments/onsen_01_sample/final/onsen_01_sample_limited_animation.mp4`

MCP 本地桥接彩排（真实本地渲染、显式标注 no external API call）：

- `.../local_sim_outputs/kling_i2v_rehearsal/.../08-004/08-004_kling_i2v_chunk01.mp4`
- `.../local_sim_outputs/kling_i2v_rehearsal/.../ON-008/ON-008_kling_i2v_chunk01.mp4`
- `.../local_sim_outputs/kling_i2v_rehearsal/.../ON-008/ON-008_kling_i2v_chunk02.mp4`

---

## 4. 代码层最终版本（已加固，PR #2 + 现有 MCP 网关）

- `kage_studio_hub/pipeline_common.py`——单一事实源：目标镜头、provider 优先级/白名单、segments、`1920x1080/24fps` 编码常量、`normalize_path / resolve_workspace_path`（跨平台路径）、`run_checked`（失败抛 `CommandError`，携带 stderr）、`MissingToolError`（环境缺工具硬失败）。
- `kage_studio_hub/shot_replacement_agent.py`——`concat_videos` 改为逐片**归一化 + 重编码**（`scale+crop→1920x1080 / fps=24 / yuv420p / setsar=1` → `filter_complex concat`），消除 `-c copy` 编码不一致；新增 `_verify_output()` ffprobe 复核；master 统计缺键回退而非静默 0。
- `kage_studio_hub/external_result_ingest_agent.py`——`build_expected_manifest(create_dirs=False)`，scan 不再创建空目录；ffprobe 缺失硬失败，质量不合格才标 rejected。
- `kage_studio_hub/external_result_review_agent.py` / `hq_provider_return_sim_agent.py`——统一用 `pipeline_common` 的路径解析与 `run_checked`。
- `kage_studio_hub/mcp_video_gateway_agent.py`——读 submit gate + provider 队列，产出 15 条 `submit_video_job` MCP dispatch payload；`prepare_only`，仅当 `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true` 且桥已配置才执行。
- `kage_studio_hub/mcp_http_video_bridge.py`——通用 HTTP 桥模板，默认 `queued` 不发请求，`external_api_call=false`。
- `kage_studio_hub/mcp_video_bridge_sim.py`——本地桥接彩排，复用 `pipeline_common`，产出真实 H.264 MP4 分片并写 sidecar。
- `scripts/verify_notion_handoff.py`——契约校验：必备文件、文档引用路径、TASK-062 须 `Needs review`、网关 manifest 须 `prepare_only` 且 15 blocked、submit gate 须 0 放行、HTTP 桥默认 `queued` 不外发、媒体 ffprobe（rehearsal 强制 1920x1080/24fps）。

> 注：verify 脚本**要求** dispatch payload 内 schema 路径使用反斜杠、网关保持 `prepare_only`、submit gate 全 blocked。这些是有意契约，后续改动不得破坏。

---

## 5. 本地最终化 Runbook（在装有 Python + FFmpeg 的机器上）

### 5.1 验证当前最终版本
```bash
python -m py_compile kage_studio_hub/*.py
python scripts/verify_notion_handoff.py            # 完整校验（需 ffprobe）
python scripts/verify_notion_handoff.py --skip-media # 跳过媒体探测
```
期望输出：`Notion/GitHub handoff verification passed`

### 5.2 重跑 HQ 回流模拟链（无外部调用，可重现 058~061）
```bash
python kage_studio_hub/run_hq_provider_return_chain.py
```
产物落在 `external_results/{inbox,manifests}`、`external_reviews/`、`master_preview/manifest_with_replacements.json`，master 保持 `needs_director_review`。

### 5.3 （可选）接入真实 provider —— 需显式授权后才做
1. 选定一条 provider 路线（Kling / Seedance / Runway / Luma / Pika / ComfyUI / AnimateDiff / Remotion 等）。
2. 用 `kage_studio_hub/mcp_http_video_bridge.py` 为该路线配置 endpoint + token（经环境变量，**不要提交**）。
3. 在 submit gate 配置审批与成本上限。
4. 仅在确认外部调用获批后设 `KAGE_MCP_VIDEO_GATEWAY_ENABLE_EXEC=true` / `KAGE_MCP_HTTP_BRIDGE_ENABLE_EXEC=true`。
5. 重跑 `MCPVideoGatewayAgent`（执行模式），把返回 MP4 放入 `anime_project/pipeline/external_results/inbox/{provider}/{segment}/{shot_id}/`。
6. 依次跑 ingest → review → replacement → master rebuild。
7. 导演/制片人审查通过后，方可解除 `needs_director_review`。

---

## 6. 验收清单（门禁阈值）

Ingest 校验门禁：
- 分辨率 == 1920×1080；`r_frame_rate == "24/1"`（精确）。
- 时长偏差 ≤ max(0.5s, 目标×8%)。
- 文件 > 100,000 bytes；含视频流。

链路门禁：
- TASK-058：`external_api_called == false` 且 return ≥ 2。
- TASK-059：accepted ≥ 2 / rejected 0 / unknown 0。
- TASK-060：reviewed ≥ 2 / approved ≥ 2 / returned 0。
- TASK-061：强制 master `needs_director_review`。
- TASK-062：网关 `prepare_only`、15 dispatch / 15 blocked、本地彩排 submitted 3 / failed 0、submit gate 0 放行。

验收通过判据：`python scripts/verify_notion_handoff.py` 退出码 0。

---

## 7. 边界声明

本文件由 Notion AI 在工作区内编写并提交。Notion 侧**不能**运行 Python / FFmpeg / Node,因此：

- 以上状态是基于仓库 `main` 的台账与 manifest 如实核对的结果,非在 Notion 内重新执行所得。
- 真实渲染、跑链、跑 verify、接入付费 provider 必须由本地操作员按第 5 节执行。
- 任何 secret / token 不得入库;若历史上曾在对话中泄露 token,请立即在 GitHub 设置中吊销。
