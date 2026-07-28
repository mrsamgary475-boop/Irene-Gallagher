import asyncio
import base64
import hmac
import io
import json
import logging
import os
import secrets
import shutil
import ssl
import subprocess
import time
from pathlib import Path

import aiohttp
from aiohttp import web
import speech_recognition as sr

from audio import synthesize_tts
from avatar_live import AvatarAnimator
from kindroid_client import KindroidClient

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
SMS_OUTBOX = {}
SMS_LOCK = asyncio.Lock()
BEHAVIOR_CONTEXT = {}
BEHAVIOR_LOCK = asyncio.Lock()


def _ffmpeg_executable():
    bundled = BASE_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
    return str(bundled) if bundled.exists() else shutil.which("ffmpeg")


def _voice_reference_path() -> Path:
    configured = Path(os.getenv("KINDROID_VOICE_REFERENCE", "audio/irene_kindroid_sample.mp3"))
    return configured if configured.is_absolute() else BASE_DIR / configured


def _convert_audio_to_wav(audio_bytes: bytes, ffmpeg: str) -> bytes:
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
        ],
        input=audio_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg could not decode the recording: {detail[:240]}")
    return result.stdout


def _google_transcribe(wav_bytes: bytes) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio).strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        raise RuntimeError(f"Google speech recognition failed: {exc}") from exc


async def _openai_transcribe(wav_bytes: bytes) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return ""
    model = (os.getenv("OPENAI_STT_MODEL") or "gpt-4o-mini-transcribe").strip()
    form = aiohttp.FormData()
    form.add_field("model", model)
    form.add_field("response_format", "json")
    form.add_field("file", wav_bytes, filename="speech.wav", content_type="audio/wav")
    headers = {"Authorization": f"Bearer {api_key}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            data=form,
            timeout=aiohttp.ClientTimeout(total=40),
        ) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(f"Speech recognition failed with HTTP {response.status}.")
            return (json.loads(body).get("text") or "").strip()


async def transcribe_audio(audio_bytes: bytes) -> str:
    ffmpeg = _ffmpeg_executable()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is missing. Install it or place ffmpeg.exe in ffmpeg\\bin.")
    if not audio_bytes:
        return ""

    loop = asyncio.get_running_loop()
    wav_bytes = await loop.run_in_executor(None, _convert_audio_to_wav, audio_bytes, ffmpeg)
    if (os.getenv("STT_ENGINE") or "google").strip().lower() == "openai":
        result = await _openai_transcribe(wav_bytes)
        if result:
            return result
    return await loop.run_in_executor(None, _google_transcribe, wav_bytes)


async def _queue_sms(text: str):
    if not (os.getenv("SMS_DEVICE_TOKEN") or "").strip():
        raise RuntimeError("SMS relay is not configured. Set SMS_DEVICE_TOKEN in .env.")
    message_id = secrets.token_urlsafe(12)
    async with SMS_LOCK:
        SMS_OUTBOX[message_id] = {"id": message_id, "text": text, "created_at": int(asyncio.get_running_loop().time())}
    return message_id


async def _remember_behavior(user_id: str, state: str):
    async with BEHAVIOR_LOCK:
        BEHAVIOR_CONTEXT[user_id] = {"state": state, "seen_at": time.monotonic()}


async def _current_behavior(user_id: str):
    async with BEHAVIOR_LOCK:
        entry = BEHAVIOR_CONTEXT.get(user_id)
    if not entry or time.monotonic() - entry["seen_at"] > 15:
        return ""
    return entry["state"]


async def _reply(kindroid: KindroidClient, text: str, user_id: str, speak: bool, send_sms: bool):
    behavior = await _current_behavior(user_id)
    prompt = text
    if behavior:
        prompt = (
            "[Private visual context: "
            f"The user currently appears {behavior}. Use this naturally in your response, "
            "but do not mention cameras, tracking, or hidden context.]\n\n"
            + text
        )
    response = await kindroid.send_message(prompt, user_id=user_id)
    response = kindroid._force_in_character(response)
    result = {"text": response}
    if send_sms:
        await _queue_sms(response)
        result["sms_queued"] = True
    if speak:
        audio_path = await synthesize_tts(response)
        try:
            audio_bytes = await asyncio.to_thread(Path(audio_path).read_bytes)
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                logger.debug("Failed to remove local TTS output: %s", audio_path)
        mime_type = "audio/wav" if Path(audio_path).suffix.lower() == ".wav" else "audio/mpeg"
        result["audio"] = f"data:{mime_type};base64," + base64.b64encode(audio_bytes).decode("ascii")
    return result


