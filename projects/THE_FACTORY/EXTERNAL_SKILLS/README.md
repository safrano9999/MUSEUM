# EXTERNAL_SKILLS

Sammlung von Agenten-Architekten & Best Practices aus etablierten Repos für die Factory.

## Repos

### 1. agency-agents
- **Source**: https://github.com/msitarzewski/agency-agents.git
- **Fokus**: Multi-Agent Patterns, Fachbereichs-Agenten, Spezialrollen
- **Relevante SOULs**:
  - `specialized/agents-orchestrator.md` — Orchestrator-Pattern
  - `project-management/project-management-project-shepherd.md` — Projektplanung
  - `specialized/` — weitere spezialisierte Rollen

### 2. openclaw-multi-agent-kit
- **Source**: https://github.com/raulvidis/openclaw-multi-agent-kit.git
- **Fokus**: OpenClaw-spezifische Multi-Agent-Workflows, Telegram-Integration, Topic-Routing
- **Relevante SOULs**:
  - `templates/soul/specialized/agents-orchestrator.md` — Lead Agent Pattern
  - `templates/soul/project-management/project-management-project-shepherd.md` — Project Shepherd
  - `templates/soul/` — vollständige Rolle-Library (Coder, QA, Manager, etc.)
- **Docs**:
  - `INSTRUCTIONS.md` — Setup-Anleitung für AI-Agenten
  - `README.md` — Architektur & Konzepte

## Verwendung

Beim Designen neuer Agenten:
1. Schau in `templates/soul/` oder `specialized/` nach einer ähnlichen Rolle
2. Kopiere die MD als Basis für `SOUL.md`
3. Passe an auf das spezifische Projekt an
4. Referenziere die Original-Doku im Agent's AGENTS.md

---

**Die Factory nutzt diese Repos als Knowledge Base für Agenten-Design.**
