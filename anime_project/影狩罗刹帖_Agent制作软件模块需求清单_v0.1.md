# 《影狩罗刹帖》Agent 制作软件模块需求清单 v0.1

## 1. 软件目标

建立一套面向动画长片的 Agent 制作软件系统，支持《影狩罗刹帖》从开发包、剧本、分镜、资产、镜头、动画、合成、声音到交付的全流程管理与自动化生成。

系统代号：Kage Studio Hub

MVP 目标：
- 管理项目文件。
- 管理角色、场景、道具、敌人资产。
- 管理镜头和状态。
- 调度 Agent 任务。
- 记录审查意见。
- 生成日报、周报和风险报告。
- 支持《雨夜温泉宿》样片 21 镜生产。

## 2. MVP 模块

### 模块 1：项目与文件库

功能：
- 导入现有 Markdown 开发文件。
- 按类别展示：剧本、样片、制片、融资、美术、技术。
- 支持版本号。
- 支持全文搜索。
- 支持文件引用关系。

数据对象：
- Document
- DocumentVersion
- DocumentTag
- ReferenceLink

优先级：P0。

### 模块 2：剧本与场景管理

功能：
- 存储场景表。
- 场号、地点、时间、角色、事件、时长。
- 标记动作戏、尺度风险、制作难度。
- 从剧本正文提取场景。

数据对象：
- Script
- Scene
- SceneCharacter
- SceneRisk

优先级：P0。

### 模块 3：镜头管理

功能：
- 创建 sequence 和 shot。
- 为每个镜头记录时长、景别、动作、声音、难度、状态。
- 支持镜头状态流转：待分镜、分镜中、动态分镜、Layout、原画、动画、上色、背景、合成、声音、完成。
- 支持 S/A/B/C 难度。

数据对象：
- Sequence
- Shot
- ShotStatus
- ShotVersion
- ShotRisk
- ShotNote

优先级：P0。

### 模块 4：资产管理

功能：
- 管理角色、敌人、场景、道具、特效、声音资产。
- 每个资产有版本、状态、负责人、引用镜头。
- 支持角色一致性备注。

数据对象：
- Asset
- AssetType
- AssetVersion
- AssetReference
- CharacterProfile
- Prop
- Background

优先级：P0。

### 模块 5：Agent 任务调度

功能：
- 创建 Agent 任务。
- 指定输入文件和输出格式。
- 记录任务状态。
- 保存 Agent 输出。
- 支持人工审查后通过或退回。

任务类型：
- 编剧任务。
- 分镜任务。
- 角色设计提示词任务。
- 视觉参考整理任务。
- 镜头风险检查任务。
- 预算报告任务。
- 宣发文案任务。

数据对象：
- Agent
- AgentTask
- TaskInput
- TaskOutput
- TaskReview

优先级：P0。

### 模块 6：审查系统

功能：
- 对文件、场景、镜头、资产添加审查意见。
- 审查意见可分配给 Agent 或人员。
- 标记优先级。
- 支持通过、退回、挂起。

数据对象：
- Review
- ReviewComment
- ReviewDecision
- Approval

优先级：P0。

### 模块 7：预算与排期

功能：
- 样片预算表。
- 模块预算。
- 镜头预算权重。
- 超支预警。
- 4 周开发计划和 8 周样片计划。

数据对象：
- Budget
- BudgetLine
- Milestone
- ScheduleItem
- RiskAlert

优先级：P1。

### 模块 8：视觉提示词与生成工作流

功能：
- 从角色小传生成视觉提示词。
- 管理正向/负向提示词。
- 记录模型、参数、种子、参考图。
- 保存生成结果并进入资产库。

数据对象：
- Prompt
- PromptVersion
- GenerationJob
- GeneratedAsset
- ModelConfig

优先级：P1。

### 模块 9：质量检查

功能：
- 检查角色名称、场景连续性、镜头编号。
- 检查尺度风险标记是否缺失。
- 检查预算是否超出。
- 检查是否新增未经批准的大场景或角色。

数据对象：
- QualityCheck
- QualityIssue
- RiskRule

优先级：P1。

### 模块 10：报告系统

功能：
- 自动生成日报。
- 自动生成周报。
- 生成样片状态报告。
- 生成融资材料缺口报告。
- 生成风险报告。

数据对象：
- Report
- ReportTemplate
- ReportSchedule

优先级：P2。

## 3. 建议数据表草案

### projects

字段：
- id
- code
- name
- status
- target_runtime
- budget_range
- created_at
- updated_at

### documents

字段：
- id
- project_id
- title
- path
- category
- version
- status
- summary
- created_at
- updated_at

### scenes

字段：
- id
- project_id
- scene_number
- title
- location
- time_of_day
- estimated_minutes
- synopsis
- story_function
- character_change
- production_risk
- rating_risk

### shots

字段：
- id
- project_id
- sequence_code
- shot_code
- scene_id
- duration_seconds
- shot_size
- camera
- description
- action
- sound_notes
- difficulty
- status
- risk_tags

### assets

字段：
- id
- project_id
- asset_code
- asset_type
- name
- description
- status
- current_version
- owner_agent
- risk_notes

