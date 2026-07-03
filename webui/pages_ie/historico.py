import os

import streamlit as st

from app.services import history

st.title("🗂️ Histórico")
st.caption("Vídeos gerados — miniatura, tags, filtros e favoritos")

videos = history.list_videos()
if not videos:
    st.info(
        "Nenhum vídeo gerado ainda. Gere o primeiro na página **Gerar Vídeo** ou no **Dashboard**."
    )
    st.stop()

# ---------------- Filtros ----------------
tag_options = sorted({t for v in videos for t in v["tags"]}, key=str.lower)
source_options = sorted({v["source"] for v in videos})
aspect_options = sorted({v["aspect"] for v in videos})

with st.container(border=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input(
        "🔎 Buscar (assunto, roteiro, título, tag)", key="hist_q"
    ).strip().lower()
    sel_tags = c2.multiselect("Tags", tag_options, key="hist_tags")
    sort_by = c3.selectbox(
        "Ordenar", ["Mais recentes", "Melhor avaliados", "Favoritos primeiro"], key="hist_sort"
    )
    c4, c5, c6, c7 = st.columns(4)
    sel_source = c4.selectbox("Fonte", ["Todas"] + source_options, key="hist_src")
    sel_aspect = c5.selectbox("Formato", ["Todos"] + aspect_options, key="hist_aspect")
    only_fav = c6.checkbox("⭐ Só favoritos", key="hist_fav")
    date_range = c7.date_input("Período", value=(), key="hist_date")


def _match(v) -> bool:
    if query:
        blob = " ".join(
            [v["subject"], v["script"], v["title"], " ".join(v["tags"])]
        ).lower()
        if query not in blob:
            return False
    if sel_tags and not set(sel_tags).issubset(set(v["tags"])):
        return False
    if sel_source != "Todas" and v["source"] != sel_source:
        return False
    if sel_aspect != "Todos" and v["aspect"] != sel_aspect:
        return False
    if only_fav and not v["favorite"]:
        return False
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d0, d1 = date_range
        if not (d0 <= v["mtime"].date() <= d1):
            return False
    return True


filtered = [v for v in videos if _match(v)]
if sort_by == "Melhor avaliados":
    filtered.sort(key=lambda v: (v["rating"], v["mtime"]), reverse=True)
elif sort_by == "Favoritos primeiro":
    filtered.sort(key=lambda v: (v["favorite"], v["mtime"]), reverse=True)

st.write(f"**{len(filtered)}** de {len(videos)} vídeo(s).")


# ---------------- Callbacks (persistem em history_meta.json) ----------------
def _save_tags(vid):
    raw = st.session_state.get(f"tags_{vid}", "")
    history.set_meta(vid, tags=[t.strip() for t in raw.split(",") if t.strip()])


def _save_title(vid):
    history.set_meta(vid, title=st.session_state.get(f"title_{vid}", "").strip())


def _save_fav(vid):
    history.set_meta(vid, favorite=bool(st.session_state.get(f"fav_{vid}")))


def _save_rating(vid):
    r = st.session_state.get(f"rate_{vid}")
    history.set_meta(vid, rating=(int(r) + 1) if r is not None else 0)


def _suggest(vid, subject, script):
    suggested = history.suggest_tags(subject, script)
    if not suggested:
        return
    existing = [t.strip() for t in st.session_state.get(f"tags_{vid}", "").split(",") if t.strip()]
    merged = existing + [t for t in suggested if t not in existing]
    st.session_state[f"tags_{vid}"] = ", ".join(merged)
    history.set_meta(vid, tags=merged)


def _delete(vid, path):
    history.delete_video(vid, path)


def _start_play(vid):
    st.session_state[f"play_{vid}"] = True


def _stop_play(vid):
    st.session_state[f"play_{vid}"] = False


# ---------------- Lista (miniatura à esquerda) ----------------
for v in filtered:
    vid = v["id"]
    # seed widget state once (lets "Sugerir tags"/rating update it via callbacks)
    st.session_state.setdefault(f"tags_{vid}", ", ".join(v["tags"]))
    if v["rating"] and f"rate_{vid}" not in st.session_state:
        st.session_state[f"rate_{vid}"] = v["rating"] - 1

    with st.container(border=True):
        left, right = st.columns([1, 3])

        if st.session_state.get(f"play_{vid}"):
            left.video(v["path"])
            left.button(
                "⏹ Fechar", key=f"stop_{vid}", on_click=_stop_play, args=(vid,), width="stretch"
            )
        else:
            thumb = history.thumbnail(v["path"])
            if thumb:
                left.image(thumb, width="stretch")
            else:
                left.markdown("### 🎬")
            left.button(
                "▶ Reproduzir", key=f"playbtn_{vid}", on_click=_start_play, args=(vid,), width="stretch"
            )
        star = "⭐ " if v["favorite"] else ""
        left.caption(f"{star}{v['mtime']:%d/%m/%Y %H:%M}")

        right.text_input(
            "Título",
            value=v["title"],
            key=f"title_{vid}",
            on_change=_save_title,
            args=(vid,),
            placeholder=(v["subject"][:60] or v["filename"]),
        )
        badges = f"`{v['source']}` · `{v['aspect']}` · {v['size_mb']:.1f} MB"
        if v["language"]:
            badges += f" · {v['language']}"
        right.caption(badges)
        if v["subject"]:
            right.caption(f"📝 {v['subject']}")

        right.text_input(
            "Tags (separadas por vírgula)",
            key=f"tags_{vid}",
            on_change=_save_tags,
            args=(vid,),
        )

        a1, a2, a3, a4, a5 = right.columns([1.3, 1.5, 1.2, 0.9, 0.8])
        a1.checkbox(
            "⭐ Favorito", value=v["favorite"], key=f"fav_{vid}", on_change=_save_fav, args=(vid,)
        )
        a2.button(
            "✨ Sugerir tags",
            key=f"sug_{vid}",
            on_click=_suggest,
            args=(vid, v["subject"], v["script"]),
            width="stretch",
        )
        with a3:
            st.caption("Nota")
            st.feedback("stars", key=f"rate_{vid}", on_change=_save_rating, args=(vid,))
        with open(v["path"], "rb") as fh:
            a4.download_button(
                "⬇",
                fh,
                file_name=f"{(v['title'] or v['task_id'][:8])}-{v['filename']}",
                key=f"dl_{vid}",
                width="stretch",
            )
        with a5.popover("🗑"):
            st.write("Excluir este vídeo permanentemente?")
            st.button(
                "Confirmar exclusão",
                key=f"del_{vid}",
                on_click=_delete,
                args=(vid, v["path"]),
                type="primary",
            )
