import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_kindroid_api_base(raw_base: str) -> str:
    base = (raw_base or "").strip()
    if not base:
        return "https://api.kindroid.ai"
    if "kindroid.ai/chat" in base.lower():
        return "https://api.kindroid.ai"
    return base.rstrip("/")


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
COMMAND_PREFIX = BOT_PREFIX
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DISCORD_SERVER_TAG = os.getenv("DISCORD_SERVER_TAG", "KIN").strip()
DISCORD_BOT_NICKNAME = os.getenv("DISCORD_BOT_NICKNAME", "Irene").strip()

KINDROID_CODE = os.getenv("KINDROID_AI_ID") or os.getenv("KINDROID_CODE", "")
KINDROID_API_KEY = os.getenv("KINDROID_API_KEY", "")
KINDROID_API_BASE = _normalize_kindroid_api_base(
    os.getenv("KINDROID_API_BASE", "https://api.kindroid.ai")
)