### agent_tasks

字段：
- id
- project_id
- agent_name
- task_type
- title
- prompt
- input_refs
- output_refs
- status
- priority
- due_date
- review_status

### reviews

字段：
- id
- project_id
- target_type
- target_id
- reviewer
- decision
- notes
- priority
- created_at

## 4. API 草案

### Project

- POST /projects
- GET /projects/{id}
- GET /projects/{id}/dashboard

### Documents

- POST /documents/import
- GET /documents
- GET /documents/{id}
- POST /documents/{id}/summarize

### Scenes

- POST /scenes
- GET /scenes
- GET /scenes/{id}
- POST /scenes/extract-from-script

### Shots

- POST /shots
- GET /shots
- GET /shots/{id}
- PATCH /shots/{id}/status
- POST /shots/import-shot-list

### Assets

- POST /assets
- GET /assets
- GET /assets/{id}
- POST /assets/{id}/versions

### Agent Tasks

- POST /agent-tasks
- GET /agent-tasks
- GET /agent-tasks/{id}
- POST /agent-tasks/{id}/run
- POST /agent-tasks/{id}/review

### Reviews

- POST /reviews
- GET /reviews
- PATCH /reviews/{id}

### Reports

- GET /reports/daily
- GET /reports/weekly
- GET /reports/risks
- GET /reports/sample-status

## 5. Agent 类型与系统提示方向

### DirectorAgent

职责：
- 审查创作是否符合项目气质。
- 检查动作是否清楚。
- 检查角色是否偏离小传。
- 给出修改指令。

### ProducerAgent

职责：
- 追踪预算和排期。
- 标记超支风险。
- 检查新增范围。
- 生成周报。

### WriterAgent

职责：
- 扩写剧本。
- 压缩对白。
- 修正人物弧线。
- 根据导演意见改写场景。

### StoryboardAgent

职责：
- 从剧本生成镜头建议。
- 生成分镜文字。
- 标注镜头难度。
- 检查空间连续性。

### VisualDesignAgent

职责：
- 从小传生成视觉提示词。
- 提出角色方向。
- 生成道具和场景提示词。
- 检查可动画化。

### ActionAgent

职责：
- 拆解战斗规则。
- 生成关键 Pose 描述。
- 检查动作是否可读。
- 控制无意义对砍。

### CompAgent

职责：
- 建议摄影合成模板。
- 标注雨、烟、火、血、毒膜层级。
- 检查夜景可读性。

### RiskAgent

职责：
- 检查版权相似风险。
- 检查尺度风险。
- 检查宣传用语风险。
- 输出风险等级。

## 6. 第一版开发任务拆分

### Sprint 1：项目库与镜头库

目标：
- 建立项目。
- 导入 22 份开发文档。
- 建立《雨夜温泉宿》21 镜 shot 数据。

任务：
1. 创建 FastAPI 项目。
2. 创建 PostgreSQL schema。
3. 创建 documents/scenes/shots/assets 基础表。
4. 写 Markdown 导入器。
5. 写 shot list 导入器。
6. 做基础 dashboard。

### Sprint 2：Agent 任务系统

目标：
- 可以创建 Agent 任务。
- 可以保存输入和输出。
- 可以人工审查。

任务：
1. 创建 agent_tasks 表。
2. 创建任务队列。
3. 创建任务详情页。
4. 创建 review 表和接口。
5. 实现 WriterAgent 和 ProducerAgent 的第一版。

### Sprint 3：样片生产看板

目标：
- 管理 21 镜状态。
- 显示 S/A/B/C 难度。
- 显示预算和风险。

任务：
1. 镜头看板 UI。
2. 状态拖拽或状态切换。
3. 镜头详情页。
4. 预算行项目。
5. 风险标签。

### Sprint 4：视觉提示词与生成记录

目标：
- 生成角色和场景提示词。
- 保存生成结果。
- 进入资产库。

任务：
1. Prompt 表。
2. Prompt 版本管理。
3. VisualDesignAgent。
4. ComfyUI 或等效工作流接口预留。
5. 资产入库。

## 7. MVP 完成定义

MVP 完成时必须能做到：
1. 查看全部开发文件。
2. 查看场景表。
3. 查看《雨夜温泉宿》21 个镜头。
4. 给每个镜头分配 Agent 任务。
5. 保存 Agent 输出。
6. 对输出进行审查和退回。
7. 查看样片预算和风险。
8. 自动生成每周状态报告。

## 8. 技术风险

| 风险 | 影响 | 控制 |
|---|---|---|
| 角色一致性难 | 高 | 建立角色参考库和人工最终审查 |
| 视频生成不可控 | 高 | 用于测试和参考，不直接作为唯一最终画面 |
| 版权相似性 | 高 | 版权检查 Agent + 人类法务审查 |
| 预算被生成试错吃掉 | 中 | 限制生成次数，记录成本 |
| Agent 输出互相矛盾 | 中 | 导演 Agent 和制片 Agent 统一裁决 |
| 文件版本混乱 | 高 | 强制版本和 shot id 规范 |

