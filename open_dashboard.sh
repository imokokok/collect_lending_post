#!/bin/zsh
# 一键打开最新汇总页面（在浏览器中打开本地 HTML 文件）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LATEST_HTML="$PROJECT_DIR/data/latest.html"

if [ ! -f "$LATEST_HTML" ]; then
    echo "暂无汇总数据，先运行一次收集..."
    cd "$PROJECT_DIR"
    python3 -c "from main import run_collection; run_collection()"
fi

open "$LATEST_HTML"
echo "已打开最新汇总页面: $LATEST_HTML"
