"""History service for generated videos.

Reads generated videos from ``storage/tasks/*/final-*.mp4`` and enriches each
with the content already saved at generation time in ``script.json``
(subject / source / aspect / language / script / search terms). User-editable
metadata (tags, favorite, rating, friendly title) lives in a single JSON store
``storage/history_meta.json`` keyed by ``<task_id>/<filename>``.

Thumbnails are extracted once with ffmpeg and cached next to each video.
Tag suggestion reuses the app's configured LLM (text only) via
``llm._generate_response`` — no vision/API-vision needed.
"""

import glob
import json
import os
import subprocess
from datetime import datetime

from loguru import logger

from app.utils import utils

_META_FILE = os.path.join(utils.storage_dir(), "history_meta.json")


def _load_meta() -> dict:
    try:
        with open(_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_meta(meta: dict) -> None:
    os.makedirs(os.path.dirname(_META_FILE), exist_ok=True)
    tmp = _META_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _META_FILE)  # atomic write


def _video_id(video_path: str) -> str:
    task_id = os.path.basename(os.path.dirname(video_path))
    return f"{task_id}/{os.path.basename(video_path)}"


def _read_script_json(task_dir: str) -> dict:
    try:
        with open(os.path.join(task_dir, "script.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def thumbnail(video_path: str) -> str | None:
    """Return a cached JPG thumbnail for the video, generating it once via ffmpeg."""
    thumb = os.path.splitext(video_path)[0] + ".thumb.jpg"
    try:
        if os.path.exists(thumb) and os.path.getmtime(thumb) >= os.path.getmtime(video_path):
            return thumb
    except OSError:
        pass
    try:
        ff = utils.get_ffmpeg_binary()
        subprocess.run(
            [ff, "-y", "-ss", "1", "-i", video_path,
             "-frames:v", "1", "-vf", "scale=360:-1", thumb],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )
        return thumb if os.path.exists(thumb) else None
    except Exception as e:  # ffmpeg missing / unreadable video — degrade gracefully
        logger.warning(f"thumbnail failed for {video_path}: {e}")
        return None


def list_videos() -> list[dict]:
    """All generated videos, newest first, each merged with content + user metadata."""
    tasks_root = utils.task_dir()
    files = glob.glob(os.path.join(tasks_root, "*", "final-*.mp4"))
    files.sort(key=os.path.getmtime, reverse=True)

    meta = _load_meta()
    script_cache: dict[str, dict] = {}
    out: list[dict] = []
    for p in files:
        task_dir = os.path.dirname(p)
        task_id = os.path.basename(task_dir)
        if task_dir not in script_cache:
            script_cache[task_dir] = _read_script_json(task_dir)
        sj = script_cache[task_dir]
        params = sj.get("params") or {}
        vid = _video_id(p)
        m = meta.get(vid, {})
        out.append(
            {
                "id": vid,
                "task_id": task_id,
                "filename": os.path.basename(p),
                "path": p,
                "mtime": datetime.fromtimestamp(os.path.getmtime(p)),
                "size_mb": os.path.getsize(p) / (1024 * 1024),
                "subject": (params.get("video_subject") or "").strip(),
                "source": params.get("video_source") or "?",
                "aspect": str(params.get("video_aspect") or "?"),
                "language": params.get("video_language") or "",
                "script": sj.get("script") or "",
                "terms": sj.get("search_terms") or [],
                "title": m.get("title") or "",
                "tags": list(m.get("tags") or []),
                "favorite": bool(m.get("favorite")),
                "rating": int(m.get("rating") or 0),
            }
        )
    return out


def set_meta(video_id: str, **fields) -> None:
    meta = _load_meta()
    entry = meta.get(video_id, {})
    entry.update(fields)
    meta[video_id] = entry
    _save_meta(meta)


def all_tags() -> list[str]:
    tags: set[str] = set()
    for e in _load_meta().values():
        for t in e.get("tags", []):
            tags.add(t)
    return sorted(tags, key=str.lower)


def delete_video(video_id: str, video_path: str) -> None:
    """Delete the video file + its thumbnail and drop its metadata entry."""
    for f in (video_path, os.path.splitext(video_path)[0] + ".thumb.jpg"):
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception as e:
            logger.warning(f"delete failed for {f}: {e}")
    meta = _load_meta()
    if video_id in meta:
        del meta[video_id]
        _save_meta(meta)


def suggest_tags(subject: str, script: str) -> list[str]:
    """Suggest 3-6 short tags from the subject + script via the configured LLM (text)."""
    from app.services import llm  # local import avoids a circular import at module load

    prompt = (
        "Gere de 3 a 6 tags curtas (1 a 2 palavras cada), em português, para catalogar "
        "um vídeo de marketing. Responda APENAS as tags separadas por vírgula, "
        "sem numeração e sem explicações.\n\n"
        f"Assunto: {subject}\nRoteiro: {script[:800]}"
    )
    try:
        resp = llm._generate_response(prompt) or ""
    except Exception as e:
        logger.error(f"suggest_tags failed: {e}")
        return []
    parts = [t for t in resp.replace("\n", ",").split(",")]
    tags: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        t = raw.strip(" #.-\t*").strip()
        if t and t.lower() not in seen and len(t) <= 30:
            seen.add(t.lower())
            tags.append(t)
    return tags[:6]


if __name__ == "__main__":
    # ponytail: offline smoke check — no ffmpeg/LLM calls required.
    vids = list_videos()
    print(f"[selfcheck] {len(vids)} vídeo(s); tags catalogadas: {all_tags()}")
    assert isinstance(vids, list)
    print("history.py self-check OK")
