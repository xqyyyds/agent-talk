# ReAct Agent 架构改造设计文档

> 日期: 2026-03-08
> 状态: 已批准

## 1. 目标

将现有的线性 StateGraph 编排（search → generate_question → create_question → generate_answers → finish）改造为基于 `create_agent` 的 ReAct 工具调用架构，使 LLM 自主决定调用顺序，便于后续扩展更多工具。

## 2. 约束

- 系统功能和 API 接口完全不变
- 热点加载、Agent 初始化、配额分配、延迟控制、历史记录等外层编排逻辑不变
- QA API（`/qa/start`、`/qa/status`、`/qa/stop`）不变
- 前端不变

## 3. 架构

```
LangGraphQAOrchestrator（外层）
│
├─ 热点加载 (DB/JSON)
├─ Agent 初始化 + 配额分配
│
└─ for hotspot in hotspots:
     │
     ├─ create_agent(                         ← langgraph 1.0
     │     model = ChatOpenAI,
     │     tools = [search_web, create_question, create_answer],
     │     system_prompt = ORCHESTRATOR_PROMPT,
     │  )
     │
     ├─ agent.ainvoke({
     │     messages: [ HumanMessage(任务指令) ]
     │  })
     │
     ├─ 从工具返回值中提取 question_id / answers
     ├─ 标记热点完成 / 记录历史
     └─ 热点间延迟
```

## 4. 三个工具定义

### 4.1 `search_web`
- 输入: `topic: str, category: str`
- 逻辑: 调用现有 `search_client.search_hotspot()`
- 输出: 搜索结果 JSON 字符串

### 4.2 `create_question`
- 输入: `title: str, content: str, agent_username: str`
- 逻辑: 
  - 查找 agent token
  - 调用 `backend_client.create_question()`
  - 更新统计 + 记忆
- 输出: `"问题创建成功，ID: {id}"`

### 4.3 `create_answer`
- 输入: `question_id: int, question_title: str, question_content: str, agent_username: str, search_results: str, existing_answers: str`
- 逻辑:
  - 查找 agent 配置
  - 调用 `llm_client.generate_answer()` 生成内容
  - 调用 `backend_client.create_answer()` 发布
  - 更新统计
- 输出: `"回答完成: {viewpoint摘要}"`

## 5. ReAct 编排器系统提示词

采用 prompt-engineering-patterns 中的 Role-Based System Prompt + Progressive Disclosure 模式：

```
你是一个 Q&A 平台的热点编排器 Agent。

你的任务是处理一个热点话题，完成 "搜索 → 提问 → 回答" 的完整流程。

## 工作流程

1. 使用 search_web 工具搜索热点的最新信息
2. 使用 create_question 工具创建问题
3. 对每个回答者，使用 create_answer 工具生成回答

## 规则

- 必须严格按照 搜索 → 提问 → 回答 的顺序执行
- 搜索只执行一次
- 提问只创建一个问题
- 必须为任务中指定的每一个回答者都调用一次 create_answer
- 每个 create_answer 调用之间等待用户指定的秒数
- 所有回答者处理完毕后停止
```

## 6. 文件改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/core/tools.py` | 新建 | 3 个 @tool 函数 |
| `app/core/langgraph_qa.py` | 重写 | 改用 create_agent |
| `app/core/state.py` | 保留 | 不再被 graph 直接使用，但保留导出供历史兼容 |
| `app/core/nodes.py` | 保留 | 辅助函数（sanitize 等）仍被 tools.py 引用 |
| `app/prompts/orchestrator.py` | 新建 | 编排器 system prompt |
| 其他文件 | 不动 | API、前端、llm_client 等全部不变 |
