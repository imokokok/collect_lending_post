"""币安广场 (Binance Square) 数据收集模块 - 使用 Playwright 搜索并拦截响应"""

import json
import time
from datetime import datetime, timezone
from config import (
    KEYWORDS,
    HIGH_INTENT_KEYWORDS,
    BINANCE_PRIORITY_KEYWORDS,
    MIN_RELEVANCE_SCORE,
    MAX_POST_AGE_DAYS,
)
from storage import filter_recent_posts


def _ensure_playwright():
    """确保 Playwright 已安装"""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("[Binance] Playwright 未安装，尝试安装...")
        import subprocess
        subprocess.run(["pip3", "install", "playwright"], check=True)
        subprocess.run(["python3", "-m", "playwright", "install", "chromium"], check=True)
        return True


def _score_relevance(text, title=""):
    """
    给币安广场帖子做相关性打分
    - 命中 HIGH_INTENT_KEYWORDS：+3 分
    - 命中普通 KEYWORDS：+1 分
    - 标题命中额外 +2 分
    """
    combined = f"{title} {text}".lower()
    score = 0
    high_hits = []
    normal_hits = []

    for kw in HIGH_INTENT_KEYWORDS:
        if kw.lower() in combined:
            score += 3
            high_hits.append(kw)

    for kw in KEYWORDS:
        if kw.lower() in combined and kw not in high_hits:
            score += 1
            normal_hits.append(kw)

    # 标题命中高价值词额外加分
    title_lower = title.lower()
    for kw in HIGH_INTENT_KEYWORDS:
        if kw.lower() in title_lower:
            score += 2

    high_hits = list(dict.fromkeys(high_hits))
    normal_hits = list(dict.fromkeys([n for n in normal_hits if n not in high_hits]))
    return score, high_hits, normal_hits


def _is_engagement_opportunity(vo, likes):
    """判断是否是可评论获客的高潜帖子"""
    # 币安广场 comments 字段不稳定，优先用点赞数+内容长度判断
    content = vo.get("content", "") or ""
    title = vo.get("title", "") or ""
    if len(content) < 30 and len(title) < 10:
        return False
    return likes > 3


def _format_post(vo, keyword):
    """格式化币安广场帖子"""
    card_type = vo.get("cardType", "")
    post_id = str(vo.get("id", ""))

    content = vo.get("content", "") or ""
    title = vo.get("title", "") or ""

    summary = content[:300] + "..." if len(content) > 300 else content
    author = vo.get("authorName", "")

    # 币安广场 `date` 字段是秒级时间戳；旧的 releaseDate/createTime 是毫秒级
    date_seconds = vo.get("date", 0)
    release_ms = vo.get("releaseDate", 0)
    create_ms = vo.get("createTime", 0)
    created_timestamp = None
    if date_seconds:
        created_timestamp = date_seconds
    elif release_ms:
        created_timestamp = release_ms / 1000
    elif create_ms:
        created_timestamp = create_ms / 1000

    stats = vo.get("stats", {}) or {}
    likes = stats.get("likeCount", 0) or vo.get("likeCount", 0)
    comments = stats.get("commentCount", 0) or vo.get("commentCount", 0)
    shares = stats.get("shareCount", 0) or vo.get("shareCount", 0)

    score, high_hits, normal_hits = _score_relevance(content, title)
    engagement = _is_engagement_opportunity(vo, likes)

    return {
        "source": "Binance Square",
        "id": post_id,
        "keyword": keyword,
        "card_type": card_type,
        "title": title,
        "text": summary,
        "author": author,
        "created_at": datetime.fromtimestamp(created_timestamp, tz=timezone.utc).isoformat() if created_timestamp else "",
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "url": f"https://www.binance.com/en/square/post/{post_id}" if post_id else "",
        "relevance_score": score,
        "high_intent_keywords": high_hits,
        "matched_keywords": normal_hits,
        "engagement_opportunity": engagement,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def collect():
    """收集币安广场上借贷协议风险管理相关帖子"""
    _ensure_playwright()
    from playwright.sync_api import sync_playwright

    all_posts = []
    seen_ids = set()
    skipped_count = 0
    old_count = 0

    # 只搜索精简后的高价值中文关键词（避免关键词过多导致运行时间过长）
    search_keywords = BINANCE_PRIORITY_KEYWORDS

    print("[Binance] 启动浏览器...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()

        # 访问首页建立 session
        print("[Binance] 访问币安广场首页...")
        try:
            page.goto("https://www.binance.com/en/square", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  [Binance] 首页加载超时（继续）: {e}")

        for keyword in search_keywords:
            try:
                print(f"[Binance] 搜索关键词: {keyword}")
                buzz_items = []

                def handle_response(response, kw=keyword):
                    nonlocal buzz_items
                    url = response.url
                    if "/bapi/composite/v2/friendly/pgc/feed/search/list" in url:
                        try:
                            data = response.json()
                            vos = data.get("data", {}).get("vos", [])
                            for vo in vos:
                                ct = vo.get("cardType", "")
                                if ct in ("BUZZ_SHORT", "BUZZ_LONG") and vo.get("content"):
                                    buzz_items.append(vo)
                        except Exception:
                            pass

                page.on("response", handle_response)

                # 带重试的搜索
                search_ok = False
                for attempt in range(3):
                    try:
                        search_url = f"https://www.binance.com/en/square/search?q={keyword}"
                        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(2500)

                        # 用搜索框触发搜索
                        try:
                            search_input = page.query_selector('input[placeholder*="earch"], input[placeholder*="搜索"]')
                            if search_input:
                                search_input.fill(keyword)
                                search_input.press("Enter")
                                page.wait_for_timeout(2500)
                        except Exception:
                            pass

                        # 滚动加载更多
                        for _ in range(1):
                            page.evaluate("window.scrollBy(0, 800)")
                            page.wait_for_timeout(800)

                        search_ok = True
                        break

                    except Exception as e:
                        print(f"  [Binance] 搜索 '{keyword}' 第 {attempt+1} 次尝试失败: {e}")
                        if attempt < 2:
                            page.wait_for_timeout(2000)
                        else:
                            print(f"  [Binance] 搜索 '{keyword}' 放弃")

                page.remove_listener("response", handle_response)

                if not search_ok:
                    continue

                keyword_posts = []
                for vo in buzz_items:
                    post_id = str(vo.get("id", ""))
                    if not post_id or post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)
                    keyword_posts.append(_format_post(vo, keyword))

                # 过滤 3 天前发布的帖子
                recent_posts = filter_recent_posts(keyword_posts, MAX_POST_AGE_DAYS)
                old_count += len(keyword_posts) - len(recent_posts)

                new_count = 0
                for post in recent_posts:
                    if post["relevance_score"] < MIN_RELEVANCE_SCORE:
                        skipped_count += 1
                        continue

                    all_posts.append(post)
                    new_count += 1

                print(f"  [Binance] '{keyword}' 获取 {len(buzz_items)} 条帖子，新增 {new_count} 条")
                time.sleep(0.7)

            except Exception as e:
                print(f"  [Binance] 关键词 '{keyword}' 处理异常，跳过: {e}")
                continue

        browser.close()

    # 按相关性和互动量综合排序
    all_posts.sort(key=lambda p: (p.get("relevance_score", 0), p.get("likes", 0)), reverse=True)

    print(f"[Binance] 共收集 {len(all_posts)} 条高相关帖子（过滤掉 {skipped_count} 条低相关，{old_count} 条超过 {MAX_POST_AGE_DAYS} 天）")
    return all_posts
