# Dark Channel — Run Locally (English)

This is a local, English setup of **MoneyPrinterTurbo**: it turns a topic/keyword
into a complete short video — AI writes the script, stock footage is fetched,
a voice‑over (TTS) is generated, subtitles are burned in, and everything is
combined with FFmpeg into a vertical (9:16) or horizontal (16:9) video.

Everything below is **already installed and configured** on this machine. You
only need to add a couple of free API keys and press start.

---

## 1. Start the app

- **Easiest:** double‑click **`start_webui.bat`** in this folder.
- **Or** from a terminal in this folder:

  ```powershell
  .venv\Scripts\python.exe -m streamlit run webui\Main.py --server.port=8501
  ```

Then open **http://localhost:8501** in your browser. The interface is in English
(language selector top‑right is set to `en - English`).

To stop it: close the terminal window, or press `Ctrl + C` in it.

---

## 2. Add your API keys (one‑time)

Open **Basic Settings (Click to expand)** at the top of the page. You need
**one AI provider key** + **one stock‑video key**.

### AI provider (writes the script)
In **LLM Settings**, pick a provider from **LLM Provider** and paste its key into
**API Key**:

| Provider in dropdown | Where to get a key | Notes |
|----------------------|--------------------|-------|
| **Gemini** (default) | https://aistudio.google.com/apikey | Generous free tier. Model: `gemini-2.5-flash` |
| **Claude** | https://console.anthropic.com/settings/keys | Paid. Model `claude-opus-4-8` (default); `claude-sonnet-4-6` is cheaper, `claude-haiku-4-5` cheapest |
| **NVIDIA** | https://build.nvidia.com | OpenAI‑compatible. Model e.g. `meta/llama-3.3-70b-instruct` |
| DeepSeek / OpenAI / Grok / Ollama (local) … | (in the dropdown) | Many others are also available |

> **Claude** and **NVIDIA** were added to this build specifically. Claude uses the
> official Anthropic SDK; NVIDIA uses NVIDIA NIM’s OpenAI‑compatible endpoint
> (`https://integrate.api.nvidia.com/v1`). Leave **Base Url** empty for Claude.

### Stock video (background footage)
In **Video Source Settings**, paste a key into **Pexels API Key** and/or
**Pixabay API Key** (both free):

- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/

To use **your own local videos** instead of a stock site, set
`material_directory` in `config.toml` to a folder of `.mp4` files.

> Keys you enter in the Web UI are saved to `config.toml` automatically, so you
> only do this once. You can also edit `config.toml` by hand.

---

## 3. Make a video

1. Type a **Video Subject** (e.g. *"the benefits of student exchange"*).
2. (Optional) tweak Video Settings (aspect ratio, clip length) and Subtitle
   Settings (font, position, color).
3. Click the big **Generate Video** button at the bottom.
4. The finished file appears under **`storage/tasks/<task-id>/`** and is playable
   in the page.

Voice‑over uses **Edge TTS** by default (free, no key). Subtitles use Edge TTS
timings by default; for tighter sync you can switch `subtitle_provider` to
`whisper` in `config.toml` (downloads a speech model on first use).

---

## What was set up (for reference)

- **FFmpeg 8.1.2** and **uv** installed via winget.
- Isolated **Python 3.12** environment in **`.venv`** (your system Python 3.13 is
  untouched — several dependencies don’t support 3.13).
- All dependencies installed, including the **`anthropic`** SDK for Claude.
- `config.toml`: `ui.language = "en"`, `llm_provider = "gemini"`,
  `video_source = "pexels"`, plus `claude_*` and `nvidia_*` settings.

### Re‑create the environment from scratch (if ever needed)
```powershell
uv venv --python 3.12
uv pip install -r requirements.txt
```

### Switching the LLM provider later
Just pick a different one in the **LLM Provider** dropdown (and paste its key),
or change `llm_provider` in `config.toml`.
