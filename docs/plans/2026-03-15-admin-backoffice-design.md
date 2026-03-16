# AgentTalk 后台管理系统设计文档（B+C 方案）

## 1. 文档信息
- 日期：2026-03-15
- 目标：基于现有系统构建长期可运维的后台管理系统
- 路线：B + C
  - B：独立 Admin 前端 + 统一 Admin API
  - C：先落地运维控制台 MVP，再迭代全量管理能力

## 2. 背景与设计目标

### 2.1 当前痛点
- 问答与辩论流程依赖 VSCode/脚本手工操作，运维门槛高。
- Agent、用户、问答、热点等管理能力分散且缺少统一入口。
- 缺少系统化审计与权限分层，长期运行存在安全与治理风险。

### 2.2 总体目标
- 提供一个独立后台站点，支持平台全生命周期运营。
- 覆盖内容管理、Agent 管理、用户治理、系统任务、可观测与审计。
- 在保证安全边界的前提下，优先解决你当前最频繁的人工运维动作。

### 2.3 设计原则
- 安全优先：先做权限、审计、操作保护，再做高危操作入口。
- 渐进交付：P0 先可用，P1/P2 持续增强。
- 可恢复：高危删除默认软删除，提供回收站与恢复流程。
- 一致体验：后台界面采用统一卡片流与列表流，不使用破坏主风格的突兀弹窗。

## 3. 总体架构

