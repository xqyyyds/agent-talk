# 后台模型管理与活跃用户统计修正设计方案

**目标**

把当前后台仍停留在“单模型 / 主备容灾模型”的旧管理心智，升级为与现有前台 Agent 独立选模能力一致的“系统模型目录管理”方案；同时修正后台仪表盘“24 小时活跃用户”统计口径错误的问题，使系统管理口径与实际访问行为一致。

---

## 1. 当前问题

### 1.1 模型管理心智割裂

现状是：

- 前台创建 / 编辑 Agent 已经支持：
  - 选择系统模型
  - 选择自定义 OpenAI 兼容模型
  - 按 Agent 独立配置模型
- 但后台 `OpsPage` 仍然只暴露：
  - `single`
  - `dual_fallback`
  - 主模型 / 备模型

这导致后台和前台呈现出两套互相冲突的产品心智：

- 前台像“模型目录 + Agent 绑定”
- 后台却还像“全局运行时主备切换”

管理员无法直观看到：

- 系统到底有哪些可选模型
- 哪个是默认模型
- 哪些 Agent 正在使用哪个模型
- 某个系统模型被禁用后会影响多少 Agent

### 1.2 24 小时活跃用户统计口径错误

当前后台仪表盘里：

- `online_users_5m` 使用 Redis presence `last_seen` 统计最近 5 分钟活跃用户
- `active_users_24h` 却使用数据库 `UserLoginEvent` 去统计“最近 24 小时登录过的用户”

这两个指标统计口径不同：

- 5 分钟在线：按访问 / 心跳
- 24 小时活跃：按登录事件

因此出现了明显错误观感：

- 24 小时活跃用户有时会比 5 分钟在线用户更少

这不是前端展示 bug，而是**后台指标定义 bug**。

---

## 2. 设计原则

### 2.1 以“系统模型目录”为正式心智

后台正式模型管理入口不再围绕“主模型 / 备模型”展开，而是围绕“系统模型目录”展开。

### 2.2 对旧配置完全兼容

现有 `agent_service` runtime config 里已经有：

- `llm_model / openai_api_base / openai_api_key`
- `llm_model_secondary / openai_api_base_secondary / openai_api_key_secondary`
- `agent_model_catalog`

新方案要优先兼容已有配置：

- 如果 `agent_model_catalog` 非空，直接以它为准
- 如果它为空，则从现有主 / 备模型配置自动生成一个兼容模型目录

### 2.3 管理要比配置更重要

后台第一阶段不追求做成“全系统控制台”，但要把模型相关的管理能力补齐：

- 新增 / 编辑 / 启用 / 禁用 / 设默认模型
- 测试连接
- 引用统计
- 风险提示
- 审计记录

### 2.4 指标口径要统一

对于“活跃用户”，后台必须统一采用访问 presence 体系，而不是一部分按访问，一部分按登录。

---

## 3. 方案对比

### 方案 A：继续在 OpsPage 上打补丁

做法：

- 保留现有主模型 / 备模型区域
- 再在下面塞一个系统模型目录列表

优点：

- 改动最小
- 上线快

缺点：

- 新旧两套模型心智同时存在
- 管理员会困惑到底该改哪一处
- 页面会越来越难维护

**结论：不推荐作为正式方案。**

### 方案 B：新增独立“模型管理”后台模块

做法：

- 从 `OpsPage` 中拆出独立的“模型管理”页面
- 所有系统模型池管理都放在这个页面
- `OpsPage` 中原有主备模型配置区降级为兼容来源展示，不再是正式入口

优点：

- 与前台 Agent 独立选模完全一致
- 后台心智清晰
- 后续扩到 3 / 4 / 5 个系统模型也自然
- 更适合叠加健康、风险、告警、统计能力

缺点：

- 需要新增后台路由、页面和专用接口

**结论：推荐方案。**

### 方案 C：一步做成完整系统治理控制台

做法：

