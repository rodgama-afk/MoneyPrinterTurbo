import streamlit as st

from app.config import config

st.title("⚙️ Configurações")
st.caption("Provedores de IA, chaves e preferências — num lugar só")

app = config.app
ui = config.ui


def _first(lst):
    return (lst or [""])[0] if lst else ""


def _index(options, value, fallback=0):
    return options.index(value) if value in options else fallback


# ---- AI provider ----
st.subheader("Provedor de IA")
providers = ["gemini", "claude", "nvidia", "openai", "deepseek", "ollama", "litellm"]
cur = app.get("llm_provider", "gemini")
if cur not in providers:
    providers.insert(0, cur)
provider = st.selectbox("Provedor", providers, index=_index(providers, cur))
api_key = st.text_input(
    f"Chave de API — {provider}",
    value=app.get(f"{provider}_api_key", ""),
    type="password",
)
model = st.text_input("Modelo", value=app.get(f"{provider}_model_name", ""))

# ---- video sources ----
st.subheader("Fontes de vídeo")
src_opts = ["pexels", "pixabay", "local"]
video_source = st.selectbox(
    "Fonte padrão",
    src_opts,
    index=_index(src_opts, app.get("video_source", "pexels")),
)
pexels = st.text_input("Pexels API Key", value=_first(app.get("pexels_api_keys")), type="password")
pixabay = st.text_input("Pixabay API Key", value=_first(app.get("pixabay_api_keys")), type="password")

# ---- subtitles + interface language ----
st.subheader("Legendas e idioma")
sub_opts = ["edge", "whisper", ""]
sub_labels = {"edge": "Edge (grátis)", "whisper": "Whisper (mais preciso)", "": "Sem legendas"}
subtitle_provider = st.selectbox(
    "Legendas",
    sub_opts,
    index=_index(sub_opts, app.get("subtitle_provider", "edge")),
    format_func=lambda x: sub_labels[x],
)
lang_opts = ["en", "zh", "de", "es", "id", "ru", "tr", "vi"]
language = st.selectbox(
    "Idioma da interface",
    lang_opts,
    index=_index(lang_opts, ui.get("language", "en")),
)

if st.button("Salvar configurações", type="primary"):
    app["llm_provider"] = provider
    if api_key:
        app[f"{provider}_api_key"] = api_key
    if model:
        app[f"{provider}_model_name"] = model
    app["video_source"] = video_source
    app["pexels_api_keys"] = [pexels.strip()] if pexels.strip() else []
    app["pixabay_api_keys"] = [pixabay.strip()] if pixabay.strip() else []
    app["subtitle_provider"] = subtitle_provider
    ui["language"] = language
    config.save_config()
    st.success("Configurações salvas em config.toml.")
