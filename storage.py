"""数据存储、汇总和清理模块"""

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import DATA_DIR, RETENTION_DAYS


def _parse_created_at(created_at):
    """解析帖子发布时间，支持 ISO 格式、时间戳和 Twitter 格式"""
    if not created_at:
        return None
    if isinstance(created_at, (int, float)):
        return datetime.fromtimestamp(created_at, tz=timezone.utc)
    s = str(created_at).strip()
    dt = None
    # ISO 格式（如 2024-02-20T14:35:00+00:00）
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Twitter 格式（如 Wed Oct 12 12:00:00 +0000 2022）
    if dt is None:
        try:
            dt = datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            pass
    if dt is None:
        return None
    # 确保带时区，避免与 aware 的 cutoff 比较时报错
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def filter_recent_posts(posts, days):
    """只保留最近 N 天内发布的帖子"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for post in posts:
        dt = _parse_created_at(post.get("created_at"))
        if dt and dt >= cutoff:
            recent.append(post)
    return recent


def _ensure_data_dir():
    """确保数据目录存在"""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def _today_dir():
    """返回今天的数据目录路径"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(DATA_DIR, today)


def save_posts(posts, source_label=""):
    """保存收集到的帖子到按日期组织的 JSON 文件"""
    if not posts:
        print(f"[Storage] {source_label} 无数据需要保存")
        return

    _ensure_data_dir()
    day_dir = _today_dir()
    os.makedirs(day_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    filename = f"{source_label}_{timestamp}.json" if source_label else f"posts_{timestamp}.json"
    filepath = os.path.join(day_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"[Storage] 已保存 {len(posts)} 条数据到 {filepath}")


def _escape_html(text):
    """HTML 转义"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _topic_tags(post):
    """根据关键词给帖子打主题标签"""
    text = f"{post.get('title','')} {post.get('text','')} {' '.join(post.get('high_intent_keywords', []))} {' '.join(post.get('matched_keywords', []))}".lower()
    tags = []
    if any(k in text for k in ["liquidation", "清算", "爆仓", "清算价格", "爆仓价", "清算风险"]):
        tags.append("清算/爆仓")
    if any(k in text for k in ["oracle", "预言机", "价格偏差", "bad debt", "坏账", "insolvency", "喂价"]):
        tags.append("预言机/坏账")
    if any(k in text for k in ["collateral", "抵押", "position", "仓位", "ltv", "抵押率", "健康因子", "健康度", "health factor"]):
        tags.append("抵押/仓位")
    if any(k in text for k in ["leverage", "杠杆", "循环贷", "borrowing", "借款", "贷款", "lending strategy", "借贷策略", "deleverage", "去杠杆"]):
        tags.append("杠杆/策略")
    protocols = ["aave", "compound", "makerdao", "spark", "morpho", "radiant", "venus", "justlend", "benqi", "curve", "crvusd", "euler", "silo", "ajna", "kamino", "solend"]
    matched_protocols = [p.upper() for p in protocols if p in text]
    if matched_protocols:
        tags.append("/".join(matched_protocols[:2]))
    return tags if tags else ["综合讨论"]


def generate_summary(posts):
    """生成收集汇总 - 交互式 HTML 页面（含筛选、搜索、排序）"""
    if not posts:
        return "本次收集无数据。\n"

    x_posts = [p for p in posts if p["source"] == "X"]
    bs_posts = [p for p in posts if p["source"] == "Binance Square"]
    hot_posts = [p for p in posts if p.get("engagement_opportunity", False)]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 为每个帖子补充主题标签
    for p in posts:
        p["topic_tags"] = _topic_tags(p)

    posts_json = json.dumps(posts, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>借贷协议帖子收集汇总 - {now}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; color: #333; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; margin-bottom: 8px; }}
  .subtitle {{ color: #888; font-size: 14px; margin-bottom: 16px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
  .stat-card {{ background: #fff; border-radius: 10px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .stat-card .num {{ font-size: 26px; font-weight: bold; color: #e94560; display: block; }}
  .stat-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
  .tip {{ background: #e8f4ff; border-left: 4px solid #0f6efd; padding: 12px 16px; border-radius: 6px; margin: 16px 0; font-size: 14px; }}
  .tip strong {{ color: #0f6efd; }}
  .controls {{ background: #fff; border-radius: 10px; padding: 16px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .control-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }}
  .control-row:last-child {{ margin-bottom: 0; }}
  .control-label {{ font-size: 13px; color: #666; font-weight: 500; min-width: 60px; }}
  .btn {{ border: 1px solid #ddd; background: #fff; color: #555; padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
  .btn:hover {{ background: #f0f0f0; }}
  .btn.active {{ background: #e94560; color: #fff; border-color: #e94560; }}
  .btn.active:hover {{ background: #d63850; }}
  input[type="text"], select {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; min-width: 200px; }}
  input[type="text"]:focus, select:focus {{ outline: none; border-color: #0f6efd; }}
  .post-list {{ margin-top: 20px; }}
  .section-title {{ color: #16213e; margin: 28px 0 12px; font-size: 18px; }}
  .post-card {{ background: #fff; border-radius: 10px; padding: 16px 20px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: none; }}
  .post-card.visible {{ display: block; }}
  .post-card:hover {{ box-shadow: 0 3px 10px rgba(0,0,0,0.12); }}
  .post-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; flex-wrap: wrap; gap: 6px; }}
  .post-author {{ font-weight: 600; color: #16213e; font-size: 14px; }}
  .post-time {{ font-size: 11px; color: #999; }}
  .post-meta {{ font-size: 12px; color: #888; display: flex; gap: 12px; flex-wrap: wrap; }}
  .post-text {{ font-size: 14px; line-height: 1.6; color: #444; margin: 10px 0; }}
  .post-link {{ display: inline-block; margin-top: 8px; color: #0f6efd; text-decoration: none; font-size: 13px; font-weight: 500; }}
  .post-link:hover {{ text-decoration: underline; }}
  .source-x {{ border-left: 4px solid #1da1f2; }}
  .source-binance {{ border-left: 4px solid #f0b90b; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 5px; margin-top: 4px; }}
  .tag-x {{ background: #e8f5fe; color: #1da1f2; }}
  .tag-binance {{ background: #fff8e1; color: #b8860b; }}
  .tag-hot {{ background: #ffe8e8; color: #e94560; font-weight: bold; }}
  .tag-score {{ background: #f0f0f0; color: #555; }}
  .tag-topic {{ background: #e8f5e9; color: #2e7d32; }}
  .keywords {{ margin-top: 6px; font-size: 11px; color: #777; }}
  .keywords .kw {{ background: #f5f5f5; padding: 1px 6px; border-radius: 4px; margin-right: 4px; }}
  .empty {{ text-align: center; color: #999; padding: 40px; font-size: 14px; }}
  .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }}
</style>
</head>
<body>
<h1>借贷协议帖子收集汇总</h1>
<p class="subtitle">{now} · 数据保留 {RETENTION_DAYS} 天</p>

<div class="stat-grid">
  <div class="stat-card"><span class="num">{len(posts)}</span><div class="label">总帖数</div></div>
  <div class="stat-card"><span class="num">{len(x_posts)}</span><div class="label">X (Twitter)</div></div>
  <div class="stat-card"><span class="num">{len(bs_posts)}</span><div class="label">币安广场</div></div>
  <div class="stat-card"><span class="num">{len(hot_posts)}</span><div class="label">高潜获客</div></div>
</div>

<div class="tip">
  <strong>使用建议：</strong>优先查看带 <span class="tag tag-hot">高潜获客</span> 标记的帖子。下方可按来源、主题筛选，也可以按相关分/时间/互动排序。
</div>

<div class="controls">
  <div class="control-row">
    <span class="control-label">来源:</span>
    <button class="btn active" data-filter="source" data-value="all">全部</button>
    <button class="btn" data-filter="source" data-value="X">X</button>
    <button class="btn" data-filter="source" data-value="Binance Square">币安广场</button>
  </div>
  <div class="control-row">
    <span class="control-label">类型:</span>
    <button class="btn active" data-filter="hot" data-value="all">全部</button>
    <button class="btn" data-filter="hot" data-value="hot">高潜获客</button>
    <button class="btn" data-filter="hot" data-value="normal">普通相关</button>
  </div>
  <div class="control-row">
    <span class="control-label">主题:</span>
    <button class="btn active" data-filter="topic" data-value="all">全部</button>
    <button class="btn" data-filter="topic" data-value="清算/爆仓">清算/爆仓</button>
    <button class="btn" data-filter="topic" data-value="预言机/坏账">预言机/坏账</button>
    <button class="btn" data-filter="topic" data-value="抵押/仓位">抵押/仓位</button>
    <button class="btn" data-filter="topic" data-value="杠杆/策略">杠杆/策略</button>
  </div>
  <div class="control-row">
    <span class="control-label">搜索:</span>
    <input type="text" id="searchBox" placeholder="搜索作者、内容、关键词...">
    <span class="control-label">排序:</span>
    <select id="sortSelect">
      <option value="score">按相关分</option>
      <option value="time">按时间</option>
      <option value="engagement">按互动量</option>
    </select>
  </div>
</div>

<div id="postList" class="post-list"></div>
<div id="emptyState" class="empty" style="display:none">没有匹配的帖子</div>

<div class="footer">每小时自动收集 | 自动清理过期数据</div>

<script>
const allPosts = {posts_json};
let currentFilters = {{ source: 'all', hot: 'all', topic: 'all' }};
let currentSearch = '';
let currentSort = 'score';

function formatTime(iso) {{
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d) ? '' : d.toLocaleString('zh-CN', {{ month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit' }});
}}

function escapeHtml(text) {{
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}}

function renderPosts() {{
  let posts = allPosts.filter(p => {{
    if (currentFilters.source !== 'all' && p.source !== currentFilters.source) return false;
    if (currentFilters.hot === 'hot' && !p.engagement_opportunity) return false;
    if (currentFilters.hot === 'normal' && p.engagement_opportunity) return false;
    if (currentFilters.topic !== 'all' && !(p.topic_tags || []).includes(currentFilters.topic)) return false;
    if (currentSearch) {{
      const s = currentSearch.toLowerCase();
      const text = `${{p.author || ''}} ${{p.text || ''}} ${{p.title || ''}} ${{p.high_intent_keywords?.join(' ') || ''}} ${{p.matched_keywords?.join(' ') || ''}}`.toLowerCase();
      return text.includes(s);
    }}
    return true;
  }});

  posts.sort((a, b) => {{
    if (currentSort === 'score') return (b.relevance_score || 0) - (a.relevance_score || 0) || (b.likes || 0) - (a.likes || 0);
    if (currentSort === 'time') return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    if (currentSort === 'engagement') {{
      const ea = (a.likes || 0) + (a.replies || a.comments || 0) * 2 + (a.retweets || a.shares || 0);
      const eb = (b.likes || 0) + (b.replies || b.comments || 0) * 2 + (b.retweets || b.shares || 0);
      return eb - ea;
    }}
    return 0;
  }});

  const container = document.getElementById('postList');
  container.innerHTML = '';

  if (posts.length === 0) {{
    document.getElementById('emptyState').style.display = 'block';
    return;
  }}
  document.getElementById('emptyState').style.display = 'none';

  const hotCount = posts.filter(p => p.engagement_opportunity).length;
  if (hotCount > 0) {{
    container.innerHTML += `<h2 class="section-title">高潜获客机会（${{hotCount}} 条）</h2>`;
    posts.filter(p => p.engagement_opportunity).slice(0, 50).forEach(p => container.appendChild(createCard(p)));
  }}
  const normalCount = posts.length - hotCount;
  if (normalCount > 0) {{
    container.innerHTML += `<h2 class="section-title">其他相关帖子（${{normalCount}} 条）</h2>`;
    posts.filter(p => !p.engagement_opportunity).slice(0, 50).forEach(p => container.appendChild(createCard(p)));
  }}
}}

function createCard(p) {{
  const div = document.createElement('div');
  div.className = `post-card visible ${{p.source === 'X' ? 'source-x' : 'source-binance'}}`;

  const title = p.title ? `<strong>${{escapeHtml(p.title)}}</strong><br>` : '';
  const text = escapeHtml((p.text || '').slice(0, 240));
  const author = escapeHtml(p.author || '');
  const timeStr = formatTime(p.created_at);
  const likes = p.likes || 0;
  const rts = p.retweets || p.shares || 0;
  const replies = p.replies || p.comments || 0;
  const score = p.relevance_score || 0;
  const isHot = p.engagement_opportunity;
  const sourceTag = p.source === 'X' ? 'tag-x' : 'tag-binance';
  const topicTags = (p.topic_tags || []).map(t => `<span class="tag tag-topic">${{escapeHtml(t)}}</span>`).join('');
  const highKws = (p.high_intent_keywords || []).slice(0, 4).map(k => `<span class="kw">${{escapeHtml(k)}}</span>`).join('');
  const normalKws = (p.matched_keywords || []).slice(0, 2).map(k => `<span class="kw">${{escapeHtml(k)}}</span>`).join('');

  div.innerHTML = `
    <div class="post-header">
      <span class="post-author">@${{author}}</span>
      <span class="post-time">${{timeStr}}</span>
    </div>
    <div class="post-text">${{title}}${{text}}</div>
    <div class="post-meta">
      <span>❤ ${{likes}}</span>
      <span>🔁 ${{rts}}</span>
      <span>💬 ${{replies}}</span>
      <span>相关分 ${{score}}</span>
    </div>
    <div style="margin-top:8px">
      <span class="tag ${{sourceTag}}">${{p.source}}</span>
      ${{isHot ? '<span class="tag tag-hot">高潜获客</span>' : ''}}
      <span class="tag tag-score">相关分 ${{score}}</span>
      ${{topicTags}}
    </div>
    ${{highKws || normalKws ? `<div class="keywords">命中: ${{highKws}} ${{normalKws}}</div>` : ''}}
    <a class="post-link" href="${{escapeHtml(p.url || '')}}" target="_blank">查看原文 →</a>
  `;
  return div;
}}

document.querySelectorAll('.btn[data-filter]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const filter = btn.dataset.filter;
    const value = btn.dataset.value;
    currentFilters[filter] = value;
    document.querySelectorAll(`.btn[data-filter="${{filter}}"]`).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderPosts();
  }});
}});

document.getElementById('searchBox').addEventListener('input', e => {{
  currentSearch = e.target.value.trim();
  renderPosts();
}});

document.getElementById('sortSelect').addEventListener('change', e => {{
  currentSort = e.target.value;
  renderPosts();
}});

renderPosts();
</script>
</body>
</html>"""

    # 保存 HTML 汇总
    _ensure_data_dir()
    day_dir = _today_dir()
    os.makedirs(day_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")

    html_path = os.path.join(day_dir, f"summary_{timestamp}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Storage] HTML 汇总已保存到 {html_path}")

    # 更新固定路径的 latest.html，方便随时打开
    latest_path = os.path.join(DATA_DIR, "latest.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Storage] 最新汇总已更新到 {latest_path}")

    # 同时保存纯文本版
    txt_summary = _generate_text_summary(posts, x_posts, bs_posts, now)
    txt_path = os.path.join(day_dir, f"summary_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_summary)

    return html_content


def _generate_text_summary(posts, x_posts, bs_posts, now):
    """生成纯文本汇总"""
    lines = [
        f"{'='*60}",
        f"  借贷协议帖子收集汇总 - {now}",
        f"{'='*60}",
        f"",
        f"总计: {len(posts)} 条",
        f"  X (Twitter): {len(x_posts)} 条",
        f"  币安广场: {len(bs_posts)} 条",
        f"",
    ]
    if x_posts:
        lines.append("--- X (Twitter) 热门帖子 ---")
        sorted_x = sorted(x_posts, key=lambda p: p.get("likes", 0), reverse=True)
        for i, p in enumerate(sorted_x[:15], 1):
            lines.append(f"{i}. @{p.get('author','')}: {p['text'][:100]}")
            lines.append(f"   likes:{p.get('likes',0)} rts:{p.get('retweets',0)} | {p['url']}")
            lines.append("")
    if bs_posts:
        lines.append("--- 币安广场帖子 ---")
        sorted_bs = sorted(bs_posts, key=lambda p: p.get("likes", 0), reverse=True)
        for i, p in enumerate(sorted_bs[:15], 1):
            title = p.get("title", "")
            text_preview = title if title else p.get("text", "")[:100]
            lines.append(f"{i}. [{p.get('author','')}] {text_preview}")
            lines.append(f"   likes:{p.get('likes',0)} | {p.get('url','')}")
            lines.append("")
    return "\n".join(lines)


def cleanup_old_data():
    """清理超过保留天数的数据"""
    _ensure_data_dir()
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    removed = 0
    for entry in os.listdir(DATA_DIR):
        entry_path = os.path.join(DATA_DIR, entry)
        if not os.path.isdir(entry_path):
            continue
        # 目录名格式: YYYY-MM-DD
        if entry < cutoff_str:
            shutil.rmtree(entry_path)
            removed += 1
            print(f"[Storage] 已删除过期数据: {entry}")

    if removed == 0:
        print(f"[Storage] 无过期数据需要清理 (保留 {RETENTION_DAYS} 天)")
    else:
        print(f"[Storage] 共清理 {removed} 个过期目录")
