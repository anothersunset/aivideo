# Kage Studio Hub MVP

这是《影狩罗刹帖》Agent 化动画制作系统的本地 MVP。

## 当前功能

- 项目总览仪表盘
- 开发文件索引
- 《雨夜温泉宿》21 镜样片看板
- Agent 任务角色列表
- Agent 任务创建、模拟运行、批准、退回
- 推荐档样片预算图
- 高风险项列表

## 使用方式

静态模式可以直接在浏览器打开：

```text
D:\codex\kage_studio_hub\index.html
```

API 模式启动：

```powershell
cd D:\codex
python kage_studio_hub\server.py
```

然后打开：

```text
http://127.0.0.1:8765
```

API 模式会自动扫描 `D:\codex\anime_project` 下的 Markdown 开发文件，并把它们加载到“开发文件”页面。

## Agent Task API

```text
GET  /api/tasks
POST /api/tasks
POST /api/tasks/{task_id}/run
POST /api/tasks/{task_id}/review
```

当前 MVP 会把任务保存在：

```text
D:\codex\kage_studio_hub\data\agent_tasks.json
```

`run` 目前是模拟 Agent 输出，用于验证制作调度、审查、退回流程。下一步可接入真实 WriterAgent、ProducerAgent、RiskAgent。

## 下一步开发

1. 改为 FastAPI + PostgreSQL 数据后端。
2. 自动导入 `anime_project` 目录里的 Markdown 文件。
3. 实现 shot/asset/agent_task 数据表。
4. 接入真实 WriterAgent、ProducerAgent、RiskAgent。
5. 接入视觉生成工作流和动态分镜生成。
