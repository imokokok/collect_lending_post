"""X (Twitter) 数据收集模块 - 使用免费 Syndication API"""

import re
import json
import time
import requests
from datetime import datetime, timezone
from config import X_ACCOUNTS, KEYWORDS, HIGH_INTENT_KEYWORDS, MIN_RELEVANCE_SCORE


def _fetch_timeline(screen_name):
    """通过 Syndication API 获取用户 Timeline（带重试和限速保护）"""
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{screen_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html",
    }

    content = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt + 1
                print(f"  [X] 获取 @{screen_name} 被限流 (429)，等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"  [X] 获取 @{screen_name} 失败: {resp.status_code}")
                return []
            content = resp.text
            break
        except Exception as e:
            print(f"  [X] 获取 @{screen_name} 异常: {e}")
            if attempt < 2:
                time.sleep(1)
            else:
                return []

    if content is None:
        return []

    # 从 HTML 中提取嵌入的 JSON 数据
    scripts = re.findall(r'<script[^>]*>\s*(\{.*?\})\s*</script>', content, re.DOTALL)
    for script_content in scripts:
        if '"tweet"' not in script_content or len(script_content) < 1000:
            continue
        try:
            data = json.loads(script_content)
            entries = data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
            return entries
        except json.JSONDecodeError:
            continue
    return []


def _parse_tweet(entry, screen_name):
    """解析推文条目"""
    tweet = entry.get("content", {}).get("tweet", {})
    if not tweet:
        return None

    tweet_id = tweet.get("id_str", "")
    if not tweet_id:
        return None

    full_text = tweet.get("full_text", "")
    user = tweet.get("user", {})

    return {
        "source": "X",
        "id": tweet_id,
        "account": f"@{screen_name}",
        "author": user.get("screen_name", screen_name),
        "text": full_text,
        "created_at": tweet.get("created_at", ""),
        "likes": tweet.get("favorite_count", 0),
        "retweets": tweet.get("retweet_count", 0),
        "replies": tweet.get("reply_count", 0),
        "url": f"https://x.com/{screen_name}/status/{tweet_id}",
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def _score_relevance(text):
    """
    给推文做相关性打分
    - 命中 HIGH_INTENT_KEYWORDS：+3 分
    - 命中普通 KEYWORDS：+1 分
    - 返回 (分数, 命中的高价值词列表, 命中的普通词列表)
    """
    text_lower = text.lower()
    score = 0
    high_hits = []
    normal_hits = []

    for kw in HIGH_INTENT_KEYWORDS:
        if kw.lower() in text_lower:
            score += 3
            high_hits.append(kw)

    for kw in KEYWORDS:
        if kw.lower() in text_lower and kw not in high_hits:
            if kw.lower() in text_lower:
                score += 1
                normal_hits.append(kw)

    # 去重
    high_hits = list(dict.fromkeys(high_hits))
    normal_hits = list(dict.fromkeys([n for n in normal_hits if n not in high_hits]))
    return score, high_hits, normal_hits


def _is_engagement_opportunity(post):
    """
    判断是否是可评论获客的高潜帖子
    条件：非纯公告、有一定互动（回复数>0 或 点赞>5）
    """
    replies = post.get("replies", 0) or 0
    likes = post.get("likes", 0) or 0
    text = post.get("text", "")
    # 过滤掉只发链接/公告、没人讨论的帖子
    if len(text) < 30:
        return False
    return replies > 0 or likes > 5


def collect():
    """收集 X 上借贷协议风险管理相关推文（免费，无需 API Key）"""
    all_posts = []
    seen_ids = set()
    skipped_count = 0

    for screen_name in X_ACCOUNTS:
        print(f"[X] 获取 @{screen_name} 的 Timeline...")
        entries = _fetch_timeline(screen_name)

        for entry in entries:
            if entry.get("type") != "tweet":
                continue

            post = _parse_tweet(entry, screen_name)
            if not post or post["id"] in seen_ids:
                continue
            seen_ids.add(post["id"])

            score, high_hits, normal_hits = _score_relevance(post["text"])
            if score < MIN_RELEVANCE_SCORE:
                skipped_count += 1
                continue

            post["relevance_score"] = score
            post["high_intent_keywords"] = high_hits
            post["matched_keywords"] = normal_hits
            post["engagement_opportunity"] = _is_engagement_opportunity(post)
            all_posts.append(post)

        # Syndication API 容易触发 429，保持较大请求间隔
        time.sleep(3.0)

    # 按相关性和互动量综合排序
    all_posts.sort(key=lambda p: (p.get("relevance_score", 0), p.get("likes", 0)), reverse=True)

    print(f"[X] 共收集 {len(all_posts)} 条高相关推文（过滤掉 {skipped_count} 条低相关）")
    return all_posts
