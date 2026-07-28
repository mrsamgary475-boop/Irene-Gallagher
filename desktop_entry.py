"""Windows desktop entry point for Irene.

Launches the local aiohttp web app and opens the configured browser.
This module is the PyInstaller entrypoint for IreneApp.exe.
"""
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(sys.argv[0]).resolve().parent
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
os.chdir(BASE_DIR)

from local_app import create_app, _ssl_context
from aiohttp import web


def _open_browser(host: str, port: int, ssl_context):
    scheme = "https" if ssl_context else "http"
    url = f"{scheme}://{host}:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    logging.basicConfig(
        level=getattr(logging, (os.getenv("LOG_LEVEL") or "INFO").upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("irene.desktop_entry")
    logger.info("Launching IreneApp from %s", BASE_DIR)
    logger.info("Runtime env file expected at %s", BASE_DIR / ".env")

    host = os.getenv("LOCAL_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("LOCAL_WEB_PORT", "8765"))
    ssl_context = _ssl_context()

    import asyncio

    async def run():
        app = await create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=host, port=port, ssl_context=ssl_context)
        await site.start()
        logger.info("IreneApp is ready at %s://%s:%d", "https" if ssl_context else "http", host, port)
        # Keep running forever
        stop = asyncio.Event()
        await stop.wait()

    threading.Thread(target=lambda: webbrowser.open(
        f"{'https' if ssl_context else 'http'}://{host}:{port}"), daemon=True
    ).start()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.exception("IreneApp crashed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
