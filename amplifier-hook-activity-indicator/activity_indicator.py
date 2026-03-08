"""Activity indicator hook - shows spinner during long-running operations."""

import sys
import threading
import time
from typing import Any, Callable

from amplifier_core.models import HookResult

# Spinner frames (braille pattern for smooth animation)
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class ActivityIndicator:
    """Thread-safe activity indicator that shows a spinner."""

    def __init__(self):
        self._active = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._message = ""

    def start(self, message: str = ""):
        """Start the spinner."""
        with self._lock:
            if self._active:
                self._message = message  # Update message if already running
                return
            self._active = True
            self._message = message
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the spinner and clear the line."""
        with self._lock:
            if not self._active:
                return
            self._active = False
        if self._thread:
            self._thread.join(timeout=0.5)
        sys.stderr.write("\r\033[K")  # Clear spinner line
        sys.stderr.flush()

    def _spin(self):
        """Spinner animation loop."""
        frame_idx = 0
        while self._active:
            frame = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
            msg = f" {self._message}" if self._message else ""
            sys.stderr.write(f"\r{frame}{msg}")
            sys.stderr.flush()
            frame_idx += 1
            time.sleep(0.08)


_indicator = ActivityIndicator()


# --- Session Lifecycle (ACTUALLY EMITTED by kernel) ---


async def on_session_start(event: str, data: dict[str, Any]) -> HookResult:
    """Start spinner when session begins - this IS emitted by kernel."""
    _indicator.start("processing...")
    return HookResult(action="continue", suppress_output=True)


async def on_session_end(event: str, data: dict[str, Any]) -> HookResult:
    """Stop spinner when session ends."""
    _indicator.stop()
    return HookResult(action="continue", suppress_output=True)


# --- Provider/LLM (ACTUALLY EMITTED) ---


async def on_provider_request(event: str, data: dict[str, Any]) -> HookResult:
    """Start spinner when LLM request begins."""
    _indicator.start("thinking...")
    return HookResult(action="continue", suppress_output=True)


async def on_provider_response(event: str, data: dict[str, Any]) -> HookResult:
    """Stop spinner when LLM response arrives."""
    _indicator.stop()
    return HookResult(action="continue", suppress_output=True)


async def on_provider_retry(event: str, data: dict[str, Any]) -> HookResult:
    """Show retry activity."""
    attempt = data.get("attempt", "")
    _indicator.start(f"retrying{f' ({attempt})' if attempt else ''}...")
    return HookResult(action="continue", suppress_output=True)


async def on_provider_throttle(event: str, data: dict[str, Any]) -> HookResult:
    """Show rate limit wait."""
    _indicator.start("rate limited, waiting...")
    return HookResult(action="continue", suppress_output=True)


async def on_provider_error(event: str, data: dict[str, Any]) -> HookResult:
    """Stop spinner on provider error."""
    _indicator.stop()
    return HookResult(action="continue", suppress_output=True)


# --- Tool Execution (ACTUALLY EMITTED) ---


async def on_tool_pre(event: str, data: dict[str, Any]) -> HookResult:
    """Start spinner when tool execution begins."""
    tool_name = data.get("tool_name", "tool")
    _indicator.start(f"running {tool_name}...")
    return HookResult(action="continue", suppress_output=True)


async def on_tool_post(event: str, data: dict[str, Any]) -> HookResult:
    """Stop spinner when tool completes."""
    _indicator.stop()
    return HookResult(action="continue", suppress_output=True)


async def on_tool_error(event: str, data: dict[str, Any]) -> HookResult:
    """Stop spinner on tool error."""
    _indicator.stop()
    return HookResult(action="continue", suppress_output=True)


async def mount(coordinator, config: dict) -> Callable | None:
    """Register activity indicator hooks for events ACTUALLY emitted by kernel/orchestrator."""
    handlers = [
        # Session lifecycle (emitted by kernel session.py)
        coordinator.hooks.register("session:start", on_session_start, priority=1),
        coordinator.hooks.register("session:end", on_session_end, priority=99),
        # Provider/LLM (emitted by providers)
        coordinator.hooks.register("provider:request", on_provider_request, priority=1),
        coordinator.hooks.register(
            "provider:response", on_provider_response, priority=1
        ),
        coordinator.hooks.register("provider:retry", on_provider_retry, priority=1),
        coordinator.hooks.register(
            "provider:throttle", on_provider_throttle, priority=1
        ),
        coordinator.hooks.register("provider:error", on_provider_error, priority=1),
        # Tool execution (emitted by tool dispatcher)
        coordinator.hooks.register("tool:pre", on_tool_pre, priority=1),
        coordinator.hooks.register("tool:post", on_tool_post, priority=1),
        coordinator.hooks.register("tool:error", on_tool_error, priority=1),
    ]

    def cleanup():
        _indicator.stop()
        for unregister in handlers:
            unregister()

    return cleanup
