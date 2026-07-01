"""Geração de Vídeo - IE (marketing)

Entry point that wraps the existing MoneyPrinterTurbo generator in a multi-page
app with a sidebar menu, an IE-branded look, and a dashboard. The generator
itself (Main.py) is reused as the "Gerar Vídeo" page.
"""

import os
import sys

import streamlit as st

# Make `app.*` importable for every page (pages run in this same process).
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

st.set_page_config(
    page_title="Geração de Vídeo - IE (marketing)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- IE brand: logo + accents (blue #0060b0 / yellow #f8c800 / navy #0f2540) ----
_ASSETS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")
_LOGO = os.path.join(_ASSETS, "ie-logo.png")
_ICON = os.path.join(_ASSETS, "ie-logo-90.png")
if os.path.exists(_LOGO):
    st.logo(
        _LOGO,
        size="large",
        link="https://ie.com.br",
        icon_image=_ICON if os.path.exists(_ICON) else None,
    )

st.markdown(
    """
    <style>
      /* Page titles carry the IE yellow accent under an IE-navy heading */
      h1 { color: #0f2540; border-bottom: 3px solid #f8c800; padding-bottom: .25rem; }
      h2, h3 { color: #0f2540; }
      /* Metrics in IE blue */
      [data-testid="stMetricValue"] { color: #0060b0; }
      /* Active sidebar menu item gets an IE yellow marker */
      [data-testid="stSidebarNav"] a[aria-current="page"] {
          border-left: 4px solid #f8c800;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages_ie/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("Main.py", title="Gerar Vídeo", icon="🎬"),
    st.Page("pages_ie/historico.py", title="Histórico", icon="🗂️"),
    st.Page("pages_ie/conexoes.py", title="Conexões para publicação", icon="📤"),
    st.Page("pages_ie/configuracoes.py", title="Configurações", icon="⚙️"),
    st.Page("pages_ie/ajuda.py", title="Ajuda / Sobre", icon="❓"),
]

pg = st.navigation(pages)

with st.sidebar:
    st.divider()
    st.caption("IE · Marketing · Geração de Vídeo")

pg.run()