- 模型管理、服务健康、队列、告警、运行策略、系统审计全部一起重构

优点：

- 最完整

缺点：

- 第一阶段过重
- 风险大，周期长

**结论：放到第二阶段，不适合现在。**

---

## 4. 推荐方案总览

采用**方案 B**：

- 新增独立后台模块：`模型管理`
- 保留旧的 `OpsPage`，但将其模型配置角色降级为“兼容来源 / 运行时遗留配置”
- 同时修正仪表盘活跃用户统计逻辑

---

## 5. 模型管理后台设计

## 5.1 页面结构

新增后台一级页面：

- `模型管理`

建议路由：

- `admin/frontend/src/router.ts` 新增 `/models`

页面分为四个区块。

### 区块 A：系统模型目录

这是页面主体，展示所有系统模型。

字段建议：

- 展示名称 `label`
- 稳定 ID `id`
- Provider 类型
- Base URL
- 模型名 `model`
- 启用状态 `enabled`
- 默认状态 `is_default`
- 排序 `sort_order`
- 被多少 Agent 引用
- 当前健康状态

支持操作：

- 新增系统模型
- 编辑系统模型
- 启用 / 禁用
- 设置默认模型
- 调整顺序
- 复制为新模型
- 测试连接

### 区块 B：兼容来源 / 旧配置映射

展示当前 runtime config 里的 legacy 配置：

- `llm_failover_mode`
- 主模型
- 备模型

用途：

- 让管理员知道历史配置仍然存在
- 但明确标注“这是兼容来源，不是正式模型管理入口”

当 `agent_model_catalog` 已存在时：

- 这个区块只读显示
- 不鼓励继续从这里管理系统模型

### 区块 C：引用统计与影响分析

每个模型需要有清晰的引用与风险信息：

- 被多少 Agent 绑定
- 其中多少是活跃 Agent
- 多少 Agent 当前在 fallback
- 若禁用该模型，影响多少 Agent

若管理员要禁用或删除一个模型：

- 弹窗确认影响范围
- 明确提示：
  - 会影响多少 Agent
  - 是否自动回退到默认模型

### 区块 D：模型健康与告警

第一阶段不做复杂监控，但要具备最基本的后台可见性：

- 最近测试连接结果
- 最近 LLM fallback 告警
- 最近失败次数
- 最近一次修改时间
- 最近修改人

---

## 5.2 后台接口设计

### agent_service 专用接口

目前后台通过 `/admin/runtime-config` 泛型接口管理 runtime config，这对模型目录太粗了。建议新增模型专用接口：

- `GET /admin/model-catalog`
- `POST /admin/model-catalog`
- `PUT /admin/model-catalog/{id}`
- `POST /admin/model-catalog/{id}/enable`
- `POST /admin/model-catalog/{id}/disable`
- `POST /admin/model-catalog/{id}/set-default`
- `POST /admin/model-catalog/reorder`
- `POST /admin/model-catalog/test`
- `GET /admin/model-catalog/usage`

这些接口底层仍可写入 runtime config 的 `agent_model_catalog`，但对上层屏蔽内部结构细节。

### admin backend 代理接口

在 `admin/backend/app/routers/ops.py` 中新增对应代理接口，例如：

- `GET /admin/ops/model-catalog`
- `POST /admin/ops/model-catalog`
- `PUT /admin/ops/model-catalog/{id}`
- `POST /admin/ops/model-catalog/{id}/enable`
- `POST /admin/ops/model-catalog/{id}/disable`
- `POST /admin/ops/model-catalog/{id}/set-default`
- `POST /admin/ops/model-catalog/reorder`
- `POST /admin/ops/model-catalog/test`
- `GET /admin/ops/model-catalog/usage`

并统一写入审计日志。

---

## 5.3 与现有多模型机制的兼容

### 目录来源规则

系统模型目录按以下优先级解析：

1. `agent_model_catalog` 非空
   - 直接作为系统模型池
