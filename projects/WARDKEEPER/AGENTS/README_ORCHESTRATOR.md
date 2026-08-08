# 🕹️ ORCHESTRATOR PLAYBOOK – 100 % VIKUNJA-ONLY

Ziel: Ein Orchestrator-Agent steuert komplette Projekte ausschließlich über die **Vikunja REST API**. Keine zusätzlichen Markdown-Dateien, keine externe MariaDB – alle Informationen (Status, Ideen, Feedback) leben direkt in Vikunja-Tasks, Kommentaren und Tags.

---

## 1. 🌐 Setup des Orchestrators

1. **Service-Account in Vikunja** erstellen (z. B. Benutzer `orchestrator`).
2. **API Token generieren** (`⚙️ → API Tokens`).
3. **Minimal-Konfig**: nur `vikunja_url` + Token.

```
# .wardkeeperenv (oder direkt als Umgebungsvariable)
VIKUNJA_BEARER_TOKEN=xxxxx
```

> Hinweis: `wardkeeper.py` benötigt im „Vikunja-only“-Modus keine DB-Parameter. Alle DB-Aufrufe werden übersprungen oder führen zu klaren Fehlermeldungen.

---

## 2. 🏗️ Projektanlage & Templates

1. **Mission definieren** (z. B. JSON/YAML Vorlage mit Tasks/Subtasks).
2. **Projekt via API erstellen**
   ```bash
   python wardkeeper.py --profile orchestrator add project --name "Mission Vega"
   ```
3. **Tasks/Subtasks importieren**
   - Skript liest Template, erstellt Tasks, setzt Beschreibungen + Tags (`#agent/brazil`, `#deadline/2026-03-20`).
4. **Assignees setzen**
   - Direkt über Vikunja (`assignees`-Feld) oder CLI-Erweiterung.

Alle Metadaten (Parent, Due-Date, Blocker, Beliefs) werden über Task-Description-Markup oder Tags gespeichert, z. B.:
```
🚀 Deliverable: MVP API
Deadline: 2026-03-20
<!-- agent:brazil -->
<!-- blocker:1234 -->
<!-- belief: "Backtest deckt 80% Cases ab" -->
```

---

## 3. 📮 Aufgabenverteilung an Agents

- Jeder Agent besitzt einen eigenen Vikunja-Token (siehe `README_STEWARD.md`).
- Agents lesen ausschließlich „ihre“ Aufgaben anhand von Tags oder Assignee-Feldern.
- Keine weiteren Dateien/DB-Einträge nötig – alles passiert via `GET /tasks`, `PUT /tasks/{id}` und Kommentare.

### Beispiel-Ablauf

1. Orchestrator taggt Task mit `agent:serbia` + `status:todo`.
2. Agent `serbia` ruft `wardkeeper.py subtasks --open --filter agent:serbia` auf.
3. Agent erledigt Arbeit, kommentiert direkt im Task („✅ API Endpoint deployed“), setzt Tag `status:done` oder `done=true` via API.
4. Orchestrator überwacht Tags/Status und erstellt Folge-Tasks, wenn nötig.


### 🧠 Beliefs & Ideen (ohne DB)

- **Kommentar-Modus**: Jeder neue Belief wird als Task-Kommentar gepostet (`Belief: "Hypothese XYZ"`). So bleibt die komplette Chronik direkt im Task sichtbar und lässt sich per API filtern.
- **Belief-Subtasks/Tags**: Alternativ legt der Orchestrator einen Sammel-Task "Beliefs" an; jeder Agent erstellt dort Subtasks (oder nutzt das Tag `#belief`). Damit lassen sich Hypothesen wie reguläre Todo-Einträge verwalten.
- **Automatisierung**: `wardkeeper.py belief` kann später einfach einen Kommentar mit dem Präfix `Belief:` erzeugen – ohne zusätzliche Dateien oder Tabellen.

---

## 4. 🔁 Kontroll- & Feedback-Loop (ohne externe DB)

| Schritt | Mechanismus | Tool |
| --- | --- | --- |
| Fortschritt ziehen | `GET /projects/{id}/tasks` | Cronjob oder Heartbeat-Script |
| Kommentare/Beliefs | `PUT /tasks/{id}/comments` | Agents posten direkt in Vikunja |
| Blocker melden | Tag `status:blocked` + Kommentar | Agent |
| Review & Escalation | Orchestrator-Report (JSON → Telegram) | Cron `*/30 * * * *` |

**Cron/Heartbeat-Idee:**
```
*/10 * * * * /usr/bin/python wardkeeper.py --profile serbia subtasks --open --auto-exec
*/30 * * * * /usr/bin/python wardkeeper.py --profile orchestrator report --project Mission-Vega
```

> Alle Reports/Kommentare bleiben innerhalb von Vikunja – dadurch ist der komplette Missionsverlauf nachvollziehbar, ohne externe Artefakte.

---

## 5. 🧭 Umsetzungsschritte

1. `wardkeeper.py` um einen `--vikunja-only` Schalter ergänzen (DB-Aufrufe deaktivieren).
2. Templates definieren, damit der Orchestrator Projekte/Tasks aus JSON erzeugen kann.
3. Filter-Logik für Agents (z. B. `--filter agent:uk`), damit sie ohne DB nur relevante Tasks ziehen.
4. Cron/Heartbeat-Skripte schreiben, die Aufgaben periodisch holen und Statusberichte senden.
5. Optional: Telegram-Bridge für Orchestrator-Reports (purely read-only, alle Daten bleiben in Vikunja).

---

## ✅ Fazit

- Single Source of Truth = Vikunja.
- Orchestrator + Worker-Agents sprechen ausschließlich über Vikunja-Endpunkte.
- Keine Markdown-Notizen, keine MariaDB – Kommentare, Tags und Beschreibungen reichen völlig, um Status, Ideen und Blocker zu tracken.
- Damit lässt sich der komplette Agent-Workflow containerisieren und leichter für „Self-Build“-Bots ausrollen.
