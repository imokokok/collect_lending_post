#!/bin/zsh
# 停止后台定时收集器
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/collector.pid"

cd "$PROJECT_DIR"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo "已停止定时收集器 (PID: $PID)"
    else
        echo "收集器没有在运行"
    fi
    rm -f "$PID_FILE"
else
    echo "没有找到收集器进程"
fi
