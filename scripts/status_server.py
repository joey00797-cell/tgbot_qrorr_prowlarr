#!/usr/bin/env python3
"""
Status HTTP Server
Запускать на машине с arr-стаком.
Отдаёт статус дисков в JSON на порту 9999.

Установка как systemd сервис:
  cp status_server.py /usr/local/bin/status_server.py
  # создать /etc/systemd/system/status-server.service
  # systemctl enable --now status-server
"""
import http.server
import json
import shutil

PORT = 9999
MEDIA_PATH = "/media"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        arr = shutil.disk_usage("/")
        try:
            media = shutil.disk_usage(MEDIA_PATH)
            media_data = {"total": media.total, "used": media.used, "free": media.free}
        except Exception:
            media_data = None

        data = {
            "arr":   {"total": arr.total, "used": arr.used, "free": arr.free},
            "media": media_data,
        }
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    print(f"Status server running on port {PORT}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
