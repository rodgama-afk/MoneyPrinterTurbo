import glob
import os
from datetime import datetime

import streamlit as st

st.title("🗂️ Histórico")
st.caption("Vídeos já gerados")

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
_TASKS = os.path.join(_ROOT, "storage", "tasks")

files = glob.glob(os.path.join(_TASKS, "*", "final-*.mp4"))
files.sort(key=os.path.getmtime, reverse=True)

if not files:
    st.info("Nenhum vídeo gerado ainda. Gere o primeiro na página **Gerar Vídeo** ou no **Dashboard**.")
else:
    st.write(f"**{len(files)}** vídeo(s) encontrado(s).")
    for path in files:
        task_id = os.path.basename(os.path.dirname(path))
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        size_mb = os.path.getsize(path) / (1024 * 1024)
        with st.container(border=True):
            st.markdown(f"**{os.path.basename(path)}** — tarefa `{task_id[:8]}`")
            st.caption(f"{mtime:%d/%m/%Y %H:%M} · {size_mb:.1f} MB")
            st.video(path)
            with open(path, "rb") as fh:
                st.download_button(
                    "Baixar",
                    fh,
                    file_name=f"{task_id[:8]}-{os.path.basename(path)}",
                    key=f"dl-{path}",
                )
