#!/usr/bin/env python3
"""A small shop with known faults, for tests/testing_skills_test.sh.

    app.py --port-file <file> --hits <file>     serves on a free loopback port and writes it to the port file

Works: the price quote and the sign-in. Broken: the coupon (500, a console error, no change on the page). Slow: the
sales report (4 s). Dead: the newsletter button (no handler). A websocket subscribes on load and answers a greeting.
Every request and every socket message is appended to the hits file, so a test can prove from the server's side what
reached it.
"""

import argparse
import base64
import hashlib
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PAGE = Path(__file__).with_name("index.html")
SLOW_SECONDS = 4
PRICE_CENTS = 999


class Shop(BaseHTTPRequestHandler):
    hits: Path

    def log_message(self, *args):
        pass

    def answer(self, status, body, kind="application/json", headers=()):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    def socket(self):
        """The smallest websocket: short text frames, each logged and answered with 'ack <text>'."""
        key = self.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        self.protocol_version = "HTTP/1.1"
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", base64.b64encode(hashlib.sha1(key.encode()).digest()).decode())
        self.end_headers()
        self.close_connection = True
        while True:
            head = self.rfile.read(2)
            if len(head) < 2 or head[0] & 0x0F != 1 or head[1] & 0x7F > 125:
                return
            mask = self.rfile.read(4)
            text = bytes(b ^ mask[i % 4] for i, b in enumerate(self.rfile.read(head[1] & 0x7F))).decode()
            with self.hits.open("a") as log:
                log.write(f"WS {text}\n")
            reply = f"ack {text}".encode()
            self.wfile.write(bytes([0x81, len(reply)]) + reply)
            self.wfile.flush()

    def record(self):
        with self.hits.open("a") as log:
            log.write(f"{self.command} {urlsplit(self.path).path}\n")

    def do_GET(self):
        self.record()
        url = urlsplit(self.path)
        if url.path == "/ws":
            return self.socket()
        if url.path == "/":
            return self.answer(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/quote":
            quantity = parse_qs(url.query).get("qty", [""])[0]
            if not quantity.isdigit() or not 0 < int(quantity) < 1000:
                return self.answer(400, {"error": "quantity must be 1 to 999"})
            return self.answer(200, {"quantity": int(quantity), "total": f"{int(quantity) * PRICE_CENTS / 100:.2f}"})
        if url.path == "/api/report":
            time.sleep(SLOW_SECONDS)
            return self.answer(200, {"orders": 12})
        if url.path == "/api/me":
            wanted = f"Bearer {os.environ.get('SHOP_TOKEN', '')}"
            if os.environ.get("SHOP_TOKEN") and self.headers.get("Authorization") == wanted:
                return self.answer(200, {"user": "demo", "echo": self.headers.get("Authorization")})
            return self.answer(401, {"error": "sign in first"})
        if url.path == "/away":
            return self.answer(302, {}, headers=[("Location", "https://elsewhere.invalid/")])
        return self.answer(404, {"error": "not found"})

    def do_POST(self):
        self.record()
        path = urlsplit(self.path).path
        data = self.body()
        if path == "/api/coupon":  # the planted fault
            return self.answer(500, {"error": "internal error"})
        if path == "/api/signin":
            expected = os.environ.get("SHOP_PASSWORD", "")
            if expected and data.get("password") == expected:
                return self.answer(200, {"user": data.get("user", "")})
            return self.answer(401, {"error": "wrong password"})
        return self.answer(404, {"error": "not found"})

    def do_DELETE(self):
        self.record()
        self.answer(200, {"deleted": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port-file", required=True)
    parser.add_argument("--hits", required=True)
    args = parser.parse_args()
    Shop.hits = Path(args.hits)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Shop)
    Path(args.port_file).write_text(str(server.server_address[1]))
    server.serve_forever()


if __name__ == "__main__":
    main()
