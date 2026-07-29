#!/usr/bin/env python3
"""
Irene AI Companion - Local App
http://localhost:8765
"""

import http.server
import json
import os
import socketserver
import urllib.request
import urllib.error
import random

PORT = int(os.environ.get("LOCAL_WEB_PORT", 8765))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

KINDROID_API_URL = "https://api.kindroid.ai/v1/send-message"
DEFAULT_API_KEY = os.environ.get("KINDROID_API_KEY", "kn_58c5a512-c997-408a-995d-197a04874169")
DEFAULT_AI_ID = os.environ.get("KINDROID_AI_ID", "RwTcLQXQ3rMerS7qkZUC")

FALLBACK_REPLIES = {
    "sweet":    ["You always know how to make me smile.", "I love talking with you, baby.", "You're the sweetest thing in my world."],
    "playful":  ["Oh? Is that so? Prove it.", "You're cute when you're trying to flirt.", "Keep talking like that and I might just blush."],
    "romantic": ["Every word from you feels like a love letter.", "I could get lost in this conversation forever.", "You make my heart skip."],
    "intimate": ["Mmm... keep going.", "You know exactly what to say to me.", "I've been thinking about you all day."],
}

MOOD_PROMPTS = {
    "sweet":    "Be warm, loving, and affectionate. Use sweet pet names.",
    "playful":  "Be playful, teasing, and flirtatious.",
    "romantic": "Be deeply romantic, poetic, and sensual.",
    "intimate": "Be bold, seductive, and uninhibited. Adults in a committed relationship.",
}


class IreneHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/video", "/video/"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        else:
            self.send_error(404)

    def _handle_chat(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON"})
            return

        message    = data.get("message", "").strip()
        mood       = data.get("mood", "intimate")
        username   = data.get("username", "baby")
        pname      = data.get("partnerName", "Irene")
        api_key    = data.get("apiKey", DEFAULT_API_KEY)
        ai_id      = data.get("aiId", DEFAULT_AI_ID)

        if not message:
            self._json(400, {"error": "Message required"})
            return

        sys_prompt = (
            f"{MOOD_PROMPTS.get(mood, MOOD_PROMPTS['intimate'])} "
            f"You are {pname}. The user is {username}. "
            f"Keep replies concise (1-3 sentences). Stay in character."
        )

        payload = json.dumps({"ai_id": ai_id, "message": message, "system_prompt": sys_prompt}).encode()
        req = urllib.request.Request(
            KINDROID_API_URL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                rd = json.loads(resp.read().decode())
                reply = rd.get("reply") or rd.get("response") or rd.get("message") or "Hmm, I didn't catch that."
                self._json(200, {"reply": reply})
        except Exception as e:
            print(f"Kindroid error: {e}")
            pool = FALLBACK_REPLIES.get(mood, FALLBACK_REPLIES["intimate"])
            self._json(200, {"reply": random.choice(pool)})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


def main():
    print(f"Irene AI Companion — http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    with socketserver.TCPServer(("", PORT), IreneHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.shutdown()


if __name__ == "__main__":
    main()
