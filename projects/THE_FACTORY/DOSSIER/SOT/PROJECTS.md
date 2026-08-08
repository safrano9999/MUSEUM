# THE FACTORY — Source of Truth

_Last updated: 2026-03-31 (2)_

This file is the single source of truth for all active, paused, and planned projects in the safrano9999 ecosystem.

---

## Active Projects

| # | Project | Type | Location | Status | Description |
|---|---------|------|----------|--------|-------------|
| 1 | **TRENDING_DEBATES** | Multi-agent / X/Twitter | `THE_FACTORY/DOSSIER/TRENDING_DEBATES` | 🟢 Active | Daily controversial topic, 3 agents debate on X. UK crawls, Serbia bullish, Russia bearish. |
| 2 | **PV_D-A-CH** | Python app / Vision AI | `~/safrano9999/PV_D-A-CH` | 🟢 Active | Solar roof analysis for D-A-CH. Satellite imagery + LLM vision → kWp potential. MySQL + WebUI. |
| 3 | **ZEROINBOX_LLM** | Python / Email AI | `~/safrano9999/ZEROINBOX_LLM` | 🔨 Umbau | AI email sorting pipeline. offlineimap + Maildir + lokaler Worker. Umbau: litellm → OC/MCP JSON-Toolcall. Telegram solo → OpenClaw Multi-Channel (Telegram/Slack/Discord/iMessage). FIFO-Interface (MCP JSON). Variante A (sync) first, dann optional Queue (Variante B). Architektur: `THE_FACTORY/DOSSIER/zeroinbox_oc_mcp_architektur.md`. FIFO-Doku: `SCRIPTS/CONTAINER/openclaw_fifo_interface.md`. |
| 4 | **NAPOLEON_HILLS_AI_MASTERMIND_CLASSES** | Multi-agent / Web | `~/safrano9999/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES` | 🟢 Active | AI Mastermind group simulation. Napoleon Hill personas debate and advise. Web editor on port 7700. |
| 5 | **WARDKEEPER** | Multi-agent / Local | `~/safrano9999/WARDKEEPER` | 🟢 Active | 5-agent local project stewardship. Daily routines, CORE.md per project, air-gapped. |
| 6 | **CLAWBRIDGE** | Infrastructure / Bash+Python | `~/safrano9999/CLAWBRIDGE` | 🟢 Active | inotify file-bus event dispatcher. Actors drop files → jobs run → Telegram feedback. |
| 7 | **FLY_CLOUDFLARE_BRIDGE** | Infrastructure / DevOps | `~/safrano9999/FLY_CLOUDFLARE_BRIDGE` | 🟢 Active | Fly.io apps behind Cloudflare Tunnel + Access. Auth dashboard via CF Worker. |
| 8 | **ALL_LLMS** | Python Library | `THE_FACTORY/DOSSIER/ALL_LLMS.md` | 📋 Dossier | Auto-discover all LLMs from env vars. Key rotation, fallback chains, pip-installable. |
| 9 | **OPENCLAW_CONTAINER** | Infrastructure / Podman | `THE_FACTORY/DOSSIER/OPENCLAW_CONTAINER.md` | 📋 Dossier | OpenClaw in a Podman container. Depends on ALL_LLMS. |
| 10 | **KIWIX_BRIDGE** | Python / Flask WebUI | `github.com/safrano9999/KIWIX_BRIDGE` | 🟢 Active | Offline RAG chat. Local Wikipedia (Kiwix) + any LLM (Ollama/LiteLLM). Anti-hallucination by design. Port 7710. Great for privacy, kids, offline use. Fun/expertise. |
| 11 | **CITADEL** | PHP / Bash | `github.com/safrano9999/CITADEL` | 🟢 Active | Self-hosted service dashboard. Auto-discovers HTTP/HTTPS services via port probing. No config needed. Useful for forky. |
| 12 | **MAILSORT_BUSINESS** | Business / Multi-channel | `THE_FACTORY/DOSSIER/MAILSORT_BUSINESS` | 🔵 Commercial | Multi-channel AI assistant runtime business. Inbox sorting as killer wedge. Fly.io Dockerfile-first deploy. See business plan. |
| 13 | **SOLANA_AIRGAPPED_DEBIAN_WORKFLOW** | Shell / Security | `github.com/safrano9999/SOLANA_AIRGAPPED_DEBIAN_WORKFLOW` | 🟡 Expertise | Air-gapped Solana tx signing on Debian. Cold wallet workflow. |
| 14 | **DAILYNEWS** | Python / PDF | `~/safrano9999/DAILYNEWS` | 🟢 Active | COS Daily News v1 — existing newspaper PDF generator. RSS feeds, football, weather, X trends. CLAWBRIDGE plugin. Unchanged. |
| 15 | **DAILYNEWS2** | Python / AI / Flask / PostgreSQL | `~/safrano9999/DAILYNEWS2` | 🔨 In Planning | COS Daily News v2 — standalone CLAWBRIDGE extension. /dailynews2 command. Crawler (pluggable backends), PostgreSQL storage, AI summaries, paywall flagging, image scraping, Flask dashboard with snapshot dropdown, topic weights, LLM model selector, PDF Intelligence Brief. See PROJECT.md. |

