"""Deep Research wrapper (optional pipeline stage 1).

Runs an agentic, long-running deep-research task on a subject and returns the
final cited report text (to feed the script stage). This is LONG, ASYNC and
EXPENSIVE — the caller keeps it OFF by default. Best-effort like every other
gemini stage: on any failure/timeout it logs and returns ``None`` so the
pipeline degrades to script-only.
"""

from __future__ import annotations

from typing import Callable, Optional

from loguru import logger

from app.services import gemini


def _report_text(interaction) -> Optional[str]:
    """Pull the final report text out of ``interaction.steps[-1].content[0]``.

    Steps/content may be SDK objects or plain dicts; content items carry a
    ``type == "text"`` and a ``text`` field. Returns the first text found, or
    ``None`` if the shape isn't as expected.
    """
    steps = getattr(interaction, "steps", None)
    if steps is None and isinstance(interaction, dict):
        steps = interaction.get("steps")
    if not steps:
        return None
    last = steps[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    if not content:
        return None
    for item in content:
        itype = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
        if itype == "text":
            text = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
            if text:
                return text
    # No item advertised type=="text"; fall back to the first thing with .text.
    for item in content:
        text = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
        if text:
            return text
    return None


def deep_research(
    subject: str,
    *,
    model: str = "deep-research-preview-04-2026",
    thinking_summaries: str = "auto",
    visualization: str = "off",
    on_tick: Optional[Callable[[object], None]] = None,
    timeout: float = 3600,
) -> Optional[str]:
    """Run an agentic deep-research task on ``subject`` and return the final
    cited report TEXT (to feed the script stage), or ``None`` on failure.

    This is a LONG, ASYNC, EXPENSIVE stage — the caller keeps it OFF by default.
    """
    try:
        c = gemini.client()
        interaction = c.interactions.create(
            input=subject,
            agent=model,
            background=True,  # background REQUIRES store=True
            store=True,
            agent_config={
                "type": "deep-research",
                "thinking_summaries": thinking_summaries,
                "visualization": visualization,
            },
        )
        interaction = gemini.poll(
            lambda: c.interactions.get(interaction.id),
            lambda i: getattr(i, "status", None) in ("completed", "failed"),
            on_tick=on_tick,
            interval=15,
            timeout=timeout,
        )
        if getattr(interaction, "status", None) != "completed":
            logger.error(f"deep research did not complete: status={getattr(interaction, 'status', None)}")
            return None
        text = _report_text(interaction)
        if not text:
            logger.error("deep research completed but no report text was found")
            return None
        return text
    except Exception as e:
        if gemini.is_access_error(e):
            logger.error(f"deep research unavailable on this key: {e}")
        else:
            logger.exception(f"deep research failed: {e}")
        return None
