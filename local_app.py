#!/usr/bin/env python3
"""
Irene AI Companion - Local App
Serves a video avatar interface on http://localhost:8765/video
Proxies chat requests to the Kindroid AI API.
"""

import http.server
import json
import os
import socketserver
import urllib.request
import urllib.error

PORT = 8765
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

KINDROID_API_URL = "https://api.kindroid.ai/v1/send-message"
DEFAULT_API_KEY = os.environ.get("KINDROID_API_KEY", "kn_9686bcf1-b1dd-424c-b02b-c06e1441449c")
DEFAULT_AI_ID = os.environ.get("KINDROID_AI_ID", "RwTcLQXQ3rMerS7qkZUC")


class IreneHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/video" or self.path == "/video/":
            self.path = "/video.html"
        elif self.path == "/" or self.path == "/index.html":
            self.path = "/video.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        else:
            self.send_error(404, "Not Found")

    def _handle_chat(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        message = data.get("message", "").strip()
        mood = data.get("mood", "intimate")
        username = data.get("username", "baby")
        partner_name = data.get("partnerName", "Irene")
        api_key = data.get("apiKey", DEFAULT_API_KEY)
        ai_id = data.get("aiId", DEFAULT_AI_ID)

        if not message:
            self._send_json(400, {"error": "Message is required"})
            return

        mood_prompts = {
            "sweet": "Be warm, loving, and affectionate. Use sweet pet names.",
            "playful": "Be playful, teasing, and flirtatious.",
            "romantic": "Be deeply romantic, poetic, and sensual.",
            "intimate": "Be bold, seductive, and uninhibited. Adults in a committed relationship.",
        }

        system_prompt = (
            f"{mood_prompts.get(mood, mood_prompts['intimate'])} "
            f"You are {partner_name}. The user is {username}. "
            f"Keep replies concise (1-3 sentences). Stay in character."
        )

        payload = json.dumps({
            "ai_id": ai_id,
            "message": message,
            "system_prompt": system_prompt,
        }).encode("utf-8")

        req = urllib.request.Request(
            KINDROID_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                reply = resp_data.get("reply") or resp_data.get("response") or resp_data.get("message") or "Hmm, I didn't catch that."
                self._send_json(200, {"reply": reply})
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"Kindroid API error {e.code}: {error_body}")
            self._send_json(200, {"reply": self._fallback_reply(mood)})
        except Exception as e:
            print(f"Kindroid fetch failed: {e}")
            self._send_json(200, {"reply": self._fallback_reply(mood)})

    def _fallback_reply(self, mood):
        replies = {
            "sweet": ["You always know how to make me smile.", "I love talking with you, baby. Tell me more.", "You're the sweetest thing in my world."],
            "playful": ["Oh? Is that so? Prove it.", "You're cute when you're trying to flirt.", "Keep talking like that and I might just blush."],
            "romantic": ["Every word from you feels like a love letter.", "I could get lost in this conversation with you.", "You make my heart skip, you know that?"],
            "intimate": ["Mmm... keep going.", "You know exactly what to say to me, don't you?", "I've been thinking about you all day."],
        }
        import random
        pool = replies.get(mood, replies["intimate"])
        return random.choice(pool)

    def _send_json(self, code, data):
        body = json.dumps(data).encode("utf-8")
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

    def log_message(self, format, *args):
        pass


def main():
    print(f"Irene AI Companion starting on http://localhost:{PORT}/video")
    print(f"Press Ctrl+C to stop.")
    with socketserver.TCPServer(("", PORT), IreneHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
            httpd.shutdown()


if __name__ == "__main__":
    main()
