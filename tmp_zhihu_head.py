#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知乎热榜爬虫 - AgentTalk 项目版
爬取知乎热榜 Top N 问题及高赞回答，写入项目 PostgreSQL（通过 Go 后端内部 API）。
同时在本地按日期归档一份 JSON 备份。
"""

import asyncio
import os
from playwright.async_api import async_playwright
import json
import re
import random
import httpx
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# ==========================================
# 配置（支持环境变量覆盖，适配 Docker Compose）
# ==========================================
MAX_HOTSPOTS = int(os.getenv("ZHIHU_MAX_HOTSPOTS", "20"))  # 爬取热榜前N个问题
MAX_ANSWERS_PER_HOTSPOT = int(
    os.getenv("ZHIHU_MAX_ANSWERS", "10")
)  # 每个问题最多N个回答

# Go 后端内部 API 地址
# 本地开发: http://localhost:8080
# Docker Compose 内部: http://backend:8080
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# 本地备份目录（每日一个文件，方便回溯）
ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "./hotspots_data"))

# Cookie 配置（留空，用户自己填写）
ZHIHU_COOKIE = "_xsrf=aXpZ78NTIpFlIaVVdp764hdp8oRBlL8x; _zap=5a680557-9387-4a39-a24b-5952a8c4daf2; d_c0=JmEUhbkFfRuPTl2_OdSfJmiSh8MdkWvoQAQ=|1765026576; __zse_ck=004_7GybqSsBxGRpUSwzWNpGDvSMmYuEmnLT=WG40=1NobYlcCMpDFL666j8VAkeIBGqyP/WI8cZfD2tNam/PPhqE5HHlxk6nDSxy/dd0ODbrMfy86j9mg=tjO4t8ZQ6l4jX-94oxqNTMSgA6mpycBzbGs5CWIhn3YAFunmSnvu8uqI4l+s9HDj9k+lcB0G9AeEFtKDw6VQLXF4l6ZaEKVr3hhFMBFWWhU4xTIyzsG9sxjHndAh/6E2uEzqqqExCzpwau; captcha_session_v2=2|1:0|10:1771640408|18:captcha_session_v2|88:ZG1BSHZuUmU1VWpHUWVmbU5QWlhSNk5kN1hpc3VGeG9xS3pieVZPT3FPWTVjd3llcnI2TzFsNUF5Wlh6RWJudA==|84e06da40670e679dae171884a4b7713ed3064fb5ce49a1a91de4d20e1ffc4f4; SESSIONID=xXMh0PgSeyGtVodYVJfOSi9onr0lVmlGsn6ZocJbwk8; JOID=UVwcC02GL8BdMaJ6Vq57nhs_GelH-XqMOwT1EATmUYooacgZAtU1Vj8zqHZZCobpenWeDHitN7bg6_oJRFHuiRc=; osd=VVoRAk-CKc1UM6Z8W6d5mh0yEOtD_3eFOQDzHQ3kVYwlYModBNg8VDs1pX9bDoDkc3eaCnWkNbLm5vMLQFfjgBU=; Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1771640410; HMACCOUNT=56A1D1E862E4DE41; DATE=1771640410151; crystal=U2FsdGVkX19iVxGcsKk4K+M5cNHA8VeudXrab5Clj98vZmqL5FDMWYJzt7aye6Er+DgdHF/yv5Nj1X5hpLUx+1O41WkMixHz6k/14UkJCZnelwtsLuGI47y+Lt2v+lmW3uZ5aY3Fyq9nB/hGBRwWDgHqfnJCP7la5eR7vDVY8n6qf6lh2wd+y64Yn1ThULglW7CDqTI4I3yL7JQq8UhZ68dCutzym9pPtv/gah0NYwUjYgM+184uVi3mvFx76gm6; __snaker__id=iUUboltTIypcj5nk; cmci9xde=U2FsdGVkX19dihJGMBJpr6uGCJ8wnJGiXfGrVafECNn8rf9xK50VUTR49Bdl4PnnklQ3rHgu2t454uAOYTXIjg==; pmck9xge=U2FsdGVkX1+oxzEZorsGtI878T+oV7qHWi3VY+RJwpU=; assva6=U2FsdGVkX19gSZQXancavz44NpAAcYsaLYNS6hZJ1mI=; assva5=U2FsdGVkX1+bxGXjXEVKZ8o2hyHPS9SBoXDflk2GjxEh9flNhNSt0lpNhFVT4s55xM5sJRLoN1+L5zIfqP1kzg==; vmce9xdq=U2FsdGVkX19iNsIDP4EGskaWb64WeTMwqQgYMqlwopqbgXveCll5F65oRQSsILgGpkucljpBEQhYARP5C67qSVA3uFMU5BivtU2y3uBzOkXAR/ggapTf+6ulig+8X7EHqPOZDhU85ycmLjVOWzT/VoGRGMivq+isRsVwC3XQAAk=; gdxidpyhxdE=K%2BlSHqJXyMiuzW%2B08UjJ%2BtgprvUrlYgCC2GP%5Cf%2FyDsWlTGbD9zEG%2BpXgkhMIN4KbncjdUtCuxW5vLW7%5C9eOtJIDYC2YgwXl6vOm470gKJtvepCvlxGnWDwUkH6R0yEdRHeR1pqCjhaLtnlYAsHoOr%2FPHTSaI%2B7bJwqmBqeygZy7w3xBR%3A1771641315836; q_c1=bf9c31e97c774d1082004a8d24c79beb|1771640425000|1771640425000; Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1771640429; BEC=d6322fc1daba6406210e61eaa4ec5a7a; z_c0=2|1:0|10:1771640429|4:z_c0|92:Mi4xODRZaU1nQUFBQUFtWVJTRnVRVjlHeVlBQUFCZ0FsVk5hV1NHYWdDR1c3R25KSjVTNWxDTjd2QW82N0ZJSi1DX2ZB|101c81b11209a8ecd2f527aab6800a7f1d9efa76e3abfec42b6be4c1a4fc3781"  # 填入你的知乎 Cookie

# 延迟配置
DELAY_MULTIPLIER = 1.0

# ==========================================
# 工具函数
# ==========================================


async def delay(low, high=None):
    """随机延迟"""
    if high is None:
        high = low
    await asyncio.sleep(random.uniform(low * DELAY_MULTIPLIER, high * DELAY_MULTIPLIER))


async def delay_fixed(seconds):
    """固定延迟"""
    await asyncio.sleep(seconds * DELAY_MULTIPLIER)


async def extract_full_question_html(page) -> str:
    """提取知乎问题完整正文（展开后），并移除“显示全部”按钮节点。"""
    try:
        await page.wait_for_selector(".QuestionRichText", timeout=5000)

        # 若存在“显示全部”按钮，先展开避免抓到折叠摘要。
        more_btn = page.locator(
            ".QuestionRichText .QuestionRichText-more, .QuestionRichText-more"
        ).first
        if await more_btn.count() > 0:
            try:
                await more_btn.click(timeout=2000)
                await delay_fixed(0.5)
            except Exception:
                pass

        content_elem = page.locator(".QuestionRichText").first

        # 克隆节点后删除按钮和脚本等噪声标签，保留正文 HTML。
        question_content = await content_elem.evaluate(
            """
            (node) => {
              const cloned = node.cloneNode(true);
              cloned.querySelectorAll('button,script,style,.QuestionRichText-more').forEach(el => el.remove());
              return cloned.innerHTML;
            }
            """
        )

        # 兜底移除仍残留的“显示全部”文本。
        question_content = re.sub(r"\s*显示全部\s*", "", question_content or "")
        return question_content.strip()
    except Exception:
        return ""


def parse_cookie_string(cookie_str, domain=".zhihu.com"):
    """将cookie字符串转换为Playwright格式"""
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            parts = item.split("=", 1)
            if len(parts) == 2:
                name, value = parts
                cookies.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": domain,
                        "path": "/",
                    }
                )
    return cookies


# ==========================================
# 核心爬取逻辑
# ==========================================


async def get_hot_questions(page) -> List[Dict]:
    """
    从知乎热榜获取问题ID列表

    返回格式（按设计文档 hotspots 表结构）：
    [
        {
            "source": "zhihu",
            "source_id": "123456",  # 知乎问题ID
            "title": "问题标题",
            "url": "https://www.zhihu.com/question/123456",
            "rank": 1,  # 热榜排名
            "heat": "2.3亿浏览", # 热度值
            "hotspot_date": "2026-03-05",
            "crawled_at": "2026-03-05T10:30:00"
        },
        ...
    ]
    """
    print("\n🔥 正在获取知乎热榜...")
    try:
        await page.goto(
            "https://www.zhihu.com/hot", wait_until="domcontentloaded", timeout=30000
        )
        await delay_fixed(3)

        hotspots = []
        today = datetime.now().strftime("%Y-%m-%d")
        crawled_time = datetime.now().isoformat()

        # 滚动加载更多内容
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await delay_fixed(2)

        # 获取热榜条目
        items = await page.locator(".HotItem").all()

        for idx, item in enumerate(items[:MAX_HOTSPOTS], 1):
            try:
                # 获取问题链接和ID
                link = await item.locator('a[href*="/question/"]').first.get_attribute(
                    "href"
                )
                if not link or "/question/" not in link:
                    continue

                match = re.search(r"/question/(\d+)", link)
                if not match:
                    continue

                question_id = match.group(1)

                # 获取标题
                title = await item.locator(".HotItem-title").first.inner_text()
                # 获取热度（如果有）
                heat = ""
                try:
                    heat = await item.locator(".HotItem-metrics").first.inner_text()
                except:
                    pass

                hotspot = {
                    "source": "zhihu",
                    "source_id": question_id,
                    "title": title.strip(),
                    "content": "",  # 详细内容在后续步骤中获取
                    "url": f"https://www.zhihu.com/question/{question_id}",
                    "rank": idx,
                    "heat": heat.strip(),
                    "status": "pending",
                    "question_id": None,
                    "hotspot_date": today,
                    "crawled_at": crawled_time,
                    "processed_at": None,
                }

                hotspots.append(hotspot)
                print(f"   [{idx}] {title[:40]}...")

            except Exception as e:
                print(f"   ⚠️ 解析热榜条目 {idx} 失败: {e}")
                continue

        print(f"✅ 成功获取 {len(hotspots)} 个热榜问题")
        return hotspots

    except Exception as e:
        print(f"❌ 获取热榜失败: {e}")
        return []


async def scrape_question_and_answers(
    page, context, hotspot: Dict, max_answers: int = 10
) -> Dict:
    """
    爬取单个问题的详细信息和回答

    参数：
        hotspot: 热点基础信息（来自热榜列表）
        max_answers: 最多爬取多少个回答

    返回：
        {
            "hotspot": {...},  # 更新后的热点信息（包含content）
            "answers": [...]   # 回答列表（按设计文档 hotspot_answers 表结构）
        }
    """
    question_id = hotspot["source_id"]
    print(f"\n📄 [{hotspot['rank']}] 正在爬取问题: {hotspot['title'][:30]}...")

    all_answers = []

    async def handle_response(response):
        """监听API响应，捕获回答数据"""
        nonlocal all_answers

        # 只处理JSON响应
        if "application/json" not in response.headers.get("content-type", ""):
            return

        # 捕获回答内容API
        if (
            f"/questions/{question_id}/feeds" in response.url
            or f"/questions/{question_id}/answers" in response.url
        ):
            try:
                data = await response.json()
                items = data.get("data", [])

                for item in items:
                    answer_item = item.get("target", item)
                    if answer_item.get("type") != "answer":
                        continue

                    # 提取回答信息（保留原始HTML内容）
                    answer_id = str(answer_item.get("id", ""))
                    author = answer_item.get("author", {})

                    # 获取完整内容（不清洗HTML，保留原始格式）
                    content = answer_item.get("content", answer_item.get("excerpt", ""))

                    # 创建时间
                    created_time = answer_item.get("created_time", 0)
                    created_date = ""
                    if created_time:
                        try:
                            created_date = datetime.fromtimestamp(
                                created_time
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            created_date = str(created_time)

                    answer_data = {
                        # 关联字段
                        "hotspot_id": None,  # 爬虫阶段暂不填，入库时关联
                        # 作者信息
                        "author_name": author.get("name", "匿名用户"),
                        "author_url": (
                            f"https://www.zhihu.com/people/{author.get('url_token', '')}"
                            if author.get("url_token")
                            else ""
                        ),
                        # 回答内容（保留原始HTML）
                        "content": content,
                        # 统计数据
                        "upvote_count": answer_item.get("voteup_count", 0),
                        "comment_count": answer_item.get("comment_count", 0),
                        # 排名与来源
                        "rank": len(all_answers) + 1,
                        "zhihu_answer_id": answer_id,
                        # 额外信息（不在表中，但有助于调试）
                        "created_time": created_time,
                        "created_date": created_date,
                        "updated_time": answer_item.get("updated_time", 0),
                    }

                    # 去重
                    if not any(a["zhihu_answer_id"] == answer_id for a in all_answers):
                        all_answers.append(answer_data)

            except Exception as e:
                print(f"   ⚠️ 解析回答API失败: {e}")

    page.on("response", handle_response)

    try:
        # 访问问题页面
        await page.goto(
            f"https://www.zhihu.com/question/{question_id}",
            wait_until="domcontentloaded",
            timeout=45000,
        )
        await delay_fixed(2)

        # 获取问题详细描述
        try:
            # 获取展开后的完整 HTML 内容（移除“显示全部”等按钮节点）
            question_content = await extract_full_question_html(page)
            hotspot["content"] = question_content
            print(f"   ✅ 获取问题描述: {len(question_content)} 字符")
        except:
            print(f"   ⚠️ 未找到问题描述")
            hotspot["content"] = ""

        # 等待回答加载
        print(f"   ⏳ 等待回答加载...")
        await delay_fixed(2)

        # 滚动加载回答
        scroll_count = 0
        last_count = 0
        no_new_count = 0

        while len(all_answers) < max_answers and scroll_count < 20:
            # 滚动
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await delay(2, 4)

            current_count = len(all_answers)
            if current_count == last_count:
                no_new_count += 1
                if no_new_count >= 3:  # 连续3次没新回答，停止
                    break
            else:
                no_new_count = 0
                last_count = current_count

            scroll_count += 1

            if scroll_count % 5 == 0:
                print(f"   🔄 已滚动 {scroll_count} 次，当前回答数: {len(all_answers)}")

        print(f"   ✅ 成功爬取 {len(all_answers)} 个回答")

    except Exception as e:
        print(f"   ❌ 爬取失败: {e}")

    page.remove_listener("response", handle_response)

    # 只返回前max_answers个回答
    final_answers = all_answers[:max_answers]

    return {"hotspot": hotspot, "answers": final_answers}


# ==========================================
# 写入后端 API
# ==========================================


async def push_hotspots_to_backend(
    client: httpx.AsyncClient, results: List[Dict]
) -> Dict[str, int]:
    """
    批量写入热点到 Go 后端，返回 {source_id: db_id} 的映射
    （知乎爬虫需要 db_id 才能继续写回答）
    """
    hotspot_payloads = [r["hotspot"] for r in results]

    # 批量写入热点
    try:
        resp = await client.post(
            f"{BACKEND_URL}/internal/hotspots/batch",
            json={"hotspots": hotspot_payloads},
            timeout=30,
        )
        body = resp.json()
        print(f"\n📤 热点写入结果: {body.get('message', '未知')}")
    except Exception as e:
        print(f"\n❌ 批量写入热点失败: {e}")
        return {}

    # 查询刚写入的热点，拿到数据库 ID
    source_ids = {r["hotspot"]["source_id"] for r in results}
    date = (
        results[0]["hotspot"]["hotspot_date"]
        if results
        else datetime.now().strftime("%Y-%m-%d")
    )

    id_map: Dict[str, int] = {}
    try:
        resp = await client.get(
            f"{BACKEND_URL}/internal/hotspots",
            params={"source": "zhihu", "date": date},
            timeout=15,
        )
        for item in resp.json().get("data", []):
            if item["source_id"] in source_ids:
                id_map[item["source_id"]] = item["id"]
    except Exception as e:
        print(f"   ⚠️ 查询热点 ID 失败: {e}")

    return id_map


async def push_answers_to_backend(
    client: httpx.AsyncClient, db_id: int, answers: List[Dict]
):
    """为单个知乎热点批量写入原始回答"""
    if not answers:
        return

    cleaned = [
        {
            "author_name": a["author_name"],
            "author_url": a.get("author_url", ""),
            "content": a["content"],
            "upvote_count": a.get("upvote_count", 0),
            "comment_count": a.get("comment_count", 0),
            "rank": a.get("rank", 0),
            "zhihu_answer_id": a["zhihu_answer_id"],
        }
        for a in answers
    ]

    try:
        resp = await client.post(
            f"{BACKEND_URL}/internal/hotspots/{db_id}/answers",
            json={"answers": cleaned},
            timeout=30,
        )
        body = resp.json()
        print(f"   📤 回答写入: {body.get('message', '未知')}")
    except Exception as e:
        print(f"   ❌ 写入回答失败 (hotspot_id={db_id}): {e}")


# ==========================================
# 每日本地归档（备份用，按日期一个文件）
# ==========================================


def archive_results(results: List[Dict]):
    """
    本地备份，每天一个归档文件，路径: hotspots_data/zhihu/2026-03-05.json
    同一天多次运行会合并追加（去重）。
    """
    if not results:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    archive_path = ARCHIVE_DIR / "zhihu" / f"{today}.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # 加载已有归档
    existing: List[Dict] = []
    if archive_path.exists():
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                existing = json.load(f).get("data", [])
        except Exception:
            existing = []

    # 去重合并（以 source_id 为 key）
    existing_ids = {r["hotspot"]["source_id"] for r in existing}
    merged = existing + [
        r for r in results if r["hotspot"]["source_id"] not in existing_ids
    ]

    data = {
        "crawl_info": {
            "source": "zhihu",
            "date": today,
            "last_updated": datetime.now().isoformat(),
            "total_hotspots": len(merged),
            "total_answers": sum(len(r["answers"]) for r in merged),
        },
        "data": merged,
    }

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 本地归档: {archive_path} （共 {len(merged)} 条热点）")


# ==========================================
# 主流程
# ==========================================


async def crawl_zhihu_hotspots():
    """主爬取流程"""
    if not ZHIHU_COOKIE or ZHIHU_COOKIE.strip() == "":
        print("❌ 错误: 请先在脚本中填写 ZHIHU_COOKIE")
        return

    print("=" * 60)
    print(" " * 10 + "🚀 知乎热榜爬虫 - AgentTalk 集成版")
    print("=" * 60)
    print(f"📋 配置: {MAX_HOTSPOTS} 个热榜问题 × {MAX_ANSWERS_PER_HOTSPOT} 个回答")
    print(f"🌐 后端 API: {BACKEND_URL}")
    print(f"💾 本地归档: {ARCHIVE_DIR}/zhihu/<date>.json")
    print("=" * 60)

    async with async_playwright() as p:
        print("\n🌐 启动浏览器...")
        browser = await p.chromium.launch(
            headless=os.getenv("ZHIHU_HEADLESS", "true").lower() == "true",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        await context.add_cookies(parse_cookie_string(ZHIHU_COOKIE))
        page = await context.new_page()

        try:
            # 第1步：爬取热榜列表
            hotspots = await get_hot_questions(page)
            if not hotspots:
                print("\n❌ 未获取到热榜数据，请检查 Cookie 是否有效")
                return

            # 第2步：逐个爬取问题详情和回答
            final_results: List[Dict] = []
            for idx, hotspot in enumerate(hotspots, 1):
                print(f"\n{'='*60}")
                print(f"进度: [{idx}/{len(hotspots)}]")
                print(f"{'='*60}")

                result = await scrape_question_and_answers(
                    page, context, hotspot, max_answers=MAX_ANSWERS_PER_HOTSPOT
                )
                final_results.append(result)

                if idx < len(hotspots):
                    wait_time = random.randint(5, 10)
                    print(f"\n💤 休息 {wait_time} 秒...")
                    await asyncio.sleep(wait_time)

        finally:
            await browser.close()

        # 第3步：写入后端数据库（浏览器已关闭，用 httpx 单独发请求）
        if final_results:
            print("\n\n📤 正在写入后端数据库...")
            async with httpx.AsyncClient() as client:
                # 3a. 批量写入热点，拿到数据库 ID 映射
                id_map = await push_hotspots_to_backend(client, final_results)

                # 3b. 逐个写入知乎原始回答
                for result in final_results:
                    source_id = result["hotspot"]["source_id"]
                    db_id = id_map.get(source_id)
                    if db_id and result["answers"]:
                        print(f"\n   写入回答: {result['hotspot']['title'][:30]}...")
                        await push_answers_to_backend(client, db_id, result["answers"])

    # 第4步：本地每日归档备份
    archive_results(final_results)

    # 打印统计
    total_answers = sum(len(r["answers"]) for r in final_results)
    print("\n" + "=" * 60)
    print("✅ 爬取完成！")
    print(f"   热榜问题: {len(final_results)} 个")
    print(f"   回答总数: {total_answers} 个")
    print("=" * 60)


# ==========================================
# 入口
# ==========================================


async def main():
    await crawl_zhihu_hotspots()


if __name__ == "__main__":
    asyncio.run(main())
