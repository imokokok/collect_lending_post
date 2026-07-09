"""主程序 - 定时收集借贷协议相关帖子"""

import os
import signal
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

from config import COLLECT_INTERVAL_HOURS
from collector_x import collect as collect_x
from collector_binance import collect as collect_binance
from storage import save_posts, generate_summary, cleanup_old_data


# 加载 .env 文件
load_dotenv()

running = True


def _signal_handler(sig, frame):
    global running
    print("\n[Main] 收到停止信号，正在退出...")
    running = False
    sys.exit(0)


def run_collection():
    """执行一次完整的收集流程"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*60}")
    print(f"  开始收集 - {now}")
    print(f"{'='*60}")

    all_posts = []

    # 收集 X 数据
    print("\n[1/2] 收集 X (Twitter) 数据...")
    try:
        x_posts = collect_x()
        save_posts(x_posts, source_label="x")
        all_posts.extend(x_posts)
    except Exception as e:
        print(f"[Main] X 收集异常: {e}")

    # 收集币安广场数据
    print("\n[2/2] 收集币安广场数据...")
    try:
        bs_posts = collect_binance()
        save_posts(bs_posts, source_label="binance")
        all_posts.extend(bs_posts)
    except Exception as e:
        print(f"[Main] 币安广场收集异常: {e}")

    # 生成汇总
    print("\n[汇总] 生成收集汇总...")
    generate_summary(all_posts)

    # 清理过期数据
    print("\n[清理] 检查过期数据...")
    cleanup_old_data()

    print(f"\n[Main] 本次收集完成，共 {len(all_posts)} 条")
    return all_posts


def main():
    global running

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    interval_seconds = COLLECT_INTERVAL_HOURS * 3600

    print(f"[Main] 借贷协议帖子收集器启动")
    print(f"[Main] 收集间隔: 每 {COLLECT_INTERVAL_HOURS} 小时")
    from config import RETENTION_DAYS
    print(f"[Main] 数据保留: {RETENTION_DAYS} 天")
    print(f"[Main] X 数据源: Twitter Syndication API (免费)")
    print(f"[Main] 币安广场: Playwright + API (免费)")
    print(f"[Main] 按 Ctrl+C 停止\n")

    # 首次立即执行
    run_collection()

    # 定时循环
    while running:
        print(f"\n[Main] 等待下次收集 ({COLLECT_INTERVAL_HOURS} 小时后)...")
        try:
            # 使用短间隔轮询，以便及时响应停止信号
            for _ in range(interval_seconds):
                if not running:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            break

        if running:
            run_collection()

    print("[Main] 已停止")


if __name__ == "__main__":
    main()
