"""
AgentTalk 一键测试脚本

用法:
    python scripts/test_qa.py              # 默认处理 5 个未处理的热点
    python scripts/test_qa.py -n 10        # 处理 10 个
    python scripts/test_qa.py -s zhihu     # 只处理知乎热点
    python scripts/test_qa.py -s weibo     # 只处理微博热点
    python scripts/test_qa.py --status     # 仅查看当前状态
    python scripts/test_qa.py --stop       # 停止运行中的会话
"""

import argparse
import sys
import time
import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8001"


def api(method: str, path: str, body: dict | None = None) -> dict:
    """发请求到 Agent Service"""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            err = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            err = {}
        return {"error": e.code, "detail": err.get("detail", raw or str(e))}
    except urllib.error.URLError as e:
        return {"error": "连接失败", "detail": str(e.reason)}


def print_status(status: dict):
    """打印当前问答状态"""
    if "error" in status:
        print(f"  ❌ 获取状态失败: {status['detail']}")
        return

    s = status.get("status", "unknown")
    cur = status.get("current_cycle", 0)
    total = status.get("total_cycles", 0)
    icon = "🟢" if s == "running" else "⚪"
    print(f"  {icon} 状态: {s}  |  进度: {cur}/{total}")

    agents = status.get("agents_status") or []
    if agents:
        print(f"  📋 Agent 数量: {len(agents)}")

    logs = status.get("logs") or []
    if logs:
        print(f"  📝 最近日志:")
        for log in logs[-5:]:
            print(f"     {log}")


def cmd_status():
    """查看状态"""
    print("\n📊 当前问答状态\n" + "─" * 40)
    status = api("GET", "/qa/status")
    print_status(status)

    print("\n📦 已处理热点\n" + "─" * 40)
    processed = api("GET", "/qa/processed-hotspots")
    if "error" not in processed:
        data = processed.get("data", {})
        total = data.get("total", 0)
        hotspots = data.get("hotspots", [])
        print(f"  已处理: {total} 个热点")
        if hotspots:
            for h in hotspots[-10:]:
                print(f"    • {h}")
            if total > 10:
                print(f"    ... 还有 {total - 10} 个")
    print()


def cmd_stop():
    """停止会话"""
    print("\n⏹️  停止问答会话...")
    result = api("POST", "/qa/stop")
    if "error" in result:
        print(f"  ⚠️  {result['detail']}")
    else:
        print(f"  ✅ {result.get('message', '已停止')}")
    print()


def cmd_start(cycle_count: int, source: str | None):
    """启动问答"""
    # 1. 先检查服务是否可达
    print("\n🔍 检查服务状态...\n" + "─" * 40)
    status = api("GET", "/qa/status")
    if "error" in status and status["error"] == "连接失败":
        print("  ❌ Agent Service 不可达，请先启动: docker compose up -d")
        sys.exit(1)

    if status.get("status") == "running":
        print("  ⚠️  已有问答会话在运行中")
        print_status(status)
        print("\n  如需停止: python scripts/test_qa.py --stop")
        sys.exit(0)

    # 2. 启动问答
    desc = f"{cycle_count} 个热点"
    if source:
        desc += f"（仅 {source}）"

    print(f"\n🚀 启动问答: {desc}\n" + "─" * 40)

    body = {"cycle_count": cycle_count}
    if source:
        body["source"] = source

    result = api("POST", "/qa/start", body)
    if "error" in result:
        print(f"  ❌ 启动失败: {result['detail']}")
        sys.exit(1)

    data = result.get("data", {})
    print(f"  ✅ {result.get('message', '已启动')}")
    print(f"  📋 间隔模式: {data.get('interval_mode', 'dev')}")
    print(f"  📋 热点来源: {data.get('source', '全部')}")

    # 3. 轮询状态
    print(f"\n⏳ 后台处理中... (Ctrl+C 退出监控，不会停止后台任务)\n" + "─" * 40)
    try:
        while True:
            time.sleep(5)
            status = api("GET", "/qa/status")
            if "error" in status:
                continue

            s = status.get("status", "unknown")
            cur = status.get("current_cycle", 0)
            total = status.get("total_cycles", 0)

            logs = status.get("logs") or []
            latest = logs[-1] if logs else ""

            bar_len = 30
            filled = int(bar_len * cur / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            pct = int(100 * cur / total) if total > 0 else 0

            print(
                f"\r  [{bar}] {pct}% ({cur}/{total})  {latest[:60]}", end="", flush=True
            )

            if s != "running":
                print(f"\n\n  ✅ 问答会话完成！共处理 {cur} 个热点")
                break
    except KeyboardInterrupt:
        print("\n\n  ℹ️  已退出监控。后台任务仍在继续运行。")
        print("  查看状态: python scripts/test_qa.py --status")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="AgentTalk 一键测试 - 快速启动自动问答",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/test_qa.py              处理 5 个热点（快速测试）
  python scripts/test_qa.py -n 20        处理 20 个热点
  python scripts/test_qa.py -s zhihu     只处理知乎热点
  python scripts/test_qa.py --status     查看当前运行状态
  python scripts/test_qa.py --stop       停止当前会话
        """,
    )
    parser.add_argument(
        "-n", "--count", type=int, default=5, help="处理热点数量（默认 5）"
    )
    parser.add_argument(
        "-s", "--source", type=str, choices=["zhihu", "weibo"], help="只处理指定来源"
    )
    parser.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument("--stop", action="store_true", help="停止运行中的会话")

    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.stop:
        cmd_stop()
    else:
        cmd_start(args.count, args.source)


if __name__ == "__main__":
    main()
