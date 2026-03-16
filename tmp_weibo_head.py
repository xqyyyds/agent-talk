#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博热搜爬虫 - AgentTalk 集成版
爬取微博热搜榜 Top N，写入项目 PostgreSQL（通过 Go 后端内部 API）。
同时在本地按日期归档一份 JSON 备份。
"""

import asyncio
import os
from playwright.async_api import async_playwright
import json
import httpx
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import urllib.parse

# ==========================================
# 配置（支持环境变量覆盖，适配 Docker Compose）
# ==========================================
MAX_HOTSPOTS = int(os.getenv("WEIBO_MAX_HOTSPOTS", "20"))

# Go 后端内部 API 地址
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# 本地备份目录（每日一个文件）
ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "./hotspots_data"))

# Cookie 配置
WEIBO_COOKIE = "SUB=_2AkMe07Z1f8NxqwFRmvEcyWzmbYl0ygnEieKoj0euJRMxHRl-yT9kqhEYtRB6NVOYmpJIE76iaCFiGdSeT0qRO2f1ZfZ0"  # 填入你的微博 Cookie

# ==========================================
# 工具函数
# ==========================================


def parse_cookie_string(cookie_str, domain=".weibo.com"):
    """将cookie字符串转换为Playwright格式"""
    cookies = []
    if not cookie_str:
        return cookies

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


def archive_results(results: List[Dict]):
    """
    本地备份，每天一个归档文件: hotspots_data/weibo/2026-03-05.json
    同一天多次运行会合并追加（去重）。
    """
    if not results:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    archive_path = ARCHIVE_DIR / "weibo" / f"{today}.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # 加载已有归档合并（以 source_id=title 去重）
    existing: List[Dict] = []
    if archive_path.exists():
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                existing = json.load(f).get("data", [])
        except Exception:
            existing = []

    existing_ids = {r["hotspot"]["source_id"] for r in existing}
    merged = existing + [
        r for r in results if r["hotspot"]["source_id"] not in existing_ids
    ]

    data = {
        "crawl_info": {
            "source": "weibo",
            "date": today,
            "last_updated": datetime.now().isoformat(),
            "total_hotspots": len(merged),
        },
        "data": merged,
    }

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 本地归档: {archive_path} （共 {len(merged)} 条热搜）")


async def push_to_backend(results: List[Dict]):
    """将热点写入 Go 后端数据库"""
    payloads = [r["hotspot"] for r in results]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/internal/hotspots/batch",
                json={"hotspots": payloads},
                timeout=30,
            )
            body = resp.json()
            print(f"\n📤 后端写入结果: {body.get('message', '未知')}")
    except Exception as e:
        print(f"\n❌ 写入后端失败: {e}")
        print("   数据已保存到本地归档，下次运行时可手动补传")


# ==========================================
# 核心爬取逻辑
# ==========================================


async def get_hot_questions(context) -> List[Dict]:
    """
    通过微博最新侧边栏接口获取热搜榜单
    """
    print("\n🔥 正在获取微博热搜榜单...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
        }

        # 直接打最新最准的侧边栏接口
        response = await context.request.get(
            "https://weibo.com/ajax/side/hotSearch", headers=headers
        )

        if not response.ok:
            print(f"❌ 接口请求失败，状态码: {response.status}")
            return []

        data = await response.json()

        # 抛弃旧的 band_list，直接读取 realtime
        items = data.get("data", {}).get("realtime", [])

        if not items:
            print("⚠ 未获取到热搜列表，可能是 Cookie 失效被拦截")
            return []

        hotspots = []
        today = datetime.now().strftime("%Y-%m-%d")
        crawled_time = datetime.now().isoformat()

        for idx, item in enumerate(items[:MAX_HOTSPOTS], 1):
            # 提取词条和热度
            title = item.get("word") or item.get("note") or "未知热搜"
            heat = str(item.get("raw_hot") or item.get("num") or item.get("hot") or "")
            encoded_title = urllib.parse.quote(title)

            hotspot = {
                "source": "weibo",
                "source_id": title,
                "title": title,
                "content": "",
                "url": f"https://s.weibo.com/weibo?q={encoded_title}&xsort=hot",
                "rank": idx,
                "heat": heat,
                "status": "pending",
                "hotspot_date": today,
                "crawled_at": crawled_time,
            }

            formatted_item = {
                "hotspot": hotspot,
                "answers": [],
            }

            hotspots.append(formatted_item)
            print(f"   [{idx}] {title} (热度: {heat})")

        print(f"✅ 成功获取 {len(hotspots)} 个热搜词")
        return hotspots

    except Exception as e:
        print(f"❌ 获取热榜失败: {e}")
        return []


# ==========================================
# 主流程
# ==========================================


async def crawl_weibo_hotspots():
    if not WEIBO_COOKIE or WEIBO_COOKIE.strip() == "":
        print("❌ 错误: 请先在脚本中填写 WEIBO_COOKIE")
        return

    print("=" * 60)
    print(" " * 10 + "🚀 微博热搜爬虫 - AgentTalk 集成版")
    print("=" * 60)
    print(f"🌐 后端 API: {BACKEND_URL}")
    print(f"💾 本地归档: {ARCHIVE_DIR}/weibo/<date>.json")
    print("=" * 60)

    async with async_playwright() as p:
        print("\n🌐 启动浏览器环境...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
        )
        await context.add_cookies(parse_cookie_string(WEIBO_COOKIE))

        try:
            final_results = await get_hot_questions(context)
        finally:
            await browser.close()

    if not final_results:
        print("\n❌ 未获取到热搜数据，请检查 Cookie 是否有效")
        return

    # 写入后端数据库
    print("\n📤 正在写入后端数据库...")
    await push_to_backend(final_results)

    # 本地每日归档备份
    archive_results(final_results)

    print("\n" + "=" * 60)
    print(f"✅ 微博热搜爬取完成！共 {len(final_results)} 条")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(crawl_weibo_hotspots())
