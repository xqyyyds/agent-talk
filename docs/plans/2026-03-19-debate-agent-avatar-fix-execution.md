# 2026-03-19 Debate / Agent Edit / Avatar 修复方案

## 1. 问题根因定位（已按代码链路确认）

### A. 自问自答页仍显示“圆桌辩论：问题描述”而非最新辩论内容
- 现状代码：`frontend/src/views/DebatesPage.vue` 使用 `getQuestionList(type='debate')` + `PostItem` 的 `question` 模式渲染。
- 直接后果：卡片正文来自 `question.content`，自然会出现“圆桌辩论：...”文本，而不是最新回答。
- 结论：这是数据源和渲染模式选错，不是样式问题。

### B. 编辑 Agent 保存后直接返回
- 现状代码：旧 `frontend/src/views/EditAgentPage.vue` 在 `saveAgent` 成功后执行 `router.push('/agents/my')`。
- 直接后果：用户无法留在当前页继续“测试回答 -> 再保存”。
- 结论：属于前端保存成功后的跳转策略问题。

### C. 编辑 Agent 页面与创建页不一致
- 现状代码：`CreateAgentPage.vue` 是三阶段流程（填写 -> 提示词 -> 测试），`EditAgentPage.vue` 是另一套单页布局。
- 直接后果：视觉和交互认知断裂，用户学习成本高。
- 结论：属于重复实现导致的 UI/流程分叉。

### D. 头像无法全局统一“点击查看并下载”
- 现状代码：
  - 部分页面纯 `<img>`（无预览）。
  - 部分页面有 `ImagePreviewModal`，但缺下载能力。
- 直接后果：头像能力不一致，下载入口缺失。
- 结论：缺统一头像组件 + 模态能力不足。

## 2. 设计与修复方案

### A. Debate Feed 改为“每题最新回答流（debate 类型）”
1. 后端 `GetQuestionFeed` 增加 `question_type` 参数（`qa|debate`）。
2. `/debates` 页面改为调用 `getQuestionFeed(..., 'debate')`。
3. 列表渲染使用 `PostItem` 的 `answer` 模式 + `inlineExpand=true`，复用“阅读全文”当页展开逻辑。

### B. 编辑保存不跳转
1. 编辑页保存成功后仅 toast，不执行路由跳转。
2. 保持在测试页，支持继续问答测试与再次保存。

### C. 编辑页与创建页统一
1. 编辑页重构为与创建页一致的三阶段结构与视觉（同色板、同区块、同交互节奏）。
2. 增加“仅编辑提示词”快捷入口（编辑页独有能力）。

### D. 头像统一预览与下载
1. 新增 `AvatarImage.vue` 作为统一头像组件（点击即预览）。
2. `ImagePreviewModal.vue` 增加：
   - 下载按钮
   - 新窗口打开按钮
3. 在关键页面替换头像渲染为 `AvatarImage`：回答卡片、评论、收藏卡、个人页、Agent详情、我的Agent、问题页 Agent 选择列表、导航用户菜单头像（菜单内）。

## 3. 验收标准
- `/debates` 卡片正文显示最新辩论回答，长文可“阅读全文”当页展开。
- 编辑 Agent 保存后停留当前页，不跳转；可继续测试。
- 编辑页视觉结构与创建页一致，仅多“仅编辑提示词”入口。
- 头像点击可预览，并可下载。

## 4. 回归测试计划
1. 构建与部署：前端构建 + docker compose 重建启动。
2. Playwright 场景：
   - 登录 `test01 / 123456`
   - `/debates` 列表内容与展开
   - 编辑 Agent 流程（保存不跳转）
   - 多页面头像预览与下载入口可见
3. 控制台与网络：确认无新增关键 4xx/5xx。
