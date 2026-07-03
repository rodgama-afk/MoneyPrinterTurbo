"""Shared helpers for the Google generative pipeline (``google-genai`` SDK).

All five stages — deep research, script, video (Veo), TTS, music (Lyria) —
authenticate with the SAME key (``config.app['gemini_api_key']``) and use the
new ``from google import genai`` SDK (>= 2.10).

Every wrapper built on top of this module is **best-effort**: on any failure it
logs and returns ``None``/``[]`` so the video pipeline degrades to its fallback
(stock footage / local BGM / edge-tts) instead of crashing the whole run.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from loguru import logger

from app.config import config


def gemini_api_key() -> str:
    """The single Google API key shared by every stage."""
    return (config.app.get("gemini_api_key") or "").strip()


def available() -> bool:
    """True when a key is configured (does not verify allowlist/billing)."""
    return bool(gemini_api_key())


def client():
    """A fresh ``google.genai`` client. Imported lazily so the app still starts
    even if ``google-genai`` isn't installed (the stages just fall back)."""
    from google import genai

    return genai.Client(api_key=gemini_api_key())


def is_access_error(err: Exception) -> bool:
    """True when the failure is a missing-access / not-allowlisted / unknown-model
    error (401/403/404, PERMISSION_DENIED, NOT_FOUND, UNAUTHENTICATED) — i.e. this
    model isn't usable on this key, so the caller should fall back rather than
    retry. Transient 5xx/429/network errors return False."""
    code = getattr(err, "code", None) or getattr(err, "status_code", None)
    if code in (401, 403, 404):
        return True
    msg = str(err).upper()
    return any(
        marker in msg
        for marker in ("PERMISSION_DENIED", "NOT_FOUND", "UNAUTHENTICATED", " 401", " 403", " 404")
    )


# ponytail: naive fixed-interval poll; add exponential backoff if 429s appear.
def poll(
    fetch: Callable[[], object],
    is_done: Callable[[object], bool],
    on_tick: Optional[Callable[[object], None]] = None,
    interval: float = 10.0,
    timeout: float = 3600.0,
):
    """Drive a long-running operation to completion.

    ``fetch()`` returns the current state object, ``is_done(obj)`` decides when to
    stop, and ``on_tick(obj)`` (optional) reports progress on every poll. Raises
    ``TimeoutError`` once ``timeout`` seconds elapse.

    Used by Veo (``client.operations.get``) and Deep Research
    (``client.interactions.get``), which have different poll surfaces.
    """
    started = time.time()
    obj = fetch()
    while not is_done(obj):
        if time.time() - started > timeout:
            raise TimeoutError("gemini long-running operation exceeded timeout")
        if on_tick:
            try:
                on_tick(obj)
            except Exception:  # progress reporting must never break the poll loop
                pass
        time.sleep(interval)
        obj = fetch()
    return obj
