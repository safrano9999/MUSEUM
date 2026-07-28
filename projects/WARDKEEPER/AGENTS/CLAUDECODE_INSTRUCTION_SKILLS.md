# Claude Code Workflow (OpenClaw Agents)

## 1. Ziel
Claude Code soll als „Coding-Agent“ eingesetzt werden, wenn ein Task mehr als reines Shell-Scripting braucht (z. B. Python-Pipeline bauen, Refactorings, Tooling). Dieser Leitfaden zeigt, wie der Orchestrator eine Session startet und Agents damit arbeiten.

## 2. Voraussetzungen
- Repo/Workspace vorbereitet (z. B. `/home/openclaw/safrano9999/PV_D-A-CH`).
- Kurzes Briefing/Plan (TASK.md oder Vikunja-Task) mit:
  - Hintergrund & Ziel
  - Wichtige Dateien/Ordner
  - Erfolgsdefinition / Tests
- Optional: Shelled venv aktivieren, wenn das Projekt eine benötigt.

## 3. Session starten
Verwende `sessions_spawn` mit `runtime="acp"` und einem Claude-Code-Modell:
```bash
sessions_spawn \
  --label "claude-code-pv" \
  --runtime acp \
  --agentId anthropic/claude-sonnet-4-5 \
  --task "Baue pv_dach.py laut PLAN.md. Schrittweise vorgehen, Tests erwähnen, Entscheidungen begründen." \
  --cwd /home/openclaw/safrano9999/PV_D-A-CH
```
Tipps:
- Nutze `--attachments` für relevante Dateien (PLAN.md, DACH.md usw.).
- Wenn Claude Code direkten Datei-Zugriff braucht, gib `--cwd` an (oder `--attach` verzeichnisse).
- Bei langen Tasks lieber eine persistente Session (`--mode session`) wählen.

## 4. Zusammenarbeit
- **Orchestrator** überwacht die Session (via `sessions_list` / `sessions_history`).
- **Claude Code** liefert Patches, Tests, Kommentare. Lass ihn kleine Schritte machen (Pull, Code, Test, Commit).
- Bei Fragen kann die Session direkt angesprochen werden (`sessions_send` + Kontext).

## 5. Abschluss
- Änderungen prüfen (`git status`, Diffformate).
- Tests laufen lassen (`pytest`, `ruff`, etc.).
- Ergebnisse kurz in Vikunja oder DACH.md notieren.
- Session schließen (`sessions_send --message "Danke, fertig"` oder Timeout).

## 6. Best Practices
1. **Kontext klein halten** – nur die Dateien schicken, die wirklich relevant sind.
2. **Klare Akzeptanzkriterien** – verhindert, dass Claude Code „driftet“.
3. **Iterationen erzwingen** – lieber mehrere kurze Läufe als einen riesigen.
4. **Fallback** – wenn Claude Code ein Feature nicht kann, in Vikunja als menschliche Action markieren.

Damit können OpenClaw-Agents (oder du selbst) Claude Code gezielt einsetzen, ohne den Multi-Agent-Plan zu verwässern.