---

## Infrastructure & Platforms (always-on)

| Component | Tech | User | Description |
|-----------|------|------|-------------|
| **OpenClaw Gateway** | Node.js / TypeScript | `openclaw` | Main bot/channel gateway. Port 18789. WebUI via Next.js. Slash-Commands via Agent-Skills (deterministisch, kein LLM). Doku: `SOT/openclaw_slash_command.md`. |
| **Hermes** | Python | `openclaw` | Agent brain. CLI + gateway mode. Skills, memory, cron, subagents. Nous Research Hermes Agent v0.6.0 released — monitor for relevant updates/integration. |
| **CLAWBRIDGE** | Bash + Python | `rafael` | inotify event bus. See project above. |
| **Ollama** | Go | `rafael` | Local LLM server. qwen3.5:2b and others. |
| **Caddy** | Go | container | Reverse proxy. |
| **Cloudflare Tunnel** | cloudflared | container | Public HTTPS without open ports. |
| **Tailscale** | Go | `root` | VPN mesh. |

---

## Bot Fleet

| Bot | Agent | Model (primary) | Role |
|-----|-------|-----------------|------|
| @magabuttlerbot | germany | claude-haiku-4-5 | Main / Coordinator |
| @rafael_cos_bot | uk | claude-haiku-4-5 | Research / Crawler |
| @healer9999bot | russia | claude-haiku-4-5 | Bearish / Anti-thesis |
| @healy9999bot | serbia | claude-haiku-4-5 | Bullish / Pro-thesis |
| @safran9999bot | france | claude-haiku-4-5 | Regional agent |
| @archiultrabot | architect | gpt-4o | Project planning |
| @orchestratorpenetratorbot | orchestrator | gpt-4o | Pipeline control |
| @stewardmanagerbot | steward | claude-haiku-4-5 | Task coordination |
| @stewardrealbot | operator | claude-haiku-4-5 | Execution |
| @inspirationalitybot | inspirator | claude-haiku-4-5 | Idea generation |
| @critizismbot | critic | claude-haiku-4-5 | QA / challenges |
| @beliefagentbot | belief_agent | claude-haiku-4-5 | Mental alignment |

---

## Agent Fallback Chain (all agents)

```
anthropic/claude-haiku-4-5       (primary)
  ↓ anthropic/claude-sonnet-4-5
  ↓ google/gemini-3-flash
  ↓ openai/gpt-4o-mini
  ↓ xai/grok-4-1-fast-non-reasoning
  ↓ moonshot/kimi-k2.5
  ↓ ollama/qwen3.5:2b             (local fallback)
```

---

## Machine & User Layout

| Host | User | Purpose |
|------|------|---------|
| `forky` (Debian 6.19.6) | `openclaw` | Agent infra, bots, Hermes, OpenClaw |
| `forky` | `rafael` | Personal: email, Telegram desktop, private files |
| Fly.io | — | Public-facing apps (Dockerfiles), behind Cloudflare |

---

## TODO

