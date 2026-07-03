"""Veo text-to-video wrapper (best-effort).

Generates one ~8s clip per prompt via the ``google-genai`` long-running video
operation and saves each to the same ``storage/cache_videos`` dir that
``material.save_video`` writes stock clips to, so they slot straight into the
existing pipeline. On ANY failure returns ``[]`` and the caller falls back to
stock footage.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from loguru import logger
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.services import gemini
from app.utils import utils


def _openable(path: str) -> bool:
    """True if moviepy can open the file with duration>0 and fps>0."""
    clip = None
    try:
        clip = VideoFileClip(path)
        return bool(clip.duration and clip.duration > 0 and clip.fps and clip.fps > 0)
    except Exception as e:
        logger.warning(f"invalid veo clip: {path} => {e}")
        return False
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass


def generate_clips(
    prompts: list[str],
    *,
    task_id: str,
    model: str = "veo-3.1-fast-generate-preview",
    aspect_ratio: str = "9:16",
    resolution: str = "720p",
    duration_seconds: str = "8",
    negative_prompt: str = "blurry, low quality, distorted, watermark",
    generate_audio: bool = False,
    enhance_prompt: bool = True,
    person_generation: str = "allow_adult",
    seed: int | None = None,
    on_tick: Optional[Callable[[object], None]] = None,
) -> list[str]:
    """Generate ONE ~8s clip per prompt. Returns a list of LOCAL .mp4 paths
    (each openable by moviepy with duration>0 and fps>0). On ANY failure
    returns [] so the caller falls back to stock footage."""
    try:
        if not gemini.available():
            logger.warning("veo: no gemini_api_key configured, skipping")
            return []

        from google.genai import types

        save_dir = utils.storage_dir("cache_videos", create=True)
        c = gemini.client()
        paths: list[str] = []

        for i, prompt in enumerate(prompts):
            out_path = os.path.join(save_dir, f"veo-{task_id}-{i}.mp4")
            try:
                op = c.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio=aspect_ratio,
                        resolution=resolution,
                        duration_seconds=duration_seconds,
                        number_of_videos=1,
                        negative_prompt=negative_prompt,
                        generate_audio=generate_audio,
                        enhance_prompt=enhance_prompt,
                        person_generation=person_generation,
                        seed=seed,  # None is accepted (optional field)
                    ),
                )
                op = gemini.poll(
                    lambda: c.operations.get(op),
                    lambda o: o.done,
                    on_tick=on_tick,
                )
                video = op.response.generated_videos[0]
                c.files.download(file=video.video)
                video.video.save(out_path)

                if _openable(out_path):
                    logger.success(f"veo clip saved: {out_path}")
                    paths.append(out_path)
                else:
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
            except Exception as e:
                # Skip this clip; if it's an access error every clip will fail
                # anyway, so bail early to fall back to stock footage.
                logger.error(f"veo clip {i} failed: {e}")
                if gemini.is_access_error(e):
                    logger.warning("veo: access error, aborting Veo generation")
                    break

        return paths
    except Exception as e:
        logger.error(f"veo generate_clips failed: {e}")
        return []


if __name__ == "__main__":
    # ponytail: no live gen (paid); only checks the no-key guard returns [].
    from app.config import config

    saved = dict(config.app)
    config.app["gemini_api_key"] = ""
    try:
        assert generate_clips(["a cat"], task_id="selftest") == []
        print("ok: no-key guard returns []")
    finally:
        config.app.clear()
        config.app.update(saved)
