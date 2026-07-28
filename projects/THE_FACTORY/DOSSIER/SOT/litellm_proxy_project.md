# LiteLLM Proxy — Project Spec

_Source: LITELLM PROXY PROJECT.pdf, eingetragen 2026-03-31_

## Ziel

Zentraler LLM-Proxy der:
- API-Keys nie nach außen exponiert
- Mehrere Keys pro Provider automatisch rotiert bei Rate Limits
- Lokale Modelle (Ollama, LM Studio) einheitlich einbindet
- Als Single Endpoint für alle Apps dient (Mastermind, Telegram Bot, Hermes, etc.)

---

## Architektur

```
Podman Host
┌─────────────────────────────────────────────────────┐
│  .env (Keys) → generate_config.py → /tmp/config.yaml│
│                                                      │
│  ┌──────────────┐   ┌─────────────────────────┐     │
│  │  ollama      │   │  litellm                │     │
│  │  :11434      │◄──│  :4000                  │     │
│  └──────────────┘   └────────────┬────────────┘     │
└────────────────────────────────── │ ─────────────────┘
                                    │
                ┌───────────────────┼───────────────┐
                ▼                   ▼               ▼
        api.gemini.com      api.anthropic.com   192.168.1.x:1234
        (Key 1, 2, 3         (Anthropic)        LM Studio iMac
         rotated)                               (Qwen3.5, bare metal)
```

Clients sprechen nur mit :4000 — Keys bleiben unsichtbar.

---

## Verzeichnisstruktur

```
litellm-proxy/
├── podman-compose.yml
├── .env                          # API Keys — NEVER in Git!
├── .gitignore
└── generate_litellm_config.py    # Startup script → config.yaml
```

---

## .env

```env
GEMINI_API_KEY=...
GEMINI_API_KEY_2=AIza...
GEMINI_API_KEY_3=AIza...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
KILOCODE_API_KEY=...

OLLAMA_HOST=ollama
LMSTUDIO_HOST=192.168.1.50

LITELLM_MASTER_KEY=sk-proxy
```

---

## generate_litellm_config.py

Läuft beim Container-Start. Liest `os.environ`, fragt lokale Endpoints ab, generiert `/tmp/config.yaml` — ephemeral, nie auf Disk persistiert.

### Provider → Default Model

| Provider | Default Model |
|---|---|
| gemini | gemini/gemini-2.0-flash |
| anthropic | anthropic/claude-sonnet-4-6 |
| openai | openai/gpt-4o |
| openrouter | openrouter/auto |
| kilocode | dynamisch via API |

### Key-Logik

- `PROVIDER_API_KEY`, `PROVIDER_API_KEY_2`, `_3` etc. → gleicher `model_name` → LiteLLM rotiert automatisch
- Kilocode: Modelle von `https://api.kilo.ai/api/gateway/models`
- Ollama: `http://{OLLAMA_HOST}:11434/v1/models`
- LM Studio: `http://{LMSTUDIO_HOST}:1234/v1/models`

### Router Settings

```yaml
router_settings:
  routing_strategy: least-busy
  num_retries: 3
  retry_after: 5
  allowed_fails: 2
```

---

## podman-compose.yml

```yaml
version: "3.8"
services:
  ollama:
    image: ollama/ollama
    container_name: ollama
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    container_name: litellm
    env_file:
      - .env
    volumes:
      - ./generate_litellm_config.py:/app/generate_litellm_config.py:ro
    ports:
      - "4000:4000"
    depends_on:
      - ollama
    command: >
      sh -c "pip install pyyaml -q &&
             python /app/generate_litellm_config.py &&
             litellm --config /tmp/config.yaml --port 4000"
    restart: unless-stopped

volumes:
  ollama_data:
```

---

## Client-Konfiguration

### Hermes Agent
```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  base_url: http://localhost:4000/v1
  api_key: sk-proxy
  default: gemini
```

### Napoleon Mastermind
```env
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=sk-proxy
```

### Telegram AI Bot
Kein Code-Change — nur `.env` umschalten:
```env
OPENAI_BASE_URL=http://litellm:4000/v1
OPENAI_API_KEY=sk-proxy
```

---

## Security Model

- Keys nur im Proxy (env_file, nie im Image)
- config.yaml ephemeral (/tmp)
- Clients sehen nur LITELLM_MASTER_KEY
- Audit Log zentral möglich
- Per-App virtuelle Keys mit Budget-Limits möglich (LiteLLM UI)

---

## Roadmap

- [ ] generate_litellm_config.py fertig + testen
- [ ] Podman Compose aufsetzen (litellm + ollama)
- [ ] LM Studio Connection testen (192.168.1.x:1234)
- [ ] Telegram Bot auf Proxy umstellen
- [ ] Hermes Agent auf Proxy umstellen
- [ ] Napoleon Mastermind auf Proxy umstellen
- [ ] Budget Limits per virtuellem Key (LiteLLM UI)
- [ ] Monitoring/Logging aktivieren (LiteLLM Dashboard)
