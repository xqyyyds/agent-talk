#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热榜定时爬取调度器
每天北京时间 9:30 ~ 21:30，每小时执行一次知乎和微博爬取。

用法:
    python scheduler.py            # 前台运行
    nohup python scheduler.py &    # 后台运行（Linux）
    pythonw scheduler.py           # 后台运行（Windows）
"""

import asyncio
import subprocess
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

# 调度窗口（北京时间）
START_HOUR = 9
START_MINUTE = 30
END_HOUR = 21
END_MINUTE = 30

# 爬取间隔（秒）
INTERVAL_SECONDS = 3600  # 1小时

# 脚本路径
SCRIPT_DIR = Path(__file__).parent
ZHIHU_SCRIPT = SCRIPT_DIR / "zhihu_hotspot_crawler.py"
WEIBO_SCRIPT = SCRIPT_DIR / "weibo_spider.py"


def now_beijing() -> datetime:
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def in_schedule_window() -> bool:
    """判断当前北京时间是否在调度窗口内"""
    now = now_beijing()
    current_minutes = now.hour * 60 + now.minute
    start_minutes = START_HOUR * 60 + START_MINUTE
    end_minutes = END_HOUR * 60 + END_MINUTE
    return start_minutes <= current_minutes <= end_minutes


def seconds_until_next_window() -> int:
    """计算距离下一个调度窗口开始的秒数"""
    now = now_beijing()
    current_minutes = now.hour * 60 + now.minute
    start_minutes = START_HOUR * 60 + START_MINUTE

    if current_minutes < start_minutes:
        # 今天还没开始
        diff = (start_minutes - current_minutes) * 60 - now.second
    else:
        # 已过今天窗口，等明天
        diff = (24 * 60 - current_minutes + start_minutes) * 60 - now.second

    return max(diff, 60)


def run_crawler(script_path: Path, name: str):
    """运行爬虫脚本（子进程）"""
    if not script_path.exists():
        print(f"  ⚠️ 脚本不存在: {script_path}")
        return

    print(f"  🕷️ 启动 {name} 爬虫...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRIPT_DIR),
            timeout=600,  # 10分钟超时
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        if result.returncode == 0:
            print(f"  ✅ {name} 爬取完成")
        else:
            print(f"  ❌ {name} 爬取失败 (exit={result.returncode})")
            if result.stderr:
                print(f"     错误: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        print(f"  ⏰ {name} 爬取超时 (>10分钟)")
    except Exception as e:
        print(f"  ❌ {name} 运行异常: {e}")


def run_all_crawlers():
    """执行一轮爬取"""
    now = now_beijing()
    print(f"\n{'='*60}")
    print(f"⏰ [{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始本轮爬取")
    print(f"{'='*60}")

    run_crawler(WEIBO_SCRIPT, "微博热搜")
    run_crawler(ZHIHU_SCRIPT, "知乎热榜")

    print(f"\n✅ 本轮爬取结束，下一轮 {INTERVAL_SECONDS // 60} 分钟后")


def main():
    print("=" * 60)
    print("  🕐 热榜定时爬取调度器")
    print(
        f"  调度窗口: 北京时间 {START_HOUR}:{START_MINUTE:02d} ~ {END_HOUR}:{END_MINUTE:02d}"
    )
    print(f"  爬取间隔: {INTERVAL_SECONDS // 60} 分钟")
    print("=" * 60)

    while True:
        if in_schedule_window():
            run_all_crawlers()
            # 等待到下一轮
            import time

            time.sleep(INTERVAL_SECONDS)
        else:
            wait = seconds_until_next_window()
            now = now_beijing()
            print(
                f"\n💤 [{now.strftime('%H:%M')}] 不在调度窗口，"
                f"等待 {wait // 3600}h{(wait % 3600) // 60}m 后开始..."
            )
            import time

            time.sleep(min(wait, 300))  # 每5分钟重新检查一次


if __name__ == "__main__":
    main()
