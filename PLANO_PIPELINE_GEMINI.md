# Plano — Pipeline Generativo Google por Etapa (config + animação)

> Status: **PLANO PARA APROVAÇÃO** (nada implementado ainda).
> App: *Geração de Vídeo - IE (marketing)*. Base: fork MoneyPrinterTurbo.
> Pesquisa das 5 APIs feita por time multi-agente (docs oficiais ai.google.dev, jun/2026).

## Decisões já travadas com você
- **Plano detalhado primeiro** → você aprova antes de eu implementar.
- **Motor de vídeo:** Veo 3.1 primário, **banco (Pexels/Pixabay) como fallback** automático.
- **Config por etapa:** seletor **flexível** de provedor/modelo, com os 5 modelos Google como **padrão**.
- **Acesso:** você tem os previews + billing → **integração real** (não mock).
- **Pesquisa Profunda:** **opcional, desligada por padrão** (toggle no 'Gerar Vídeo'); implementada por último.
- **Áudio:** **narração TTS (pt-BR) + Veo mudo** (`generate_audio=false`) + música Lyria ao fundo.
- **Qualidade Veo:** Fast/Standard/Lite e 720p/1080p/4k **configuráveis na UI**, **padrão Fast + 720p**; estimativa de custo antes de gerar.
- **Duração alvo:** **~30–45s** (4–6 clipes Veo de 8s, ~$3,2–4,8/short).

## Princípio de arquitetura
O pipeline Google é um **segundo motor**, ativado por `params.video_source == "gemini"`. O caminho de banco de vídeos (`material.download_videos`) e toda a montagem final (`video.combine_videos` / `video.generate_video`) **ficam intactos** — a mudança é um conjunto de *branches novos*, não cirurgia no que já funciona. Cada etapa Google que falhar (sem acesso/cota) **cai no fallback** correspondente, sem quebrar a geração.

---

## Pré-requisito técnico (bloqueante)
| Item | Situação | Ação |
|---|---|---|
| SDK | Repo usa `google.generativeai` (antigo, `generate_content`). | Adicionar **`google-genai` (>= 2.3.0)** — `from google import genai`. É o SDK que expõe `client.interactions.*` (Deep Research, Lyria) e `client.models.generate_videos` (Veo). Chave reutiliza `config.app.gemini_api_key`. |
| Persistência | `config.save_config()` só grava tabelas `app/azure/.../ui`. | Todas as chaves novas ficam **sob `[app]`** (ex.: `veo_model`), nunca em uma tabela `[gemini]` nova (senão não salva). |

---

## 1. Configuração por etapa (todos os parâmetros documentados)

Cada etapa expõe **provedor + modelo + parâmetros**. Padrões pensados para *short de marketing* (9:16, ~30–45s, 1 locutor). ⚠️ = ponto de baixa confiança na doc (confirmar contra chave real).

### Etapa 1 · Pesquisa Profunda — `deep-research-preview-04-2026`
Interactions API, **assíncrono** (`background=True` + `store=True`, poll em `interactions.get`). Relatório citado (texto) que alimenta o roteiro. ⚠️ SDK/quota/RPM não 100% verificáveis; ~$1–7 e até ~20 min por execução.

| Parâmetro | Tipo | Valores | Padrão |
|---|---|---|---|
| `agent` | string | `deep-research-preview-04-2026` \| `deep-research-max-preview-04-2026` | preview (rápido) |
| `input` | string/array | texto ou multimodal (texto/imagem/PDF) | tema do vídeo |
| `background` | bool | `true` (obrigatório) | true |
| `store` | bool | `true` (obrigatório c/ background) | true |
| `stream` | bool | true/false (para animação) | true |
| `agent_config.thinking_summaries` | string | `auto` \| `none` | `auto` (alimenta a animação) |
| `agent_config.visualization` | string | `auto` \| `off` | `off` (gráficos não servem p/ roteiro) |
| `agent_config.collaborative_planning` | bool | true/false | false |
| `tools` | array | google_search / url_context / code_execution / mcp_server / file_search | padrão (search+url+code) |
| `previous_interaction_id` | string | continuar interação | — |

Limites: 1M tokens entrada / 65k saída; ~60 min máx; saída = texto citado + imagens base64 (sem JSON estruturado).

### Etapa 2 · Roteiro — `gemini-3.1-pro-preview`
Texto/raciocínio. **Recomendo rotear pelo dispatcher existente** `llm._generate_response` (provedor `gemini`) em vez da Interactions API (mais verificado no seu código). Paid tier.

