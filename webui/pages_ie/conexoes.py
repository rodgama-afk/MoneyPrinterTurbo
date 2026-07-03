import streamlit as st

from app.config import config

st.title("📤 Conexões para publicação")
st.caption("Publique automaticamente nas redes via Upload-Post (TikTok · Instagram · YouTube Shorts)")

st.info(
    "Crie uma conta e pegue sua API key em https://upload-post.com — "
    "documentação em https://docs.upload-post.com"
)

ui = config.ui

enabled = st.toggle(
    "Ativar integração Upload-Post",
    value=bool(ui.get("upload_post_enabled", False)),
)
api_key = st.text_input(
    "Upload-Post API Key",
    value=ui.get("upload_post_api_key", ""),
    type="password",
)
username = st.text_input(
    "Upload-Post usuário",
    value=ui.get("upload_post_username", ""),
)
platforms = st.multiselect(
    "Plataformas de destino",
    options=["tiktok", "instagram", "youtube"],
    default=ui.get("upload_post_platforms", ["tiktok", "instagram"]),
)
auto_upload = st.toggle(
    "Publicar automaticamente após gerar o vídeo",
    value=bool(ui.get("upload_post_auto_upload", False)),
)
_privacy_opts = ["public", "unlisted", "private"]
_cur_privacy = ui.get("upload_post_youtube_privacy_status", "public")
yt_privacy = st.selectbox(
    "Privacidade no YouTube Shorts",
    options=_privacy_opts,
    index=_privacy_opts.index(_cur_privacy) if _cur_privacy in _privacy_opts else 0,
)

if st.button("Salvar conexões", type="primary"):
    ui["upload_post_enabled"] = enabled
    ui["upload_post_api_key"] = api_key
    ui["upload_post_username"] = username
    ui["upload_post_platforms"] = platforms
    ui["upload_post_auto_upload"] = auto_upload
    ui["upload_post_youtube_privacy_status"] = yt_privacy
    config.save_config()
    st.success("Conexões salvas em config.toml.")

st.divider()
active = bool(ui.get("upload_post_enabled")) and bool(ui.get("upload_post_api_key"))
st.write(f"**Status atual:** {'✅ ativa' if active else '⬜ inativa'}")
if enabled and not api_key:
    st.warning("A integração está ativada mas falta a API Key.")