| # | Task | Project | Priority | Status |
|---|------|---------|----------|--------|
| 0 | **PostgreSQL Setup + Migration** — Step 1: spin up central PostgreSQL via Podman on forky (local), persistent volume, bind to localhost. Step 2: migrate projects in order: WARDKEEPER (Vikunja), PV_D-A-CH, DAILYNEWS2 (greenfield). Separate DB per project. MariaDB stays running in parallel until each project verified. | Infrastructure | Critical | ✅ Phase 1 done — PostgreSQL deployed locally via Podman, listening on localhost:5432. Next: migrations. |
| 1 | PV_D-A-CH: Migrate DB from MariaDB → PostgreSQL. Safe + no hurry. Steps: 1) Add psycopg2 + SQLAlchemy PG support. 2) Update compose.yaml (postgres image). 3) Migrate schema + data. 4) Update fly.toml (Fly Postgres). 5) Test full pipeline. Consider PostGIS for geospatial columns (geometry/lat/lon). Keep MariaDB running in parallel until PG verified. | PV_D-A-CH | High | ⏳ Pending |
| 2 | Dogfood QA loop — PV_D-A-CH WebUI hardening. Full loop: 1) Playwright CDP browser (port 9223) → QA all 4 tabs (OSM, Generate, View/Export, Vision) → find bugs/edges. 2) Fix in ~/safrano9999/PV_D-A-CH. 3) git push → github.com/safrano9999/PV_D-A-CH. 4) flyctl deploy → pv-d-a-ch.kleinekuehe.de (fra). 5) Verify in browser. Repeat. flyctl at ~/.fly/bin/flyctl. fly.toml app=pv-d-a-ch region=fra. | PV_D-A-CH | High | ⏳ Pending — awaiting edge case briefing from Rafael |
| 3 | Dogfood QA loop — start app, run systematic WebUI test, fix findings | NAPOLEON_HILLS_AI_MASTERMIND_CLASSES (`mastermind_web.py`, port 7700) | High | ⏳ Pending |
| 4 | Dogfood QA loop — app already running on port 7800, run QA pass | FLY_CLOUDFLARE_BRIDGE (`bridge_web.py`) | High | ⏳ Pending |
| 5 | Deploy local Mattermost via Podman container, bind to 192.168.11.55 (LAN), accessible via Tailscale mesh from anywhere. Configure OpenClaw Mattermost extension + Hermes gateway binding. No internet exposure. | Infrastructure | Medium | ⏳ Pending |
| 7 | CODEANALYST: Scan all source code in ~/safrano9999/, detect all external Linux programs/commands called (shell, subprocess, os.system, backticks etc.), count occurrences globally + per project. Flask WebUI. New repo: safrano9999/CODEANALYST. | CODEANALYST | Medium | ⏳ Pending |
| 9 | **Bash → Python Migration** — SOLANA_AIRGAPPED_DEBIAN_WORKFLOW + NaturalGrounding-Tiktok-Ying-Video-Manager: pure Bash, sollen vollständig auf Python portiert werden. Repos bereits in ~/safrano9999. | Infrastructure | Medium | ⏳ Pending |
| 8 | **Repos aufräumen** — alle 31 Repos in ~/safrano9999 durchgehen: README.md prüfen/ergänzen, .gitignore hardenen, secrets/env-examples bereinigen, veraltete/leere Repos identifizieren, SOT aktualisieren. Betrifft: SMOKETEST, ROUTINE, solana_hello, TELEGRAM_BOT, SGPTMAILDIR_SORTER, ORGANICSLOP, MAILMUSEUM, GEMINI_EXPRESS, KACHELMANN, CALENDAR, PORTFOLIO_OS und alle aktiven Repos. | Infrastructure | Medium | ⏳ Pending |
| 6 | MAILSORT_BUSINESS: Clone existing Fly.io OpenClaw instance (region: SJC/US) via Dockerfile → configure multi-channel (iMessage, WhatsApp, Slack etc.) → wire CLAWBRIDGE to deliver via that instance. Dockerfile-first = portable: same image runs on Fly.io EU, VPS, or Mac Mini appliance with zero rearchitecting. Later: migrate to EU region for GDPR compliance. | MAILSORT_BUSINESS | High | ⏳ Pending |
|| 12 | **LITELLM_PROXY** — Zentraler LLM-Proxy via Podman. Key-Rotation, lokale Modelle (Ollama + LM Studio iMac), Single Endpoint für alle Apps. Vollständige Spec: `SOT/litellm_proxy_project.md`. Port 4000. Clients: Hermes, Napoleon Mastermind, Telegram Bot. | Infrastructure | High | ⏳ Pending |
|| 11 | **WARDKEEPER: Vikunja Agent Provisioning** — Alle Agenten aus `openclaw.json` bekommen eigene Vikunja-User + API-Tokens + SKILL.md + HEARTBEAT-Template. Script: `WARDKEEPER/provision_agents.py`. Voraussetzung: Vikunja-Container läuft unter openclaw (podman). Details + vollständiger Plan: `SOT/wardkeeper_vikunja_provisioning.md`. Flags: `--dry-run`, `--ask-all`. | WARDKEEPER | High | ⏳ Pending |

---

## Notes

- SOUL.md identities for all agents live in `~/safrano9999/SKILLS/SOULS/`
- Dossier templates in `THE_FACTORY/DOSSIER/templates/`
- This file should be updated whenever a project is added, paused, or completed
