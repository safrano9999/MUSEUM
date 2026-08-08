# AGENTS_REGISTRY

Alle in THE_FACTORY verfügbaren Agenten + ihre Rollen.

## Core Roles

| Agent | Bot | Model | Rolle | Status |
|-------|-----|-------|-------|--------|
| architect | @archiultrabot | gpt-4o | Projektplanung & Step 0 | ✅ Ready |
| orchestrator | @orchestratorpenetratorbot | gpt-4o | Pipeline-Control | ✅ Ready |

## Regional/Specialized (verfügbar zum Spawnen)

| Agent | Bot | Primary Model | Fallbacks | Notiz |
|-------|-----|---------------|-----------|-------|
| uk | @rafael_cos_bot | claude-haiku-4-5 | 6-model chain | Research |
| france | @safran999bot | claude-haiku-4-5 | 6-model chain | |
| serbia | @healy9999bot | claude-haiku-4-5 | 6-model chain | |
| russia | @healer9999bot | claude-haiku-4-5 | 6-model chain | |
| italy | @triggershotbot | claude-haiku-4-5 | 6-model chain | |
| germany | @magabuttlerbot | claude-haiku-4-5 | 6-model chain | |
| china | @golemjudenbot | claude-haiku-4-5 | 6-model chain | |
| america | @farmerscowbot | claude-haiku-4-5 | 6-model chain | |
| steward | @stewardmanagerbot | haiku-4-5 | 6-model chain | Task Coord |
| operator | @stewardrealbot | haiku-4-5 | 6-model chain | Execution |
| inspirator | @inspirationalitybot | haiku-4-5 | 6-model chain | |
| critic | @critizismbot | haiku-4-5 | 6-model chain | QA |
| belief_agent | @beliefagentbot | haiku-4-5 | 6-model chain | |
| argentinia | @pmaradonabot | haiku-4-5 | 6-model chain | |
| brazil | @ronaldobrazilbot | haiku-4-5 | 6-model chain | |

## Fallback Chain (alle Agents)

```
anthropic/claude-haiku-4-5 (primary)
  ↓
anthropic/claude-sonnet-4-5
  ↓
google/gemini-3-flash
  ↓
openai/gpt-4o-mini
  ↓
xai/grok-4-1-fast-non-reasoning
  ↓
moonshot/kimi-k2.5
  ↓
ollama/qwen3.5:2b (lokal)
```

---

**Spawn-Strategie:**
- Architect & Orchestrator sind dauerhaft (registered Bots).
- Worker-Agents werden vom Orchestrator ad-hoc gespawnt (Run-Sessions) oder können persistent sein.
- Alle kommunizieren über Vikunja (Schnittstelle zur Koordination).
