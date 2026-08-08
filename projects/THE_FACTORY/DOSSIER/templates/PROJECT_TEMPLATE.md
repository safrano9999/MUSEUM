# [PROJECT_NAME]

**Beschreibung**: [Ein Satz: Was ist das Ziel?]

---

## A. Sollzustand

[Stichpunkte: Was soll das Programm tun? Input → Processing → Output?]

---

## B. Health Check & UI

**Projekt-Typ**: [CLI / Headless Server / WebUI / Desktop-GUI (Qt/Electron) / API / etc.]

**Implementierung**: [Sprache + Framework, z.B. "Python mit Flask", "Go mit Gin", "Node.js mit React", "Standalone Binary", etc.]

Zu Beginn prüft das Programm alle erforderlichen Abhängigkeiten (Dependencies, Connections, Ports, etc.). Klappt das, zeigt es einen grünen ✔️ und ist ready. Schlägt etwas fehl, gibt es einen roten Hinweis + Exitcode.

**Features**:
- [Feature 1 + Beispiel-Nutzung: `python script.py --flag <arg>`]
- [Feature 2 + Beispiel]
- [Feature N + Beispiel]

**Standardverhalten**: [Was macht das Skript ohne Argumente?]

---

## C. Dependencies

- [Sprache + Version: z.B. Python 3.10+]
- [Libraries: z.B. requests, pandas, web3.py]
- [Externe Services: z.B. API-Keys, Datenbanken]
- [System-Tools: z.B. Docker, ffmpeg]

---

## D. Artefakte, Dateien & Libraries

- `[script_name].py` – Hauptskript
- `.[PROJECT]env` – Secrets (API-Keys, Credentials)
- `[project].toml` – Technische Parameter
- `requirements.txt` – Python-Dependencies

---

## E. Peripherie

[Datenbank-Schema, Queue-Struktur, externe Schnittstellen, falls relevant]

```
Input (CLI Arguments)
  ↓
Core Logic / Pipeline
  ↓
Data Processing / External APIs
  ↓
Output (Terminal / DB / File)
```

---

## F. Ideen & Weiteres

- [Erweiterungsidee 1]
- [Nice-to-have Feature]
- [Offene Frage / Research-Task]


---

## Z. Vom Architect auszufüllen

Bevor Übergabe an den Orchestrator:

- [ ] **Single oder Multi-Agent?** (Step 0 Entscheidung)
  - [ ] Single → Claude Code Workflow
  - [ ] Multi → Orchestrator mit Worker-Agents
  
- [ ] **Blackbox Research abgeschlossen?** (falls nötig)
  - Welche kritischen Technologien/APIs?
  - Kosten/Rate-Limits geklärt?

- [ ] **Datenquellen erreichbar & getestet?**
  - Alle APIs erreichbar?
  - Secrets konfiguriert?

- [ ] **Entwicklungs-Setup fertig?**
  - venv / Dependencies installierbar?
  - Alle Configs vorlagen fertig?

- [ ] **Worker-Agent Strategie geklärt?**
  - Ad-hoc (Run-Sessions) oder persistent?
  - Welche Rollen? (Code, Vision, DB, Reporting, etc.)

- [ ] **Gibt es Milestones / Phasen?**
  - Kann das Projekt schrittweise gebaut werden?
  - Oder muss alles auf einmal?
  - Welche Ziele sind nach Phase 1, 2, 3 erreicht?