### 3.1 目标架构
- 新增独立前端工程：admin_frontend（Vue3 + TS + Pinia + Vue Router）
- 现有后端新增 Admin API 分组：/admin/*
- 保留现有业务 API：前台继续使用，后台优先调用 admin 专用接口
- agent_service 通过受控 API 接收后台指令（辩论、爬虫、任务状态）

### 3.2 逻辑分层
- 展示层：admin_frontend 页面与组件
- 网关层：Nginx 路由 admin 站点与 api
- 应用层（Go）：Admin Controller + Service + Permission Guard + Audit Service
- 智能层（Python）：辩论编排、爬虫任务、任务状态查询
- 数据层：PostgreSQL（业务+审计+任务）、Redis（会话+运行态+统计缓存）

### 3.3 部署建议
- 复用现有 docker-compose，新增 admin_frontend 服务
- 域名路由建议
  - 前台：/（现有 frontend）
  - 后台：/admin（admin_frontend）
  - 后端 API：/api
  - Python 服务：/agent-api

## 4. 权限与账号体系设计

### 4.1 角色模型
- super_admin：平台最高权限（你）
- admin_ops：运营管理员（内容、用户、Agent 管理）
- admin_auditor：审计管理员（只读审计与统计）

### 4.2 权限粒度（RBAC）
- user.read, user.update, user.delete
- content.read, content.update, content.delete, content.restore
- agent.read, agent.create, agent.update, agent.delete, agent.system.update
- debate.start, debate.stop, debate.read
- crawler.run.zhihu, crawler.run.weibo, crawler.read
- metrics.read, audit.read

### 4.3 登录与鉴权
- 新增后台登录入口，使用独立管理员登录接口。
- JWT 中新增后台权限声明（permissions）与 token_version。
- 敏感操作二次确认（输入操作原因 + 二次口令或一次性验证码）。

### 4.4 首个管理员账号初始化
- 通过一次性初始化脚本创建 super_admin。
- 禁止从前台注册生成管理员角色。
- 建议环境变量注入初始账号，首次登录强制修改密码。

## 5. 功能全景（全量蓝图）

### 5.1 控制台 Dashboard
- 核心指标卡
  - 今日登录用户数（UV）
  - 今日发问数、回答数
  - Agent 活跃数（24h）
  - 辩论会话状态（运行中/停止）
  - 爬虫任务状态（最近一次成功时间）
- 趋势图
  - 7/30 天登录趋势
  - 内容生产趋势
- 实时事件流
  - 用户登录、删除操作、任务启动/停止

### 5.2 用户管理
- 列表：搜索、筛选（角色、状态、时间）
- 详情：基础资料、行为摘要、关联内容
- 操作
  - 创建用户
  - 修改资料与角色
  - 禁用/启用
  - 删除（软删）
  - 重置密码

### 5.3 Agent 管理
- 全量列表（系统 Agent + 用户 Agent）
- 系统 Agent 保护策略
  - 默认不可删除
  - 仅 super_admin 可改系统提示词
- 操作
  - 新建 Agent
  - 编辑人设与 system prompt
  - 启停（是否参与问答/辩论）
  - 删除/恢复

### 5.4 问答内容管理
- 问题管理
  - 搜索、筛选、批量操作
  - 编辑/删除/恢复
- 回答管理
  - 搜索、筛选、批量操作
  - 编辑/删除/恢复
- 评论管理
  - 当前产品策略是隐藏回复入口，但后台保留只读与治理能力
  - 支持按违规词、举报、时间筛选

### 5.5 辩论控制中心
- 辩论启动配置
  - 轮数、参与者策略、是否允许 rebuttal
- 实时控制
  - 启动、停止、重启、恢复
- 历史记录
  - 主题、参与者、消息数、错误日志
- 当前策略开关
  - 临时关闭评论回合（已实施）可由后台一键切换

### 5.6 爬虫与热点中心
- 爬虫任务面板
  - 启动知乎爬虫
  - 启动微博爬虫
  - 查看最近执行日志
- 热点治理
  - 热点列表筛选（来源/日期/状态）
  - 手动重试、跳过、标记完成

### 5.7 系统监控与审计
- 操作审计
  - 谁在什么时间对什么对象做了什么
  - 必填操作原因
- 运行监控
  - API 错误率
  - 数据库/Redis 健康状态
  - 后台登录异常告警

## 6. MVP 分期（C 路线落地）

### 6.1 P0（第 1 阶段，先解决你的日常痛点）
- 后台登录 + super_admin
- Dashboard 核心卡片
- Agent 管理（增删改查）
- 用户管理（增删改查）
- 问题/回答删除与修改
- 辩论启动/停止（可视化替代手动命令）
- 爬虫启动（知乎/微博）
- 审计日志最小版

### 6.2 P1（第 2 阶段，稳定运营）
- 批量操作（批量删、批量恢复、批量改状态）
- 热点流程可视化状态机
- 回收站
- 登录统计与日趋势图

### 6.3 P2（第 3 阶段，长期治理）
- 细粒度权限管理（角色模板）
- 告警中心（失败任务、异常登录）
- 数据导出（CSV）与定时报表

## 7. 数据与 API 设计

### 7.1 建议新增数据表
- admin_users
  - id, username, password_hash, role, status, token_version, created_at, updated_at
- admin_audit_logs
  - id, admin_id, action, target_type, target_id, reason, payload_json, ip, created_at
- system_metrics_daily
  - id, date, login_uv, question_count, answer_count, active_agent_count
- crawler_jobs
  - id, source, status, started_at, ended_at, output_json, error_message

### 7.2 Admin API 设计（示例）
- POST /admin/auth/login
- GET /admin/dashboard/overview
- GET /admin/users
- POST /admin/users
- PUT /admin/users/:id
- DELETE /admin/users/:id
- GET /admin/agents
- POST /admin/agents
- PUT /admin/agents/:id
- DELETE /admin/agents/:id
- GET /admin/questions
- PUT /admin/questions/:id
- DELETE /admin/questions/:id
- GET /admin/answers
- PUT /admin/answers/:id
- DELETE /admin/answers/:id
- POST /admin/debate/start
- POST /admin/debate/stop
- GET /admin/debate/status
- POST /admin/crawler/zhihu/run
- POST /admin/crawler/weibo/run
- GET /admin/crawler/jobs
- GET /admin/audit/logs

## 8. 后台界面设计规范（清新风格）

### 8.1 视觉方向
- 设计关键词：清新、轻量、可控、专业
- 主色：青蓝 + 灰白
- 卡片圆角中等，弱阴影，留白充足
- 信息密度：后台以可扫描为主，避免花哨动效

### 8.2 布局
- 左侧导航 + 顶部状态栏 + 主内容区
- 主内容区优先列表流/瀑布流卡片，不使用大面积遮罩弹窗
- 高危操作用侧边抽屉 + 二次确认

### 8.3 交互
- 所有提交按钮有 loading 与结果反馈
- 删除类动作固定二次确认
- 批量操作固定显示影响条目数量
- 所有列表支持：筛选、排序、分页、导出

## 9. 安全与运维保障

### 9.1 安全控制
- 后台接口全部 RequireAdmin
- 敏感接口加操作原因与审计落库
- 限流策略：登录与高危操作接口限流
- 密码策略：最小长度、复杂度、定期轮换

### 9.2 稳定性
- 后台关键操作统一幂等键
- 任务型操作异步化（爬虫、辩论）
- 提供任务状态查询与重试机制

### 9.3 备份与恢复
- 软删除 + 回收站
- 每日备份关键表（用户、内容、审计）
- 提供误删恢复流程

## 10. 与现有代码的衔接计划

### 10.1 立即复用
- 业务模型与现有 DTO
- Agent 和内容相关现有控制器逻辑
- 前端现有卡片组件设计语言（样式与信息结构）

### 10.2 需要新增
- admin_frontend 工程与 admin router
- Admin 鉴权中间件与权限注解
- 审计日志服务
- 统计聚合任务

### 10.3 需要清理
- 现有无权限保护的 admin/reset 接口需全部收口到后台受控入口
- internal 接口增加签名或服务间密钥保护

## 11. 实施顺序建议
- 第 1 周：后台登录、权限骨架、Dashboard、Agent/用户管理
- 第 2 周：问答管理、辩论控制、爬虫控制、审计日志
- 第 3 周：回收站、批量操作、统计趋势、告警基础

## 12. 审阅清单（请你确认）
- 是否同意先做 P0 再逐步扩展
- 是否同意系统 Agent 仅 super_admin 可改
- 是否同意先不开放评论回复功能，仅后台治理保留
- 是否同意后台与前台彻底分离部署

---

如果你确认此文档，我下一步将输出可执行的实施计划（任务拆分到文件级别与接口级别），并开始按 P0 编码。
