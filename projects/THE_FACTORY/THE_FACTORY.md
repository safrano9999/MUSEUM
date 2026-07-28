# THE_FACTORY Configuration

## Build Directory

**Active Project**: `../PV_D-A-CH`

All output, code, and deployables go here. Direct path for local testing:
```bash
cd ../PV_D-A-CH
python PV_D-A-CH.py --help
```

---

## Agent Workspaces

### 1. Architect (📐)
- **Agent ID**: `architect`
- **Workspace**: `/home/openclaw/safrano9999/WARDKEEPER/VIKUNJA/workspace/architect`
- **Soul**: `/home/openclaw/safrano9999/THE_FACTORY/SOULS/ARCHITECT.md`
- **Telegram**: @archiultrabot

### 2. Orchestrator (♟️)
- **Agent ID**: `orchestrator`
- **Workspace**: `/home/openclaw/safrano9999/WARDKEEPER/VIKUNJA/workspace/orchestrator`
- **Soul**: `/home/openclaw/safrano9999/THE_FACTORY/SOULS/ORCHESTRATOR.md`
- **Telegram**: @orchestratorpenetratorbot

---

## Projects

### Active

| # | Project | Typ | Dossier | Build Dir | Status |
|---|---------|-----|---------|-----------|--------|
| 1 | **ALL_LLMS** | Python Library (pip) | `./DOSSIER/ALL_LLMS.md` | `../ALL_LLMS` | 📋 Dossier |
| 2 | **OPENCLAW_CONTAINER** | Podman Container | `./DOSSIER/OPENCLAW_CONTAINER.md` | TBD | 📋 Dossier |

---

## Dependencies zwischen Projekten

```
OPENCLAW_CONTAINER
  └── ALL_LLMS (pip install -e im Container)
        └── wird genutzt von: TELEGRAM-AI-BOT, MAILSORT, künftige Projekte
```

---

## References

- **Dossier Templates**: `./DOSSIER/templates/`
- **Soul Central**: `./SOULS/`
- **External References**: `./EXTERNAL_SKILLS/`

