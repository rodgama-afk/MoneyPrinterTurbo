import streamlit as st

st.title("❓ Ajuda / Sobre")

st.markdown(
    """
### Geração de Vídeo - IE (marketing)

Aplicação local que transforma um tópico em um vídeo curto completo:
**roteiro por IA → vídeos de banco → narração (TTS) → legendas → montagem**.

#### Como gerar um vídeo
1. Em **Configurações**, cole ao menos **uma chave de IA** e **uma chave de vídeo**.
2. Abra **Gerar Vídeo**, digite o tópico e clique em **Generate Video**
   — ou use a **Geração rápida** no **Dashboard**.
3. O vídeo aparece no **Histórico** e na pasta `storage/tasks/…`.

#### Onde pegar chaves gratuitas
| Serviço | Link |
|---|---|
| **Gemini** (IA) | https://aistudio.google.com/apikey |
| **Claude** (IA) | https://console.anthropic.com/settings/keys |
| **NVIDIA** (IA) | https://build.nvidia.com |
| **Pexels** (vídeo) | https://www.pexels.com/api/ |
| **Pixabay** (vídeo) | https://pixabay.com/api/docs/ |

#### Publicação automática
Em **Conexões para publicação** você conecta o **Upload-Post** para postar
direto no TikTok, Instagram e YouTube Shorts.

#### Idiomas de roteiro
O gerador escreve o roteiro no idioma escolhido em **Script Language**
(inclui **pt-BR** e **es**). A narração usa Edge TTS (grátis).

---
Baseado no projeto open-source **MoneyPrinterTurbo**. Uso interno — IE / Marketing.
"""
)
