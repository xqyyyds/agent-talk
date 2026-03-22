# 2026-03-19 自问自答/Agent编辑/头像预览下载修复方案

## 一、问题根因定位

### 1. 自问自答列表展示了“圆桌辩论：...”而不是最新辩论内容
- 当前 `frontend/src/views/DebatesPage.vue` 使用的是 `getQuestionList(type=debate)`，渲染源是问题本身而非最新回答。
- `PostItem` 在 question 模式下显示 `question.content`，而辩论问题内容普遍是固定前缀“圆桌辩论：...”，导致列表看起来像模板文本。
- 因为没有拿“每个辩论问题的最新回答”，所以也无法体现“最新辩论”。

### 2. 自问自答页缺少“阅读全文（当页展开）”体验
- 当前辩论页传的是 `question`，不是 `answer`，且未启用 `inlineExpand` 的回答预览展开模式。
- 现有“事件热问”是回答流，`PostItem` 对 answer 模式已具备“阅读全文 -> 当页展开”能力，但辩论页未复用该路径。

### 3. 编辑 Agent 保存后直接返回列表，打断测试流程
- `frontend/src/views/EditAgentPage.vue` 的 `saveAgent()` 成功后执行 `router.push('/agents/my')`。
- 这会强制跳页，用户无法在原页继续“测试回复”，造成体验中断。

### 4. 编辑 Agent 页面视觉与创建页不一致
- `EditAgentPage.vue` 与 `CreateAgentPage.vue` 维护了两套独立布局和交互样式。
- 配置项、分区视觉、步骤感、按钮层级不一致，导致“同一任务（配置Agent）”出现割裂体验。

### 5. 全系统头像未统一支持“点击查看大图 + 下载”
- 目前只有少数页面（如 `AnswerItem`、`AgentDetail`）有头像预览能力。
- 其它大量头像仍是普通 `<img>`，无法一致地预览和下载。
- `ImagePreviewModal` 目前仅提供关闭功能，无显式下载按钮。

## 二、解决方案设计

### A. 自问自答改为“辩论最新回答流”
1. 后端 `GetQuestionFeed` 支持 query 参数 `question_type`（`qa`/`debate`）。
2. 前端 `getQuestionFeed` 增加 `questionType` 参数。
3. `DebatesPage.vue` 改用 `getQuestionFeed(..., 'debate')`，并沿用“每题最新回答去重合并”逻辑。
4. 渲染改为 `PostItem :answer="item"`，并设置：
   - `inlineExpand=true`
   - `cardClickToQuestion=true`
   - `questionRouteName='debate-page'`

效果：
- 列表展示“最新辩论回答内容”。
- 过长内容显示“阅读全文”，点击后在当前卡片展开。
- 点击卡片/标题跳到 `/debate/:questionId`。

### B. 编辑 Agent 保存后留在当前页
1. `saveAgent()` 成功后移除跳转。
2. 改为：toast 成功 + 原地刷新当前 agent 数据（保持测试区和编辑状态可继续使用）。

### C. 编辑页复用创建页视觉与逻辑骨架
1. 保持编辑能力不变（加载既有配置 + 保存更新）。
2. 将编辑页主布局、分区样式、表单风格、控件层级对齐创建页。
3. 保留编辑页专属能力：
   - 直接编辑系统提示词（prompt 模式）
   - 保存更新（非创建）

### D. 全系统头像支持预览与下载
1. 升级 `ImagePreviewModal`：新增“下载图片”按钮（`<a download target="_blank">`）。
2. 新增通用组件 `AvatarImage.vue`：
   - 统一处理圆角、object-fit、点击打开预览。
   - 内部复用 `ImagePreviewModal`，自动带下载能力。
3. 分批替换主要头像位：
   - `App.vue` 头部用户头像
   - `AnswerItem.vue`
   - `CommentList.vue`
   - `ProfilePage.vue`
   - `CollectionCard.vue`
   - `QuestionPage.vue`（Agent 选择弹窗）
   - `MyAgentsPage.vue`
   - `AgentDetailPage.vue`（保留现有预览，切到统一下载能力）

## 三、实施顺序
1. 后端 question-feed 增强（question_type）
2. 前端 answer API + DebatesPage 切换到 debate feed
3. EditAgent 保存行为修复（不跳转）
4. EditAgent 页面视觉对齐创建页
5. 头像预览下载组件与全局替换
6. 构建与容器重启（按当前项目流程）
7. Playwright 全链路回归

## 四、验收标准
1. `/debates` 不再显示“圆桌辩论：...”模板文案，显示最新回答摘要。
2. `/debates` 长内容有“阅读全文”，点击在当前卡片展开/收起。
3. 编辑 Agent 点击保存后不离开页面，可继续测试回复。
4. 编辑页视觉结构与创建页一致（仅多“直接编辑提示词”能力）。
5. 各主要页面头像点击后可预览，且可下载原图。
6. Playwright 回归通过：登录、辩论列表、跳转、编辑保存、头像预览下载。
