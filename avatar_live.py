import asyncio
import hashlib
import os
import shutil
from pathlib import Path
from datetime import datetime


class AvatarAnimator:
    """Generates mood-driven avatar clips for OBS/virtual camera workflows."""

    def __init__(self, base_dir: Path | None = None):
        root = Path(base_dir or os.getcwd())
        self.source_image = root / "avatar" / "first_order" / "source.png"
        self.output_file = root / "avatar" / "live" / "irene_live.mp4"
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_dir = root / "avatar" / "live" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = root / "avatar" / "live" / "state.txt"
        self.ffmpeg = root / "ffmpeg" / "bin" / "ffmpeg.exe"
        self._lock = asyncio.Lock()
        self.last_error = ""

    def output_path(self) -> Path:
        return self.output_file

    def infer_mood(self, text: str) -> str:
        t = (text or "").lower()
        if any(k in t for k in ("angry", "mad", "furious", "shut up", "enough", "listen carefully", "now")):
            return "intense"
        if any(k in t for k in ("love", "baby", "darling", "sweet", "miss you", "kiss")):
            return "affectionate"
        if any(k in t for k in ("haha", "lol", "tease", "playful", "fun", "😉", "😏")):
            return "playful"
        if any(k in t for k in ("sorry", "hurt", "sad", "tired", "quiet", "down")):
            return "soft"
        if any(k in t for k in ("calm", "breathe", "steady", "focus", "relax")):
            return "calm"
        return "neutral"

    def _mood_profile(self, mood: str, digest: bytes) -> tuple[str, int]:
        # Base movement parameters
        amp_x = 8 + (digest[0] % 8)
        amp_y = 6 + (digest[1] % 6)
        period_x = 16 + (digest[2] % 10)
        period_y = 20 + (digest[3] % 10)
        zoom_step = 0.00045 + (digest[4] % 4) * 0.0001
        max_zoom = 1.08 + (digest[5] % 4) * 0.01
        seconds = 12
        eq = "eq=contrast=1.03:saturation=1.05:brightness=0.00"

        if mood == "intense":
            amp_x += 10
            amp_y += 8
            period_x = max(8, period_x - 6)
            period_y = max(10, period_y - 5)
            zoom_step += 0.00025
            max_zoom += 0.03
            eq = "eq=contrast=1.10:saturation=1.12:brightness=0.02"
            seconds = 10
        elif mood == "affectionate":
            amp_x = max(5, amp_x - 2)
            amp_y = max(4, amp_y - 2)
            period_x += 8
            period_y += 10
            zoom_step = max(0.00035, zoom_step - 0.0001)
            eq = "eq=contrast=1.02:saturation=1.10:brightness=0.01"
            seconds = 14
        elif mood == "playful":
            amp_x += 6
            amp_y += 4
            period_x = max(10, period_x - 2)
            period_y = max(12, period_y - 2)
            eq = "eq=contrast=1.06:saturation=1.14:brightness=0.01"
            seconds = 11
        elif mood == "soft":
            amp_x = max(4, amp_x - 4)
            amp_y = max(3, amp_y - 3)
            period_x += 12
            period_y += 12
            zoom_step = max(0.0003, zoom_step - 0.00015)
            eq = "eq=contrast=0.99:saturation=0.94:brightness=-0.01"
            seconds = 15
        elif mood == "calm":
            amp_x = max(4, amp_x - 3)
            amp_y = max(3, amp_y - 3)
            period_x += 14
            period_y += 14
            eq = "eq=contrast=1.00:saturation=0.98:brightness=0.00"
            seconds = 16
        elif mood == "excited":
            amp_x += 8
            amp_y += 6
            period_x = max(10, period_x - 4)
            period_y = max(12, period_y - 3)
            zoom_step += 0.0002
            eq = "eq=contrast=1.08:saturation=1.15:brightness=0.02"
            seconds = 11
        elif mood == "curious":
            amp_x += 4
            amp_y += 3
            period_x = max(12, period_x - 2)
            period_y = max(14, period_y - 2)
            eq = "eq=contrast=1.04:saturation=1.08:brightness=0.01"
            seconds = 13
        elif mood == "surprised":
            amp_x += 12
            amp_y += 10
            period_x = max(8, period_x - 8)
            period_y = max(10, period_y - 6)
            zoom_step += 0.0003
            max_zoom += 0.04
            eq = "eq=contrast=1.12:saturation=1.18:brightness=0.03"
            seconds = 9

        vf = (
            f"zoompan=z='min(zoom+{zoom_step:.4f},{max_zoom:.2f})':"
            f"x='iw/2-(iw/zoom/2)+sin(on/{period_x})*{amp_x}':"
            f"y='ih/2-(ih/zoom/2)+cos(on/{period_y})*{amp_y}':"
            "d=1:s=768x768,"
            f"{eq},"
            # Hold the final frame a bit so it feels like a non-loop "state".
            "tpad=stop_mode=clone:stop_duration=1.2,"
            "format=yuv420p"
        )
        return vf, seconds

    async def render(self, text: str) -> bool:
        # Use pre-generated neural animation if available
        pre_generated = self.first_order_dir / "irene_avatar_animation.mp4"
        if pre_generated.exists():
            try:
                shutil.copy2(pre_generated, self.output_file)
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                self.state_file.write_text(f"mood=neural\nstatus=ok\nupdated={timestamp}\n", encoding="utf-8")
                return True
            except Exception:
                pass
        
        if not self.ffmpeg.exists() or not self.source_image.exists():
            return False

        async with self._lock:
            mood = self.infer_mood(text)
            digest = hashlib.sha256((text or "").encode("utf-8", errors="ignore")).digest()
            vf, seconds = self._mood_profile(mood, digest)

            args = [
                str(self.ffmpeg),
                "-y",
                "-loop",
                "1",
                "-i",
                str(self.source_image),
                "-vf",
                vf,
                "-t",
                str(seconds),
                "-r",
                "30",
                "-an",
                str(self.output_file),
            ]

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            if proc.returncode != 0 or not self.output_file.exists():
                self.last_error = (
                    err.decode("utf-8", errors="ignore") if err else "ffmpeg render failed with no stderr"
                )
                try:
                    self.state_file.write_text(
                        f"mood={mood}\nstatus=error\nerror={self.last_error[:1500]}\n",
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                return False

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            history_clip = self.history_dir / f"irene_{timestamp}_{mood}.mp4"
            try:
                shutil.copy2(self.output_file, history_clip)
            except Exception:
                # History copy is best-effort; keep live file even if this fails.
                pass

            try:
                self.state_file.write_text(f"mood={mood}\nstatus=ok\nupdated={timestamp}\n", encoding="utf-8")
            except Exception:
                pass

            return True
