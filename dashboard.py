"""简易本地 Web 服务器 - 浏览器访问即可查看最新汇总"""

import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timezone

from config import DATA_DIR
from collector_x import collect as collect_x
from collector_binance import collect as collect_binance
from storage import generate_summary, save_posts, cleanup_old_data


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/latest", "/index.html"]:
            self._serve_latest()
        elif self.path == "/collect":
            self._do_collect()
        elif self.path == "/stats":
            self._serve_stats()
        else:
            super().do_GET()

    def _serve_latest(self):
        """返回最新的 HTML 汇总"""
        latest_path = os.path.join(DATA_DIR, "latest.html")
        if os.path.exists(latest_path):
            with open(latest_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self._send_html("""
            <html><body style="font-family:sans-serif; padding:40px; text-align:center">
                <h1>暂无汇总数据</h1>
                <p>请先运行一次收集任务。</p>
                <a href="/collect" style="color:#0f6efd">立即收集</a>
            </body></html>
            """)

    def _do_collect(self):
        """立即执行一次收集并返回结果"""
        try:
            x_posts = collect_x()
            save_posts(x_posts, source_label="x")
            bs_posts = collect_binance()
            save_posts(bs_posts, source_label="binance")
            all_posts = x_posts + bs_posts
            generate_summary(all_posts)
            cleanup_old_data()

            self._send_html(f"""
            <html><body style="font-family:sans-serif; padding:40px">
                <h1>收集完成</h1>
                <p>共收集 {len(all_posts)} 条数据（X: {len(x_posts)}，币安广场: {len(bs_posts)}）</p>
                <a href="/" style="color:#0f6efc; font-size:18px">查看最新汇总 →</a>
            </body></html>
            """)
        except Exception as e:
            self._send_html(f"""
            <html><body style="font-family:sans-serif; padding:40px">
                <h1>收集失败</h1>
                <p style="color:red">{e}</p>
                <a href="/">返回首页</a>
            </body></html>
            """, status=500)

    def _serve_stats(self):
        """返回当前统计信息"""
        latest_path = os.path.join(DATA_DIR, "latest.html")
        exists = os.path.exists(latest_path)
        mtime = os.path.getmtime(latest_path) if exists else None
        updated_at = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if mtime else "N/A"

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({
            "has_data": exists,
            "last_updated": updated_at,
            "data_dir": os.path.abspath(DATA_DIR),
        }, ensure_ascii=False).encode("utf-8"))

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[Dashboard] {datetime.now(timezone.utc).strftime('%H:%M:%S')} - {args[0]}")


def run_server(port=8080):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("localhost", port), DashboardHandler)
    print(f"\n[Dashboard] 服务器已启动")
    print(f"[Dashboard] 访问地址: http://localhost:{port}")
    print(f"[Dashboard] 按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dashboard] 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    run_server()