| Parâmetro | Tipo | Valores | Padrão |
|---|---|---|---|
| `model` | string | `gemini-3.1-pro-preview` | — |
| `system_instruction` | string | persona | `DEFAULT_SCRIPT_SYSTEM_PROMPT` atual |
| `thinking_level` | enum | minimal/low/medium/high | **medium** ⚠️ (docs conflitam sobre o default) |
| `max_output_tokens` | int | ≤ 65536 | 2000 |
| `temperature` | float | 0–2 | *deixar no default* (3.x degrada se mexer) |
| `top_p` / `top_k` | float/int | — | default |
| `response_format` | obj | json_schema | — |
| `tools` | array | google_search, code_execution, url_context, grounding | — |
| `previous_interaction_id` | string | revisão multi-turn | — |

Preço ~$2 in / $12 out por 1M tokens.

### Etapa 3 · Vídeo — `veo-3.1-generate-preview` (núcleo novo)
`client.models.generate_videos`, **assíncrono** (poll `operations.get` até `done`), baixa via `client.files.download`. Gera N clipes de 8s cobrindo a duração da narração; a montagem existente concatena/letterboxa igual ao banco.

| Grupo | Parâmetro | Valores | Padrão |
|---|---|---|---|
| modelo | `veo_model` | `veo-3.1-generate-preview` \| `...-fast-...` \| `...-lite-...` | **fast** ($0.10/s vs $0.40) |
| enquadramento | `aspect_ratio` | `16:9` \| `9:16` | `9:16` (de `params.video_aspect`) |
| | `resolution` | `720p` \| `1080p` \| `4k` | `720p` |
| | `duration_seconds` | `"4"`/`"6"`/`"8"` (string) | `"8"` |
| | `number_of_videos` | 1 (fixo p/ Veo 3.1) | 1 |
| conteúdo | `negative_prompt` | texto | `"blurry, low quality, distorted, watermark"` |
| | `generate_audio` | true/false | **false** (a voz vem da Etapa 4; evita colidir) |
| | `enhance_prompt` | true/false | true |
| | `person_generation` | `allow_all` \| `allow_adult` | `allow_adult` |
| | `seed` | int | — |
| avançado | `image` / `last_frame` | Image | — (image-to-video, 1º/último frame) |
| | `reference_images` | até 3 (força 8s) | — |
| | `video` | Video anterior (estender, 720p) | — |

Limites: 8s/clipe; MP4 com SynthID; vídeo apagado do servidor em 2 dias (baixar na hora). Preço Fast 720p **$0.10/s**.

### Etapa 4 · Áudio/Narração — `gemini-3.1-flash-tts-preview` (90% pronto)
Já existe `voice.py:gemini_tts` (dispatch por prefixo `gemini:`). Só falta **trocar o model id hardcoded** (`gemini-2.5-flash-preview-tts`, voice.py:1050) por `config.app.get("tts_model", ...)`.

| Parâmetro | Valores | Padrão |
|---|---|---|
| `tts_model` | `gemini-3.1-flash-tts-preview` (2.5 = fallback grátis) | 3.1 |
| `voice_name` | 30 vozes (Kore, Zephyr, Puck, Charon, Leda, Orus, Aoede…) | Kore |
| `response_modalities` | `["AUDIO"]` | — |
| multi-speaker | até 2 locutores | 1 (marketing) |
| tags inline | `[whispers]`, `[excited]`… + estilo em linguagem natural no texto | — |

Saída: PCM 24kHz mono 16-bit → convertido p/ MP3 (já feito). **Não existe `language_code`/`temperature`** — idioma vem do texto. Preço $1 in / $20 out por 1M. ⚠️ prompts de preview "podem ser usados para melhorar produtos Google" → não enviar material confidencial.

### Etapa 5 · Música de Fundo — `lyria-3-clip-preview`
Interactions API, **síncrono**. Clipe fixo de **30s**, MP3 48kHz. Escreve o mp3 em `resource/songs/` e aponta `params.bgm_file`; a montagem já faz loop/fade/volume.

| Parâmetro | Valores | Padrão |
|---|---|---|
| `music_enabled` | bool | true |
| `music_model` | `lyria-3-clip-preview` ($0.04/clipe) | — |
| `input` (prompt) | texto (+ até 10 imagens); **tempo/gênero/humor/estrutura tudo por linguagem natural** | derivado do humor do roteiro ou campo do usuário |
| `bgm_volume` | reusa `params.bgm_volume` | 0.2 |

⚠️ **Não há** parâmetros de tempo/seed/negative/lyrics — tudo é prompt. Sem edição iterativa.

---

## 2. Layout de módulos novos
```
app/services/gemini/
├── __init__.py   # _client() -> genai.Client; poll(fetch, is_done, on_tick) genérico (LRO)
├── research.py   # deep_research(subject, cfg) -> str        [assíncrono: create bg + poll]
├── video.py      # generate_clips(prompts, cfg) -> [mp4...]   [assíncrono: poll operations]
└── music.py      # generate_music(prompt, cfg) -> mp3 path    [síncrono]
# roteiro -> continua no llm.py (novo override de provedor); TTS -> continua em voice.py
```
Cada wrapper captura exceção e retorna `None`/`[]` → nunca derruba a geração.

