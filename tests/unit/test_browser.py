"""Unit tests for Phase 08 Browser Intelligence and Deterministic DOM Automation."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from nova.control.browsers.models import BrowserActionResult, BrowserTab, DOMElement
from nova.control.browsers.playwright_manager import PlaywrightBrowserController, SUSPICIOUS_PHRASES
from nova.errors import SecurityError
from nova.tools.browser import (
    BROWSER_TOOL_SPECS,
    browser_click,
    browser_extract,
    browser_fill_form,
    browser_hover,
    browser_inspect_page,
    browser_list_tabs,
    browser_navigate,
    browser_new_tab,
    browser_select,
)
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry


def test_browser_models_validation():
    """Verify serialization and defaults of browser data models."""
    tab = BrowserTab(tab_id="tab_1", title="Google", url="https://google.com", is_active=True)
    assert tab.tab_id == "tab_1"
    assert tab.title == "Google"
    assert tab.url == "https://google.com"
    assert tab.is_active is True

    data = tab.model_dump()
    assert data["tab_id"] == "tab_1"
    assert data["is_active"] is True

    el = DOMElement(
        ref="el_0",
        role="button",
        name="Submit",
        tag="button",
        visible=True,
        enabled=True,
        selector_strategy="index",
        is_sensitive=False,
    )
    assert el.ref == "el_0"
    assert el.name == "Submit"
    assert el.is_sensitive is False

    res = BrowserActionResult(success=True, state_changed=True, navigation_occurred=False)
    assert res.success is True
    assert res.error is None


def test_prompt_injection_heuristic():
    """Verify that prompt injection patterns raise SecurityError."""
    controller = PlaywrightBrowserController()

    # Clean text should pass
    controller._check_prompt_injection("Welcome to the website. Please log in.")

    # Suspicious phrases must raise SecurityError
    for phrase in SUSPICIOUS_PHRASES:
        with pytest.raises(SecurityError) as exc_info:
            controller._check_prompt_injection(f"Some preamble. {phrase.upper()} and do something bad.")
        assert "Safety violation" in str(exc_info.value)


def test_download_quarantine_heuristic():
    """Verify executable downloads are detected and handled."""
    controller = PlaywrightBrowserController()

    mock_download = MagicMock()
    mock_download.suggested_filename = "malware.exe"
    # Should not raise, but log quarantine
    controller._handle_download(mock_download)

    mock_download.suggested_filename = "document.pdf"
    controller._handle_download(mock_download)


def test_browser_tools_registration(tool_registry: ToolRegistry):
    """Verify browser tools are correctly registered with risk metadata."""
    from nova.tools.browser import register_browser_tools
    register_browser_tools(tool_registry)

    tool_names = [meta.name for meta, _ in BROWSER_TOOL_SPECS]
    assert "browser_new_tab" in tool_names
    assert "browser_list_tabs" in tool_names
    assert "browser_navigate" in tool_names
    assert "browser_inspect_page" in tool_names
    assert "browser_click" in tool_names
    assert "browser_fill_form" in tool_names
    assert "browser_select" in tool_names
    assert "browser_hover" in tool_names
    assert "browser_extract" in tool_names

    # Check risk levels in registry
    for meta, _ in BROWSER_TOOL_SPECS:
        registered = tool_registry.get_metadata(meta.name)
        assert registered is not None
        assert registered.risk_level in [ToolRiskLevel.READ_ONLY, ToolRiskLevel.LOW]


@pytest.mark.asyncio
async def test_browser_tools_invocation_mocked():
    """Verify tool wrappers correctly call controller methods."""
    mock_controller = MagicMock()
    mock_controller.new_tab = AsyncMock(
        return_value=BrowserTab(tab_id="tab_123", title="Example", url="https://example.com", is_active=True)
    )
    mock_controller.list_tabs = AsyncMock(
        return_value=[BrowserTab(tab_id="tab_123", title="Example", url="https://example.com", is_active=True)]
    )
    mock_controller.navigate = AsyncMock(
        return_value=BrowserActionResult(success=True, state_changed=True, navigation_occurred=True)
    )
    mock_controller.inspect = AsyncMock(
        return_value=[
            DOMElement(
                ref="el_0",
                role="button",
                name="Sign in",
                tag="button",
                visible=True,
                enabled=True,
                selector_strategy="index",
                is_sensitive=False,
            )
        ]
    )
    mock_controller.click = AsyncMock(return_value=BrowserActionResult(success=True, state_changed=True))
    mock_controller.fill = AsyncMock(return_value=BrowserActionResult(success=True, state_changed=True))
    mock_controller.select = AsyncMock(return_value=BrowserActionResult(success=True, state_changed=True))
    mock_controller.hover = AsyncMock(return_value=BrowserActionResult(success=True, state_changed=True))
    mock_controller.extract = AsyncMock(return_value="Extracted page text")

    with patch("nova.tools.browser.get_browser_controller", return_value=mock_controller):
        res = await browser_new_tab(url="https://example.com")
        assert res["tab_id"] == "tab_123"
        mock_controller.new_tab.assert_awaited_once_with("https://example.com")

        res = await browser_list_tabs()
        assert len(res["tabs"]) == 1
        assert res["tabs"][0]["tab_id"] == "tab_123"

        res = await browser_navigate(tab_id="tab_123", url="https://example.com")
        assert res["success"] is True

        res = await browser_inspect_page(tab_id="tab_123")
        assert len(res["elements"]) == 1
        assert res["elements"][0]["ref"] == "el_0"

        res = await browser_click(tab_id="tab_123", ref="el_0")
        assert res["success"] is True

        res = await browser_fill_form(tab_id="tab_123", ref="el_0", value="test")
        assert res["success"] is True

        res = await browser_select(tab_id="tab_123", ref="el_0", value="opt1")
        assert res["success"] is True

        res = await browser_hover(tab_id="tab_123", ref="el_0")
        assert res["success"] is True

        res = await browser_extract(tab_id="tab_123")
        assert res["content"] == "Extracted page text"


@pytest.mark.asyncio
async def test_browser_extract_security_error_handling():
    """Verify tool wrapper catches SecurityError on prompt injection."""
    mock_controller = MagicMock()
    mock_controller.extract = AsyncMock(side_effect=SecurityError("Safety violation: prompt injection detected."))

    with patch("nova.tools.browser.get_browser_controller", return_value=mock_controller):
        res = await browser_extract(tab_id="tab_123")
        assert res.get("safety_violation") is True
        assert "Safety violation" in res.get("error", "")


@pytest.mark.asyncio
async def test_browser_controller_tab_lifecycle():
    """Verify PlaywrightBrowserController tab management methods with mocked page."""
    controller = PlaywrightBrowserController()

    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="Mock Title")
    mock_page.url = "https://mock.url"
    mock_page.is_closed = MagicMock(return_value=False)
    mock_page.close = AsyncMock()
    mock_page.bring_to_front = AsyncMock()

    controller.pages["tab_1"] = mock_page

    tabs = await controller.list_tabs()
    assert len(tabs) == 1
    assert tabs[0].tab_id == "tab_1"
    assert tabs[0].title == "Mock Title"

    assert await controller.focus_tab("tab_1") is True
    mock_page.bring_to_front.assert_awaited_once()

    assert await controller.close_tab("tab_1") is True
    mock_page.close.assert_awaited_once()
    assert "tab_1" not in controller.pages

    assert await controller.close_tab("non_existent") is False
