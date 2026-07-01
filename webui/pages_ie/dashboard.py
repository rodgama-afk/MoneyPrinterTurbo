import glob
import os
from datetime import datetime

import streamlit as st

from app.config import config
from app.services import usage

st.title("📊 Dashboard")
st.caption("Visão geral — Geração de Vídeo - IE (marketing)")

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
_TASKS = os.path.join(_ROOT, "storage", "tasks")


def _list_videos():
    files = glob.glob(os.path.join(_TASKS, "*", "final-*.mp4"))
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def _key_ok(v):
    if isinstance(v, list):
        return any(bool(x) for x in v)
    return bool(v)


videos = _list_videos()
tot = usage.totals()

# ---- stats ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vídeos gerados", len(videos))
c2.metric("Chamadas de IA", tot["calls"])
c3.metric("Tokens usados", f'{tot["total_tokens"]:,}'.replace(",", "."))
c4.metric("Provedor atual", config.app.get("llm_provider", "-"))

st.divider()

# ---- provider status ----
st.subheader("Status dos provedores")
status_rows = [
    ("Gemini (IA)", _key_ok(config.app.get("gemini_api_key"))),
    ("Claude (IA)", _key_ok(config.app.get("claude_api_key"))),
    ("NVIDIA (IA)", _key_ok(config.app.get("nvidia_api_key"))),
    ("OpenAI (IA)", _key_ok(config.app.get("openai_api_key"))),
    ("Pexels (vídeo)", _key_ok(config.app.get("pexels_api_keys"))),
    ("Pixabay (vídeo)", _key_ok(config.app.get("pixabay_api_keys"))),
]
cols = st.columns(3)
for i, (name, ok) in enumerate(status_rows):
    cols[i % 3].write(f'{"✅" if ok else "⬜"} {name}')

st.divider()

# ---- token usage per key ----
st.subheader("Uso de tokens por chave configurada")
summary = usage.summary_by_key()
if summary:
    st.dataframe(
        [
            {
                "Provedor": r["provider"],
                "Chave": r["key"],
                "Modelo": r["model"],
                "Chamadas": r["calls"],
                "Tokens entrada": r["input_tokens"],
                "Tokens saída": r["output_tokens"],
                "Total": r["total_tokens"],
            }
            for r in summary
        ],
        width="stretch",
        hide_index=True,
    )
else:
    st.info("Nenhum uso registrado ainda. Gere um roteiro ou vídeo para começar a contabilizar tokens.")

st.divider()

# ---- quick generation ----
st.subheader("Geração rápida")
with st.form("quick_gen"):
    subject = st.text_input("Tópico do vídeo", placeholder="ex.: os benefícios do intercâmbio estudantil")
    lang = st.selectbox(
        "Idioma do roteiro",
        ["", "pt-BR", "es", "en-US"],
        format_func=lambda x: "Detectar automático" if x == "" else x,
    )
    submitted = st.form_submit_button("Gerar agora", type="primary")

if submitted:
    if not subject.strip():
        st.warning("Digite um tópico.")
    else:
        from app.models.schema import VideoParams
        from app.services import task as tm
        from app.utils import utils

        params = VideoParams(
            video_subject=subject.strip(),
            video_language=lang,
            paragraph_number=1,
        )
        task_id = utils.get_uuid()
        with st.spinner("Gerando vídeo… isso pode levar alguns minutos. Não feche a página."):
            try:
                result = tm.start(task_id=task_id, params=params, stop_at="video")
            except Exception as e:
                result = None
                st.error(f"Falha na geração: {e}")
        if result and result.get("videos"):
            st.success("Vídeo gerado com sucesso!")
            st.video(result["videos"][0])
        elif result is not None:
            st.warning("Processo concluído, mas nenhum vídeo foi retornado. Confira as chaves em Configurações.")

st.divider()

# ---- recent videos ----
st.subheader("Vídeos recentes")
if not videos:
    st.info("Nenhum vídeo ainda. Use a Geração rápida acima ou a página Gerar Vídeo.")
else:
    for path in videos[:6]:
        task_id = os.path.basename(os.path.dirname(path))
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        st.markdown(f"**tarefa `{task_id[:8]}`** · {mtime:%d/%m/%Y %H:%M}")
        st.video(path)
        with open(path, "rb") as fh:
            st.download_button("Baixar", fh, file_name=f"{task_id[:8]}.mp4", key=f"dl-{path}")
        st.divider()
