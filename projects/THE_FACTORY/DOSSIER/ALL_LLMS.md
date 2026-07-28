# ALL_LLMS

**Beschreibung**: Standalone Python-Package das anhand vorhandener API-Keys und Endpoints automatisch alle verfügbaren LLM-Models discovert — einmal sauber, überall importieren.

---

## A. Sollzustand

- Env-Vars scannen (`*_API_KEY`) → Provider automatisch erkennen
- Pro Provider `/v1/models` fetchen → vollständige Modell-Liste
- Ollama Discovery (lokal, podman, docker)
- Custom OpenAI-kompatible URLs (LM Studio, etc.) via `OPENAI_URL`, `OPENAI_URL_2`, ...
- Kilocode Gateway Discovery
- Multi-Key-Support pro Provider (`PROVIDER_API_KEY`, `_API_KEY_2`, `_API_KEY_3`, ...)
- Key-Rotation bei Rate-Limits + Dead-Key-Detection
- Fallback-Model-Switching wenn alle Keys eines Providers erschöpft
- Provider-Routing: `provider/model` Format → richtiger Endpoint + API-Format
- `.env` oder Env-Vars im RAM — beides unterstützt
- Output: `{provider: [model1, model2, ...]}` Registry

---

## B. Health Check & UI

**Projekt-Typ**: Python Library (pip-installbar) + optional CLI

**Implementierung**: Python 3.10+ mit litellm

Beim Import/Init: alle konfigurierten Provider anpingen, Models fetchen, Registry aufbauen. Nicht erreichbare Endpoints → Warning, kein Crash.

**Features**:
- `from all_llms import registry` — fertige Model-Registry als Dict
- `from all_llms import completion` — litellm.completion mit Key-Rotation + Provider-Routing
- `python -m all_llms` — CLI: zeigt alle gefundenen Provider + Models
- `python -m all_llms --json` — JSON-Output für Scripting

**Standardverhalten**: Import baut Registry, zeigt gefundene Provider im Log.

---

## C. Dependencies

- Python 3.10+
- `litellm` — LLM-Abstraction + bekannte Provider-Listen
- `python-dotenv` — .env Laden (optional)
- Keine weiteren externen Dependencies

---

## D. Artefakte, Dateien & Libraries

- `all_llms/__init__.py` – Public API (registry, completion)
- `all_llms/discover.py` – Provider-Detection, Model-Fetching
- `all_llms/routing.py` – Provider-Routing (kilocode/, ollama/, custom URLs)
- `all_llms/rotation.py` – Key-Rotation + Fallback-Logik
- `pyproject.toml` – Package-Config, pip-installbar
- `.env` – (optional) API-Keys

---

## E. Peripherie

```
Env-Vars / .env
  ↓
parse_env_providers()  →  {provider: api_key}
  ↓
Per Provider: /v1/models fetchen
  ↓
MODEL_REGISTRY: {provider: [models]}
PROVIDER_KEYS:  {provider: [key1, key2, ...]}
OPENAI_URL_MAP: {hostname: {url, key, models}}
  ↓
completion(model="provider/model", messages=[...])
  → routing → key rotation → litellm.completion()
```

**Quellcode-Basis**: Extrahiert aus `TELEGRAM-AI-BOT/ai_chat.py` (Zeilen 522-906, bewährt im Produktionseinsatz)

---

## F. Ideen & Weiteres

- Cache für Model-Registry (nicht bei jedem Import neu fetchen)
- Async-Support für Discovery (parallel fetchen)
- Health-Check Endpoint für Container-Nutzung
- Model-Filtering (nur Chat-Models, keine Embedding/TTS/Image)
- Integration mit THE_FACTORY Container-Setup (Milestone 1)

---

## Z. Vom Architect auszufüllen

Bevor Übergabe an den Orchestrator:

- [x] **Single oder Multi-Agent?** (Step 0 Entscheidung)
  - [x] Single → Claude Code Workflow
  - [ ] Multi → Orchestrator mit Worker-Agents

- [x] **Blackbox Research abgeschlossen?**
  - Quellcode in ai_chat.py vollständig analysiert
  - Keine externen APIs nötig außer den LLM-Providern selbst
  - Keine Kosten — nutzt nur bestehende API-Keys

- [x] **Datenquellen erreichbar & getestet?**
  - Provider-APIs erreichbar (laufen bereits in Produktion)
  - Keys in Env-Vars vorhanden

- [ ] **Entwicklungs-Setup fertig?**
  - Repo anlegen in ~/safrano9999/ALL_LLMS
  - pyproject.toml + Package-Struktur

- [ ] **Worker-Agent Strategie geklärt?**
  - N/A — Single-Agent (Claude Code direkt)

- [x] **Gibt es Milestones / Phasen?**
  - Phase 1: Core Discovery + Registry (parse_env, fetch models, build registry)
  - Phase 2: Routing + Rotation (completion wrapper)
  - Phase 3: CLI + pip install -e . in bestehende Projekte einbauen
