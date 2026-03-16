# 知乎热榜爬虫使用说明

## 功能

专为 AgentTalk 项目设计的知乎热榜数据采集工具：

- ✅ 爬取知乎热榜 Top 20 问题
- ✅ 每个问题采集最多 10 个高赞回答
- ✅ **保留原始HTML格式**（方便前端渲染）
- ✅ 按设计文档 schema 结构存储
- ✅ 本地JSON文件存储（测试用）

## 快速开始

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 获取知乎 Cookie

1. 打开浏览器，访问 https://www.zhihu.com 并登录
2. 按 F12 打开开发者工具
3. 切换到 "Network" 标签
4. 刷新页面
5. 点击任意请求，找到 Request Headers 中的 `Cookie`
6. 复制完整的 Cookie 字符串

### 3. 配置脚本

打开 `zhihu_hotspot_crawler.py`，找到第27行：

```python
ZHIHU_COOKIE = ""  # 在这里填入你的知乎 Cookie
```

将复制的 Cookie 粘贴进去：

```python
ZHIHU_COOKIE = "你的完整Cookie字符串"
```

### 4. 运行爬虫

```bash
cd agent_service/scripts
python zhihu_hotspot_crawler.py
```

## 输出文件

爬取的数据保存在 `./hotspots_data/` 目录：

```
hotspots_data/
  ├── zhihu_hotspots_20260305_103000_progress.json  # 进度文件（每5题保存）
  └── zhihu_hotspots_20260305_104230_final.json     # 最终文件
```

## 数据格式

输出 JSON 的结构：

```json
{
  "crawl_info": {
    "source": "zhihu",
    "crawled_at": "2026-03-05T10:30:00",
    "total_hotspots": 20,
    "total_answers": 158,
    "config": {
      "max_hotspots": 20,
      "max_answers_per_hotspot": 10
    }
  },
  "data": [
    {
      "hotspot": {
        "source": "zhihu",
        "source_id": "123456",
        "title": "问题标题",
        "content": "<p>问题详细描述HTML</p>",
        "url": "https://www.zhihu.com/question/123456",
        "rank": 1,
        "heat": "2.3亿浏览",
        "status": "pending",
        "hotspot_date": "2026-03-05",
        "crawled_at": "2026-03-05T10:30:00"
      },
      "answers": [
        {
          "author_name": "张三",
          "author_url": "https://www.zhihu.com/people/xxx",
          "content": "<p>回答内容HTML（保留原始格式）</p>",
          "upvote_count": 12345,
          "comment_count": 678,
          "rank": 1,
          "zhihu_answer_id": "789012",
          "created_date": "2026-03-04 15:30:00"
        }
      ]
    }
  ]
}
```

### 关键特性

1. **原始HTML保留**：`content` 字段保存知乎的原始HTML，包含：
   - 段落标签 `<p>`
   - 图片 `<img>`
   - 代码块 `<pre>`
   - 链接 `<a>`
   - 格式化 `<b>`, `<i>`, `<u>` 等

2. **字段对齐设计文档**：数据结构完全对应 `agent-qa-design.md` 第十二章的 `hotspots` 和 `hotspot_answers` 表结构

3. **增量保存**：每处理5个问题自动保存进度，防止中断丢失数据

## 配置调整

在脚本顶部可以调整参数：

```python
MAX_HOTSPOTS = 20           # 爬取热榜前N个问题
MAX_ANSWERS_PER_HOTSPOT = 10  # 每个问题最多N个回答
OUTPUT_DIR = Path('./hotspots_data')  # 输出目录
DELAY_MULTIPLIER = 1.0      # 延迟倍率（增大可降低风控风险）
```

## 常见问题

### Q: 爬取失败或被拦截？

A: 增加延迟倍率：

```python
DELAY_MULTIPLIER = 2.0  # 所有延迟翻倍
```

### Q: Cookie 失效？

A: 重新登录知乎，获取新的 Cookie

### Q: 想要更多回答？

A: 修改 `MAX_ANSWERS_PER_HOTSPOT` 的值（注意：增加会延长爬取时间）

### Q: 为什么保留HTML而不是纯文本？

A: 
1. 保留原始格式，前端可以正常渲染（图片、代码块、链接等）
2. 后续入库时可以根据需要转换
3. 原始数据更灵活，方便调试和展示

## 下一步

爬虫测试成功后，根据设计文档第十二章：

1. 创建 Go 后端 API（`POST /internal/hotspots/batch`）
2. 修改爬虫脚本，改为调用 API 写入数据库
3. Agent Service 从数据库读取热点数据
4. 前端实现「知乎原答案 vs Agent 回答」对比展示

## 注意事项

⚠️ 本爬虫仅用于学习和测试，请遵守知乎使用条款
⚠️ 不要频繁运行，建议每天只爬取一次
⚠️ Cookie 包含敏感信息，不要提交到代码仓库
