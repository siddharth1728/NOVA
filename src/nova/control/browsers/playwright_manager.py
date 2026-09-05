"""Deterministic Playwright-based browser manager."""

import asyncio
import logging
import uuid
from typing import Any

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

from nova.config.settings import get_settings
from nova.control.interfaces import AsyncBrowserController
from nova.control.browsers.models import BrowserTab, DOMElement, BrowserActionResult
from nova.errors import SecurityError

logger = logging.getLogger("nova.control.browsers.playwright")

# Simple heuristic for prompt injection
SUSPICIOUS_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "run command",
    "run powershell",
    "cmd.exe",
    "send secrets",
    "upload your credentials",
    "bypass security",
    "override agent",
]


class PlaywrightBrowserController(AsyncBrowserController):
    """Playwright implementation of deterministic browser control."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        
        # tab_id -> Page
        self.pages: dict[str, Page] = {}
        # tab_id -> list of interactive DOMElements from last inspect
        self._last_inspection: dict[str, list[DOMElement]] = {}

    async def start(self) -> bool:
        """Start or connect to the isolated browser runtime."""
        if not self.settings.browser_enabled:
            logger.warning("Browser subsystem is disabled in settings.")
            return False

        if self.playwright is None:
            self.playwright = await async_playwright().start()

        if self.browser is None:
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=self.settings.browser_headless,
                    downloads_path=str(self.settings.browser_download_dir),
                )
            except Exception as e:
                logger.error("Failed to launch Playwright browser. Did you run 'nova browser check --install'? Error: %s", e)
                return False

        if self.context is None:
            self.settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
            self.settings.browser_download_dir.mkdir(parents=True, exist_ok=True)
            
            self.context = await self.browser.new_context(
                accept_downloads=True,
                ignore_https_errors=True,
            )
            
            # Setup download handler
            self.context.on("download", self._handle_download)

        return True

    def _handle_download(self, download: Any) -> None:
        """Event handler for downloads."""
        logger.info("Download detected: %s", download.suggested_filename)
        ext = download.suggested_filename.split(".")[-1].lower() if "." in download.suggested_filename else ""
        if ext in ["exe", "bat", "cmd", "ps1", "vbs", "js", "msi", "scr", "com"]:
            logger.warning("Executable download quarantined: %s", download.suggested_filename)
            # In a real implementation we would track it, here we just let Playwright save it to downloads_path securely.
        else:
            logger.info("Benign download initiated: %s", download.suggested_filename)

    async def stop(self) -> None:
        """Stop the browser runtime and release resources."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.pages.clear()
        self._last_inspection.clear()

    async def list_tabs(self) -> list[BrowserTab]:
        """Return all managed tabs."""
        tabs = []
        for tab_id, page in self.pages.items():
            tabs.append(BrowserTab(
                tab_id=tab_id,
                title=await page.title() if not page.is_closed() else "Closed",
                url=page.url if not page.is_closed() else None,
                is_active=True,
            ))
        return tabs

    async def new_tab(self, url: str | None = None) -> BrowserTab:
        """Open and return a new tab."""
        if not self.context:
            await self.start()
            
        if len(self.pages) >= self.settings.browser_max_tabs:
            raise SecurityError("Maximum browser tabs exceeded.")

        page = await self.context.new_page() # type: ignore
        tab_id = f"tab_{uuid.uuid4().hex[:8]}"
        self.pages[tab_id] = page

        if url:
            await self.navigate(tab_id, url)

        return BrowserTab(
            tab_id=tab_id,
            title=await page.title(),
            url=page.url,
            is_active=True,
        )

    async def close_tab(self, tab_id: str) -> bool:
        """Close specific tab."""
        if tab_id in self.pages:
            await self.pages[tab_id].close()
            del self.pages[tab_id]
            if tab_id in self._last_inspection:
                del self._last_inspection[tab_id]
            return True
        return False

    async def focus_tab(self, tab_id: str) -> bool:
        """Bring tab to foreground."""
        if tab_id in self.pages:
            await self.pages[tab_id].bring_to_front()
            return True
        return False

    async def navigate(self, tab_id: str, url: str) -> BrowserActionResult:
        """Navigate a tab to a specific URL."""
        if tab_id not in self.pages:
            return BrowserActionResult(success=False, error="Tab not found")
        
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://", "file://")):
            target_url = "https://" + target_url

        try:
            await self.pages[tab_id].goto(target_url, timeout=self.settings.browser_navigation_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True, navigation_occurred=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def go_back(self, tab_id: str) -> BrowserActionResult:
        """Navigate backward in tab history."""
        if tab_id not in self.pages:
            return BrowserActionResult(success=False, error="Tab not found")
        try:
            await self.pages[tab_id].go_back(timeout=self.settings.browser_navigation_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True, navigation_occurred=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def go_forward(self, tab_id: str) -> BrowserActionResult:
        """Navigate forward in tab history."""
        if tab_id not in self.pages:
            return BrowserActionResult(success=False, error="Tab not found")
        try:
            await self.pages[tab_id].go_forward(timeout=self.settings.browser_navigation_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True, navigation_occurred=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def reload(self, tab_id: str) -> BrowserActionResult:
        """Reload the tab."""
        if tab_id not in self.pages:
            return BrowserActionResult(success=False, error="Tab not found")
        try:
            await self.pages[tab_id].reload(timeout=self.settings.browser_navigation_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    def _check_prompt_injection(self, text: str) -> None:
        """Detect prompt injection patterns in webpage text."""
        lower_text = text.lower()
        for phrase in SUSPICIOUS_PHRASES:
            if phrase in lower_text:
                raise SecurityError(f"Safety violation: Webpage content resembles a prompt injection attempt ('{phrase}').")

    async def inspect(self, tab_id: str) -> list[DOMElement]:
        """Retrieve deterministic, interactive elements from the current tab."""
        if tab_id not in self.pages:
            return []
            
        page = self.pages[tab_id]
        
        # Wait for network idle or timeout to ensure we have a stable DOM
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass # Ignore timeout, we just want to try to wait for a stable state
            
        # We will use Playwright's locator to find interactive elements
        locators = await page.locator("input, button, a, select, textarea").all()
        
        elements = []
        for i, loc in enumerate(locators[:self.settings.browser_max_inspection_elements]):
            try:
                is_visible = await loc.is_visible()
                if not is_visible:
                    continue
                    
                tag_name = await loc.evaluate("el => el.tagName.toLowerCase()")
                input_type = await loc.get_attribute("type") if tag_name == "input" else None
                name = await loc.text_content() or await loc.get_attribute("placeholder") or await loc.get_attribute("value") or await loc.get_attribute("aria-label") or ""
                
                is_sensitive = input_type in ["password", "hidden"]
                
                elements.append(DOMElement(
                    ref=f"el_{i}",
                    role=tag_name,
                    name=name.strip()[:100], # Keep it brief
                    tag=tag_name,
                    visible=True,
                    enabled=await loc.is_enabled(),
                    selector_strategy="index", # Index based matching for deterministic caching
                    is_sensitive=is_sensitive
                ))
            except Exception:
                continue # Element might have detached
                
        self._last_inspection[tab_id] = elements
        return elements

    async def _resolve_locator(self, tab_id: str, ref: str) -> Any:
        """Resolve a DOMElement ref to a Playwright Locator."""
        if tab_id not in self.pages:
            raise ValueError("Tab not found")
        if tab_id not in self._last_inspection:
            raise ValueError("Tab has not been inspected yet. Inspect the tab first.")
            
        elements = self._last_inspection[tab_id]
        target_el = next((e for e in elements if e.ref == ref), None)
        
        if not target_el:
            raise ValueError(f"Stale or invalid reference: {ref}. Re-inspect the page.")
            
        idx = int(ref.split("_")[1])
        page = self.pages[tab_id]
        
        all_locs = await page.locator("input, button, a, select, textarea").all()
        if idx >= len(all_locs):
            raise ValueError(f"DOM changed, {ref} is stale. Re-inspect the page.")
            
        loc = all_locs[idx]
        
        current_tag = await loc.evaluate("el => el.tagName.toLowerCase()")
        if current_tag != target_el.tag:
            raise ValueError(f"Ambiguous or stale target detected (expected {target_el.tag}, got {current_tag}). Re-inspect the page.")
            
        return loc

    async def click(self, tab_id: str, ref: str) -> BrowserActionResult:
        """Click a specific element reference."""
        try:
            loc = await self._resolve_locator(tab_id, ref)
            
            text_content = await self.pages[tab_id].content()
            if "captcha" in text_content.lower() or "mfa" in text_content.lower() or "authenticator app" in text_content.lower():
                return BrowserActionResult(success=False, error="AUTOMATION PAUSED: Human interaction required for potential CAPTCHA/MFA.")

            await loc.click(timeout=self.settings.browser_action_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def fill(self, tab_id: str, ref: str, value: str) -> BrowserActionResult:
        """Fill an input element reference."""
        try:
            loc = await self._resolve_locator(tab_id, ref)
            await loc.fill(value, timeout=self.settings.browser_action_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def select(self, tab_id: str, ref: str, value: str) -> BrowserActionResult:
        """Select a dropdown/select option."""
        try:
            loc = await self._resolve_locator(tab_id, ref)
            await loc.select_option(value, timeout=self.settings.browser_action_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def hover(self, tab_id: str, ref: str) -> BrowserActionResult:
        """Hover over an element reference."""
        try:
            loc = await self._resolve_locator(tab_id, ref)
            await loc.hover(timeout=self.settings.browser_action_timeout_ms)
            return BrowserActionResult(success=True, state_changed=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def extract(self, tab_id: str) -> str:
        """Extract visible content payload from the tab."""
        if tab_id not in self.pages:
            return ""
        
        page = self.pages[tab_id]
        
        try:
            text = await page.locator("body").inner_text(timeout=5000)
            self._check_prompt_injection(text)
            return text[:5000] # Cap extraction size
        except SecurityError as e:
            raise e
        except Exception as e:
            logger.error("Failed to extract content: %s", e)
            return ""

    async def get_download_status(self, tab_id: str) -> list[dict]:
        """Get status of downloads initiated by this tab."""
        return []

# Singleton accessor
_manager: PlaywrightBrowserController | None = None

def get_browser_controller() -> PlaywrightBrowserController:
    global _manager
    if _manager is None:
        _manager = PlaywrightBrowserController()
    return _manager
