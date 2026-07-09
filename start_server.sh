#!/bin/zsh
# 一键启动本地 Web 服务器并自动打开浏览器
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8080

cd "$PROJECT_DIR"

# 检查端口是否被占用
if lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "服务器已经在运行 (端口 $PORT)"
else
    echo "正在启动服务器..."
    nohup python3 "$PROJECT_DIR/dashboard.py" > "$PROJECT_DIR/dashboard.log" 2>&1 &
    sleep 2
fi

# 打开浏览器
open "http://localhost:$PORT"
echo "已打开: http://localhost:$PORT"