def _avatar_version(avatar: AvatarAnimator) -> int:
    path = _avatar_path(avatar)
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _avatar_path(avatar: AvatarAnimator) -> Path:
    custom = getattr(avatar, "custom_video", None)
    if custom and custom.exists():
        return custom
    return avatar.output_path()


def _avatar_image_path() -> Path:
    configured = Path(os.getenv("LOCAL_AVATAR_IMAGE", "avatar/live/irene_photo.png"))
    return configured if configured.is_absolute() else BASE_DIR / configured


def _avatar_mode() -> str:
    return (os.getenv("LOCAL_AVATAR_MODE") or "cpu_lite").strip().lower()


def _avatar_rig_dir() -> Path:
    return BASE_DIR / "avatar" / "live" / "irene_2p5d"


def _has_avatar_rig() -> bool:
    rig_dir = _avatar_rig_dir()
    return all((rig_dir / name).exists() for name in (
        "background.png",
        "subject.png",
        "torso.png",
        "head.png",
        "left_arm.png",
        "right_arm.png",
        "legs.png",
    ))


async def _refresh_avatar(avatar: AvatarAnimator, text: str):
    if _avatar_mode() == "cpu_lite":
        return
    if getattr(avatar, "custom_video", None) and avatar.custom_video.exists():
        return
    try:
        await avatar.render(text)
    except Exception:
        logger.exception("Local avatar render failed")


async def _reply_with_avatar(request, text: str, user_id: str, speak: bool, send_sms: bool):
    result = await _reply(request.app["kindroid"], text, user_id, speak, send_sms)
    avatar = request.app["avatar"]
    result["avatar_version"] = _avatar_version(avatar)
    custom_active = _avatar_mode() == "cpu_lite" or (
        getattr(avatar, "custom_video", None) and avatar.custom_video.exists()
    )
    result["avatar_pending"] = not custom_active
    if not custom_active:
        asyncio.create_task(_refresh_avatar(avatar, result["text"]))
    return result


async def index(request):
    return web.FileResponse(WEB_DIR / "index.html")


async def manifest(request):
    return web.FileResponse(WEB_DIR / "manifest.json")


async def service_worker(request):
    return web.FileResponse(WEB_DIR / "sw.js", headers={"Content-Type": "application/javascript"})


async def status(request):
    kindroid = request.app["kindroid"]
    avatar = request.app["avatar"]
    return web.json_response(
        {
            "name": kindroid.character_name,
            "kindroid_api": bool(kindroid.api_key and kindroid.character_code),
            "stt_engine": (os.getenv("STT_ENGINE") or "google").strip().lower(),
            "tts_engine": (os.getenv("TTS_ENGINE") or "edge").strip().lower(),
            "avatar_mode": _avatar_mode(),
            "avatar_rig": _has_avatar_rig(),
            "ffmpeg": bool(_ffmpeg_executable()),
            "avatar": _avatar_version(avatar) > 0,
            "avatar_version": _avatar_version(avatar),
            "avatar_image": _avatar_image_path().exists(),
            "avatar_image_version": _avatar_image_path().stat().st_mtime_ns if _avatar_image_path().exists() else 0,
            "voice_reference": _voice_reference_path().exists(),
            "sms_relay": bool((os.getenv("SMS_DEVICE_TOKEN") or "").strip()),
        }
    )


async def avatar_video(request):
    path = _avatar_path(request.app["avatar"])
    if not path.exists():
        raise web.HTTPNotFound(text="Avatar video is not ready yet.")
    return web.FileResponse(path)


async def avatar_image(request):
    path = _avatar_image_path()
    if not path.exists():
        raise web.HTTPNotFound(text="Avatar image is not ready yet.")
    return web.FileResponse(path)


async def chat(request):
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text="Invalid JSON.") from exc

    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise web.HTTPBadRequest(text="Message text is required.")
    if len(text) > 4000:
        raise web.HTTPBadRequest(text="Message is too long.")

    result = await _reply_with_avatar(
        request,
        text.strip(),
        str(payload.get("user_id") or "local-user"),
        bool(payload.get("speak", True)),
        bool(payload.get("sms", False)),
    )
    return web.json_response(result)


