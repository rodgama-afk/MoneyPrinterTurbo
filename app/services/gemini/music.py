"""Lyria 3 clip music wrapper — a fixed ~30s instrumental MP3 from a prompt.

Best-effort like every other gemini stage: on any failure it logs and returns
``None`` so the pipeline falls back to local/random BGM instead of crashing.

Lyria is SYNCHRONOUS — ``interactions.create`` returns the finished audio, so
there is no ``gemini.poll`` here. All control (tempo/genre/mood/structure) is
expressed in the natural-language ``prompt``; there are no tempo/seed/negative
params. Output is MP3 (48kHz), written under ``resource/songs`` so the existing
``video.get_bgm_file`` / ``_BGM_EXTENSIONS=('.mp3',)`` accept it.
"""

from __future__ import annotations

import base64
import hashlib
import os

from loguru import logger

from app.services import gemini
from app.utils import utils


def generate_music(
    prompt: str,
    *,
    task_id: str | None = None,
    model: str = "lyria-3-clip-preview",
) -> str | None:
    """Generate a fixed ~30s instrumental music clip (MP3 48kHz) from a
    natural-language prompt. Returns a LOCAL ``.mp3`` path (under
    ``resource/songs``) or ``None`` on failure."""
    try:
        c = gemini.client()
        interaction = c.interactions.create(model=model, input=prompt)

        audio = getattr(interaction, "output_audio", None)
        if not audio:
            logger.warning(f"[{task_id}] Lyria returned no output_audio for model {model}")
            return None

        # google-genai objects expose fields as attributes; be defensive about
        # dict-style access in case a raw response dict slips through.
        data = getattr(audio, "data", None)
        if data is None and isinstance(audio, dict):
            data = audio.get("data")
        if not data:
            logger.warning(f"[{task_id}] Lyria output_audio had no data")
            return None

        raw = base64.b64decode(data)

        # Unique name from the prompt so repeat prompts overwrite rather than pile up.
        name = f"lyria-{hashlib.sha1(prompt.encode('utf-8')).hexdigest()[:12]}.mp3"
        out_path = os.path.join(utils.song_dir(), name)
        with open(out_path, "wb") as f:
            f.write(raw)

        logger.info(f"[{task_id}] Lyria music written: {out_path} ({len(raw)} bytes)")
        return os.path.abspath(out_path)
    except Exception as e:
        if gemini.is_access_error(e):
            logger.warning(f"[{task_id}] Lyria model not accessible on this key: {e}")
        else:
            logger.error(f"[{task_id}] Lyria music generation failed: {e}")
        return None


if __name__ == "__main__":
    # ponytail: offline self-check of the parsing/write path — no paid API call.
    # Fake an interaction whose output_audio.data is base64 MP3 bytes.
    class _Audio:
        data = base64.b64encode(b"ID3fake-mp3-bytes").decode()

    class _Interaction:
        output_audio = _Audio()

    class _Client:
        class interactions:  # noqa: N801 - mimic SDK namespace
            @staticmethod
            def create(model, input):
                return _Interaction()

    gemini.client = lambda: _Client()  # type: ignore[assignment]
    p = generate_music("calm lo-fi piano, 90 bpm", task_id="selfcheck")
    assert p and p.endswith(".mp3") and os.path.isfile(p), p
    assert open(p, "rb").read() == b"ID3fake-mp3-bytes"
    os.remove(p)

    # Falsy output_audio -> None
    _Interaction.output_audio = None  # type: ignore[assignment]
    assert generate_music("x", task_id="selfcheck") is None
    print("music.py self-check OK")
