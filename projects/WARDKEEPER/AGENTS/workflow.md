# 🧩 Agent-Workflow (Vikunja-Only)

## 0. Preparation & Decision
- Gemeinsam mit dem User entscheiden, ob der Use Case als Single-Agent (z. B. reines Skript) oder Multi-Agent-Workflow laufen soll.
- Wenn **Single-Agent** gewählt wird → direkt `CLAUDECODE_INSTRUCTION_SKILLS.md` folgen (Claude Code Workflow).
- Nur wenn **Multi-Agent** gewünscht ist, geht es mit Schritt 1 ff. weiter.
- Zur Orientierung dienen die Referenz-Repos `agents/agency-agents` und `agents/openclaw-multi-agent-kit` sowie projektspezifische Dossiers (z. B. DACH.md).
- Preparations = Setup von DB/Secrets (`.PV_D-A-CHenv`), Token-Verteilung und alle Vorarbeiten, damit Agents später loslegen können.

## 1. Rollen
- **Orchestrator-Agent**: legt Projekte/Tasks an, weist sie zu, überwacht Fortschritt.
- **Worker-Agents**: führen die Subtasks aus (OSM, Sat-Bilder, Vision, Reporting usw.).
- **Operator (Mensch)**: definiert Missionsziele, prüft Reports, greift nur bei Eskalationen ein.

## 2. Setup-Schritte
1. Orchestrator spawnt Worker-Bots.
2. Für jeden Bot: Vikunja-User + API-Token anlegen → in `AGENTS/<bot>/.wardkeeperenv` schreiben.
3. Optional: pro Bot eigene `wardkeeper.cfg` (falls unterschiedliche Defaults nötig).
4. Orchestrator pflegt Missions-Templates (JSON/YAML) mit Tasks/Subtasks/Tags.

## 3. Missions-Lifecycle
1. **Mission anlegen**
   - `wardkeeper.py add project --name "Mission …"` (Profil: orchestrator)
   - Tasks/Subtasks aus Template erzeugen, Beschreibungen mit Links/Beliefs füllen.
2. **Zuweisung**
   - `assignees` + Tags (`agent:osm`, `agent:vision`).
3. **Ausführung**
   - Worker-Agents: `wardkeeper.py --profile <bot> subtasks --open --filter agent:<bot>`
   - Subtask erledigen → `set subtask <id> --done --text "Ergebnis…"` + Kommentar `Belief: …` falls nötig.
4. **Monitoring**
   - Orchestrator-Cron (z. B. alle 30 Min) ruft `wardkeeper.py list --json` oder `report` auf und pusht Status nach Telegram.
5. **Eskalationen**
   - Tags `status:blocked`, Kommentare `Blocker: …` → Orchestrator reagiert (neue Tasks, Reminder, Mensch informieren).
6. **Abschluss**
   - Wenn alle Subtasks done → Orchestrator markiert Task/Projekt als abgeschlossen, archiviert Ergebnisse.

## 4. Taktung
- **Worker-Heartbeat**: `*/10 * * * * wardkeeper.py --profile <bot> subtasks --open …`
- **Orchestrator-Report**: `*/30 * * * * wardkeeper.py --profile orchestrator report --project <id>`
- **Sofort-Push**: Sobald ein Worker fertig ist, sofort `set subtask --done` + Kommentar (kein Warten auf Cron).

## 5. Datenquellen & Artefakte
- In jeder Task-Beschreibung stehen die relevanten Pfade (Repo, Bucket, API-Endpunkt).
- Agents hängen Zwischenergebnisse als Kommentare/Attachments an oder verlinken auf dedizierte Speicherorte.
- Der Orchestrator pflegt eine kurze Naming-Konvention (`/data/raw`, `/data/processed`, usw.), damit jeder Bot sofort weiß, wohin Ergebnisse gehören.

## 6. Tooling
- `wardkeeper.py` wird um `--profile`/`--env-file` erweitert (TODO), damit Agents nicht manuell exportieren müssen.
- `belief`-Command schreibt Kommentare `Belief: …` direkt in Vikunja (kein MariaDB).
- Telegram dient nur als Notification-/Review-Layer.

Mit diesem Workflow bearbeiten die Agents komplette Missionen ausschließlich via Vikunja + wardkeeper, ohne zusätzliche DB oder Markdown-Dateien.