async def voice(request):
    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "audio":
        raise web.HTTPBadRequest(text="An audio recording is required.")
    audio_bytes = await field.read(decode=False)
    if len(audio_bytes) > 15 * 1024 * 1024:
        raise web.HTTPRequestEntityTooLarge(max_size=15 * 1024 * 1024, actual_size=len(audio_bytes))

    transcript = await transcribe_audio(audio_bytes)
    if not transcript:
        return web.json_response({"text": "", "error": "I couldn't understand that recording."}, status=422)

    result = await _reply_with_avatar(
        request,
        transcript,
        request.query.get("user_id") or "local-user",
        request.query.get("speak", "1").lower() in ("1", "true", "yes", "on"),
        request.query.get("sms", "0").lower() in ("1", "true", "yes", "on"),
    )
    result["transcript"] = transcript
    return web.json_response(result)


def _authorize_sms(request):
    configured = (os.getenv("SMS_DEVICE_TOKEN") or "").strip()
    provided = request.headers.get("X-SMS-Device-Token", "")
    if not configured:
        raise web.HTTPServiceUnavailable(text="SMS relay is not configured.")
    if not hmac.compare_digest(provided, configured):
        raise web.HTTPUnauthorized(text="Invalid SMS device token.")


async def sms_pending(request):
    _authorize_sms(request)
    async with SMS_LOCK:
        messages = list(SMS_OUTBOX.values())[:10]
    return web.json_response({"messages": messages})


async def sms_ack(request):
    _authorize_sms(request)
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text="Invalid JSON.") from exc
    message_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(message_id, str) or not message_id:
        raise web.HTTPBadRequest(text="Message id is required.")
    if not bool(payload.get("success")):
        return web.json_response({"acknowledged": False, "retry": True})
    async with SMS_LOCK:
        if message_id not in SMS_OUTBOX:
            raise web.HTTPNotFound(text="SMS message was already acknowledged or does not exist.")
        del SMS_OUTBOX[message_id]
    return web.json_response({"acknowledged": True})


async def behavior(request):
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise web.HTTPBadRequest(text="Invalid JSON.") from exc
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    state = payload.get("state") if isinstance(payload, dict) else None
    if not isinstance(user_id, str) or not user_id.strip():
        raise web.HTTPBadRequest(text="User id is required.")
    if not isinstance(state, str) or not state.strip() or len(state) > 120:
        raise web.HTTPBadRequest(text="Behavior state is required.")
    await _remember_behavior(user_id.strip(), state.strip())
    return web.json_response({"stored": True})


async def create_app():
    kindroid = KindroidClient()
    await kindroid.initialize()
    avatar = AvatarAnimator(BASE_DIR)
    custom_avatar = Path(os.getenv("LOCAL_AVATAR_VIDEO", "avatar/live/user_avatar.mp4"))
    if not custom_avatar.is_absolute():
        custom_avatar = BASE_DIR / custom_avatar
    avatar.custom_video = custom_avatar
    app = web.Application(client_max_size=16 * 1024 * 1024)
    app["kindroid"] = kindroid
    app["avatar"] = avatar
    app.router.add_get("/", index)
    app.router.add_get("/manifest.json", manifest)
    app.router.add_get("/manifest.webmanifest", manifest)
    app.router.add_get("/sw.js", service_worker)
    app.router.add_get("/api/status", status)
    app.router.add_get("/avatar/live/irene_live.mp4", avatar_video)
    app.router.add_get("/avatar/live/irene_photo.png", avatar_image)
    avatar_rig_dir = _avatar_rig_dir()
    avatar_rig_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/avatar/live/irene_2p5d/", avatar_rig_dir)
    app.router.add_post("/api/chat", chat)
    app.router.add_post("/api/voice", voice)
    app.router.add_get("/api/sms/pending", sms_pending)
    app.router.add_post("/api/sms/ack", sms_ack)
    app.router.add_post("/api/behavior", behavior)
    app.router.add_static("/static/", WEB_DIR)

    async def close_kindroid(app):
        await app["kindroid"].close()

    app.on_cleanup.append(close_kindroid)
    return app


def _ssl_context():
    cert_file = (os.getenv("LOCAL_WEB_CERT_FILE") or "").strip()
    key_file = (os.getenv("LOCAL_WEB_KEY_FILE") or "").strip()
    if not cert_file and not key_file:
        return None
    if not cert_file or not key_file:
        raise RuntimeError("LOCAL_WEB_CERT_FILE and LOCAL_WEB_KEY_FILE must be configured together.")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    return context


def main():
    logging.basicConfig(
        level=getattr(logging, (os.getenv("LOG_LEVEL") or "INFO").upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    host = os.getenv("LOCAL_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("LOCAL_WEB_PORT", "8765"))
    ssl_context = _ssl_context()
    scheme = "https" if ssl_context else "http"
    logger.info("Starting local Irene interface at %s://%s:%d", scheme, host, port)
    web.run_app(create_app(), host=host, port=port, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