## 3. Orquestração (`task.py:start`)
```
progress=5
├─ (NOVO) se deep_research_enabled: research = gemini.research.deep_research(subject)
│         → alimenta o roteiro (append em video_script_prompt); stop_at=="research" retorna
├─ 1. generate_script            (roteiro; modelo por override em _generate_response)
├─ 2. generate_terms             ← PULA quando source in ("local","gemini") (Veo usa o roteiro)
├─ 3. generate_audio             (já roteia gemini: TTS)
├─ 4. generate_subtitle          (whisper recomendado p/ sincronizar com Veo)
├─ 5. get_video_materials
│      se source=="gemini": divide roteiro em N segmentos (N*8s ≥ duração) → gemini.video.generate_clips
│      senão: caminho de banco/local INTACTO   ← FALLBACK
├─ (NOVO) se music_enabled: params.bgm_file = gemini.music.generate_music(mood)
└─ 6. generate_final_videos      (INTACTO: letterbox + concat + mux voz/BGM)
```
Fallbacks: pesquisa falha → roteiro só com o tema; **Veo falha → `download_videos` do banco**; Lyria falha → BGM local; TTS 3.1 falha → 2.5 ou edge-tts.

Pontos de edição: `task.py:334/337/352/404/428`, `material.py:304` (branch `veo`), `schema.py:110` (campos novos em `VideoParams`), `webui/Main.py:811` + `pages_ie/dashboard.py:101` (setar campos novos), `config.example.toml:177`.

## 4. Animação de execução passo a passo
Hoje `tm.start` roda **síncrono** → a UI só mostra log corrido. Solução:
1. Rodar `tm.start` em **thread** (só mexe em `sm.state`, nunca no Streamlit).
2. Loop de rerun na página lê `sm.state.get_task(task_id)` e renderiza um **checklist com `st.status`/`st.progress`**: `Pesquisa → Roteiro → Narração → Legendas → Clipes Veo → Música → Montagem`, com ✅/⏳/⬜.
3. Sub-progresso das etapas assíncronas via `on_tick` do `poll()` → grava `sub_log` no estado (ex.: "Veo clipe 2/5 renderizando…", ou o `thinking_summary` da pesquisa).
4. Preview de artefatos por etapa: `st.text_area` (roteiro), `st.video` (1º clipe), `st.audio` (música).

Requer estender `state.update_task` com um campo `stage`/`sub_log` (state.py:39).

## 5. Custo e guardas
| Etapa | Custo (short ~40s) | Guarda |
|---|---|---|
| Pesquisa | OFF ($0); se on, $1–7 | flag; `-max-` só sob opt-in |
| Roteiro | ~$0.01 | thinking_level=medium |
| **Veo** | 5 clipes × 8s × $0.10 = **~$4** (Fast/720p) | Fast+720p padrão; cap `max_veo_clips`; **estimativa de custo na UI antes de gerar** |
| Narração | ~$0.02 | — |
| Música | $0.04 | — |

Total ~**$4/short**, dominado pelo Veo. Guardas: default Fast+720p, `generate_audio=false`, cap de clipes, estimativa+confirmação na UI, retry/backoff em 429.

## 6. Riscos abertos (confirmar contra chave real)
1. ⚠️ **SDK `google-genai` / `client.interactions`** existe no seu ambiente? (maior risco — metade do pipeline depende dele). Confirmo logo no início.
2. ⚠️ **Allowlist dos previews** — qualquer um dos 5 pode dar 403 até liberar. Mitigado por detecção + fallback.
3. ⚠️ **RPM da Pesquisa Profunda** (~2–5, não oficial) → manter OFF por padrão.
4. ⚠️ **IDs `-preview-*` mudam** → todos como config, nunca hardcode.
5. ⚠️ **Retenção de dados** TTS/Lyria preview → aviso na UI, não mandar material sensível.

## 7. Ordem de implementação proposta (a mais segura)
1. Adicionar `google-genai` + confirmar `client.interactions`/`generate_videos` na sua chave. (desbloqueia tudo)
2. Config por etapa em `VideoParams` + `config.example.toml` + telas (Configurações + painel do Gerar Vídeo).
3. **Etapa 4 (TTS 3.1)** — trocar o hardcode (1 linha; etapa já funciona).
4. **Etapa 3 (Veo)** — `gemini/video.py` + branch `source=="gemini"` + fallback banco. (capacidade nova principal)
5. **Etapa 5 (Lyria)** — `gemini/music.py` → `bgm_file`.
6. **Animação** (thread + polling + `st.status`).
7. **Etapa 1 (Deep Research)** por último, atrás de flag (menos verificada, menos essencial p/ short).

Cada passo é entregável e verificável isoladamente.