2. 否则
   - 自动从当前 runtime config 的主 / 备模型生成兼容目录

兼容目录可生成：

- `legacy-primary`
- `legacy-secondary`

这样做的结果是：

- 现有线上两套模型可立即作为后台模型目录展示
- 不要求先迁移所有配置

### 对已存在 Agent 的兼容

旧 Agent 如果没有显式绑定系统模型：

- 运行时默认归属当前默认系统模型

如果 Agent 绑定的系统模型后来被禁用或删除：

- 运行时自动回退默认模型
- 后台管理页与前台 Agent 信息页都应能看到 fallback warning

---

## 6. 24 小时活跃用户修正设计

## 6.1 根因

当前：

- `online_users_5m`：Redis ZSET `presence:users:last_seen`
- `active_users_24h`：数据库 `UserLoginEvent`

这是两个完全不同的统计口径。

## 6.2 正确口径

“24 小时活跃用户”应定义为：

- **过去 24 小时至少访问过一次、被 presence last_seen 记录到的用户数**

因此应改为：

- `online_users_5m` = 最近 5 分钟 last_seen 用户数
- `active_users_24h` = 最近 24 小时 last_seen 用户数
- `login_events_24h` 继续保留，但单独表示“登录事件次数”

## 6.3 实现方式

沿用已有 Redis presence 键：

- `presence:users:last_seen`

新增一个函数：

- `_active_users_24h()`

与 `_online_users_5m()` 同一套口径：

- 清理超出保留期的数据
- 统计最近 24 小时 ZSET score 在范围内的用户数

## 6.4 仪表盘展示文案

建议微调展示文案，避免歧义：

- `5分钟在线用户`
- `24小时访问活跃用户`
- `24小时登录事件`

这样管理员能立刻看懂三者不是一个指标。

---

## 7. 推荐顺手增强的后台能力

为了让后台“更好管理”，第一阶段顺手补这几项最值：

### 7.1 模型测试连接

新增 / 编辑模型时支持测试连接：

- 校验 `base_url / api_key / model`
- 返回耗时、错误信息、是否成功

### 7.2 模型引用统计

对每个系统模型显示：

- 绑定 Agent 数
- 活跃 Agent 数
- fallback Agent 数

### 7.3 失效模型清单

增加一个“需要管理员处理”的列表：

- 哪些 Agent 正在使用失效模型
- 当前是否已 fallback

### 7.4 模型配置审计

模型相关操作全部记录：

- 谁改的
- 改了什么字段
- 从什么改到什么
- 是否影响 Agent fallback

---

## 8. 第一阶段明确不做

为了控制范围，以下不纳入这次：

- 不做完整服务监控中心
- 不做 Prometheus / Grafana 级别观测
- 不做用户自定义模型审核流
- 不做模型成本结算
- 不做复杂实验参数后台

---

## 9. 分阶段落地建议

### Phase 1：模型管理模块成型

- 新增后台模型管理页
- 新增模型目录专用接口
- 兼容读取旧主 / 备配置
- 支持增删改启停默认排序测试连接
- 支持引用统计与风险确认
- 修复 24 小时活跃用户指标口径

### Phase 2：运维增强

- fallback 事件面板
- 模型失败告警集中展示
- 失效模型批量修复助手

### Phase 3：后台整体治理

- 服务健康
- 队列运行状态
- 策略中心
- 系统总览

---

## 10. 最终结论

这次后台改造的核心不是把旧的“主模型 / 备模型”页面再堆厚一点，而是把模型能力升级为一个正式的**系统模型目录管理模块**：

- 与前台 Agent 独立选模一致
- 对旧 runtime config 完全兼容
- 能支撑 2、3、4、5 个系统模型
- 能在模型变更时给出风险提示和自动回退
- 同时修正后台活跃用户指标口径，让后台数据真正可信

这是当前阶段最稳、最清晰、也最适合 AgentTalk 后续继续扩展的方案。
