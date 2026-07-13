#!/bin/zsh
# 一键启动后台定时收集（每小时自动收集一次）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_DIR/collector.log"
PID_FILE="$PROJECT_DIR/collector.pid"

cd "$PROJECT_DIR"

# 检查是否已经在运行
if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
    echo "定时收集器已经在运行 (PID: $(cat "$PID_FILE"))"
    echo "日志: $LOG_FILE"
    exit 0
fi

# 启动后台收集
nohup python3 "$PROJECT_DIR/main.py" > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

echo "定时收集器已启动 (PID: $PID)"
echo "日志: $LOG_FILE"
echo "每小时自动收集一次，按 Ctrl+C 不会中断"
