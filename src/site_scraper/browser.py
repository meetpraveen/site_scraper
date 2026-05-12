from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def launch_debug_chrome(url: str, user_data_dir: Path, port: int = 9222) -> subprocess.Popen[str]:
    user_data_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["google-chrome", f"--remote-debugging-port={port}", f"--user-data-dir={user_data_dir}", "--no-first-run", "--no-default-browser-check", url]
    console.print(f"Launching Chrome on debug port {port}.")
    return subprocess.Popen(cmd, text=True)


async def wait_for_user_auth() -> None:
    console.print("Authenticate in the opened browser, then press Enter here to continue.")
    await asyncio.to_thread(input)
