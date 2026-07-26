import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

import discord

logger = logging.getLogger(__name__)
_COQUI_MODEL = None
_COQUI_LOCK = threading.Lock()


def _ffmpeg_path() -> Optional[str]:
    bundled = Path.cwd() / "ffmpeg" / "bin" / "ffmpeg.exe"
    return str(bundled) if bundled.exists() else shutil.which("ffmpeg")


def _load_reference_with_ffmpeg(path: str, sampling_rate: int):
    import torch

    executable = _ffmpeg_path()
    if not executable:
        raise RuntimeError("FFmpeg is required for the Coqui voice reference.")
    result = subprocess.run(
        [
            executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sampling_rate),
            "-f",
            "f32le",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg could not load the voice reference: {detail[:240]}")
    samples = torch.frombuffer(bytearray(result.stdout), dtype=torch.float32).clone()
    return samples.unsqueeze(0)


async def synthesize_tts(text: str) -> str:
    """Create an MP3 using the configured online TTS provider."""
    value = (text or "").strip()
    if not value:
        raise ValueError("Cannot synthesize empty text.")

    engine = (os.getenv("TTS_ENGINE") or "edge").strip().lower()
    suffix = ".wav" if engine == "coqui" else ".mp3"
    fd, output = tempfile.mkstemp(prefix="irene_tts_", suffix=suffix)
    os.close(fd)
    voice = (os.getenv("TTS_VOICE") or "en-US-AriaNeural").strip()

    try:
        if engine == "coqui":
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _synthesize_coqui_sync, value, output)
            return output

        if engine != "gtts":
            try:
                import edge_tts

                await edge_tts.Communicate(value, voice=voice).save(output)
                return output
            except Exception as exc:
                logger.warning("Edge TTS failed; trying gTTS fallback: %s", exc)

        from gtts import gTTS

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: gTTS(text=value, lang=os.getenv("TTS_LANGUAGE", "en"), slow=False).save(output),
        )
        return output
    except Exception:
        try:
            os.remove(output)
        except OSError:
            logger.debug("Failed to remove TTS output after synthesis error: %s", output)
        raise


def _synthesize_coqui_sync(text: str, output: str):
    global _COQUI_MODEL
    reference = Path(os.getenv("KINDROID_VOICE_REFERENCE", "audio/irene_kindroid_sample.mp3"))
    if not reference.is_absolute():
        reference = Path.cwd() / reference
    if not reference.exists():
        raise FileNotFoundError(f"Voice reference file not found: {reference}")

    model_name = os.getenv("COQUI_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    device = os.getenv("TTS_DEVICE", "cpu").strip().lower()
    with _COQUI_LOCK:
        if _COQUI_MODEL is None:
            from TTS.api import TTS
            from TTS.tts.models import xtts

            # The bundled FFmpeg executable is available, but TorchCodec expects shared FFmpeg DLLs.
            xtts.load_audio = _load_reference_with_ffmpeg
            _COQUI_MODEL = TTS(model_name=model_name, progress_bar=False).to(device)
        _COQUI_MODEL.tts_to_file(
            text=text,
            file_path=output,
            speaker_wav=str(reference),
            language=os.getenv("TTS_LANGUAGE", "en"),
        )


async def send_tts_clip(channel: discord.abc.Messageable, text: str):
    """Send a temporary TTS MP3 to a text channel and remove the local file."""
    output = await synthesize_tts(text)
    try:
        extension = Path(output).suffix or ".mp3"
        await channel.send(file=discord.File(output, filename=f"irene{extension}"))
    finally:
        try:
            os.remove(output)
        except OSError:
            logger.debug("Failed to remove sent TTS clip: %s", output)


async def play_tts(voice_client: discord.VoiceClient, text: str):
    """Synthesize and play speech, removing the file after ffmpeg finishes."""
    output = await synthesize_tts(text)
    finished = asyncio.Event()
    loop = asyncio.get_running_loop()

    def after_playback(error):
        if error:
            logger.error("FFmpeg playback failed: %s", error)
        loop.call_soon_threadsafe(finished.set)

    try:
        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.2)
        executable = _ffmpeg_path() or "ffmpeg"
        voice_client.play(
            discord.FFmpegPCMAudio(output, executable=executable),
            after=after_playback,
        )
        await finished.wait()
    finally:
        try:
            os.remove(output)
        except OSError:
            logger.debug("Failed to remove played TTS file: %s", output)
