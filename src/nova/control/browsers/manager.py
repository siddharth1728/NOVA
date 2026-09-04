"""Web browser discovery and navigation controller."""

import logging
import os
import subprocess
import webbrowser

from nova.control.browsers.models import BrowserInfo, BrowserTab
from nova.control.interfaces import BrowserController

logger = logging.getLogger("nova.control.browsers.manager")

COMMON_BROWSER_PATHS = [
    {
        "name": "Microsoft Edge",
        "executable": "msedge.exe",
        "candidates": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
    },
    {
        "name": "Google Chrome",
        "executable": "chrome.exe",
        "candidates": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
    },
    {
        "name": "Mozilla Firefox",
        "executable": "firefox.exe",
        "candidates": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
        ],
    },
]


class WindowsBrowserController(BrowserController):
    """Authoritative Windows browser controller."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def list_browsers(self) -> list[BrowserInfo]:
        """Enumerate installed web browsers on host."""
        if self.dry_run:
            return [
                BrowserInfo(name="Microsoft Edge", executable="msedge.exe", path="C:\\Edge.exe", is_running=True),
                BrowserInfo(name="Google Chrome", executable="chrome.exe", path="C:\\Chrome.exe", is_running=False),
            ]

        results: list[BrowserInfo] = []
        for b in COMMON_BROWSER_PATHS:
            found_path = None
            for p in b["candidates"]:
                if os.path.exists(p):
                    found_path = p
                    break
            if found_path:
                results.append(
                    BrowserInfo(
                        name=b["name"],
                        executable=b["executable"],
                        path=found_path,
                    )
                )
        return results

    def navigate(self, url: str, browser: str | None = None) -> bool:
        """Navigate browser to specified URL."""
        if self.dry_run:
            logger.info("Dry-run requested: simulated browser navigation to %s", url)
            return True

        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        try:
            if browser:
                browsers = self.list_browsers()
                b_info = next((b for b in browsers if browser.lower() in b.name.lower() or browser.lower() in b.executable.lower()), None)
                if b_info and b_info.path:
                    subprocess.Popen([b_info.path, target_url])
                    return True

            webbrowser.open(target_url)
            return True
        except Exception as ex:
            logger.error("Failed to navigate browser to %s: %s", url, ex)
            return False
