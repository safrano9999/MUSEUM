# 🤖 AGENT HANDBOOK – WARDKEEPER + VIKUNJA

Dieses Dokument erklärt, wie einzelne Agents ihren eigenen Zugang zur Vikunja-Instanz (`https://127.0.0.1:460`) bekommen und den bestehenden `wardkeeper.py`-Workflow selbst bedienen können. Ziel: Jeder Bot hat seine eigenen API-Tokens, arbeitet seine Aufgaben direkt in Vikunja ab und liefert Feedback über dieselben REST-Endpunkte.

---

## 🧭 Architektur in Kürze

1. **Vikunja** = zentrales Kanban + Task-API. Unterstützt Multi-User samt Tokens.
2. **WARDKEEPER** = Python-Client + Zusatz-Datenbank (Ideen, Beliefs, Media). Skript: `~/safrano9999/WARDKEEPER/VIKUNJA/wardkeeper.py`.
3. **Agents** = bekommen eigene Konfig, eigenes Token, eigenes Arbeitsverzeichnis. Jeder ruft `wardkeeper.py` mit _seinem_ Profil auf und sieht nur die Tasks, die ihm zugewiesen wurden.
4. **Orchestrator** = erstellt/aktualisiert Aufgaben (z. B. Steward/Operator) und weist sie den richtigen Agent-Usern in Vikunja zu.

---

## 🛠️ Vorbereitung pro Agent

| Schritt | Beschreibung |
| --- | --- |
| 1️⃣ Vikunja-User anlegen | In der UI (⚙️ → Benutzer) neuen User oder API-Token erzeugen. Optional Teams pro Projekt. |
| 2️⃣ API-Token notieren | `Einstellungen → API Tokens → + API Token`. Token-Kopie geht in `.wardkeeperenv`. |
| 3️⃣ Agent-Ordner erstellen | In `~/safrano9999/WARDKEEPER/VIKUNJA/AGENTS/<agent-id>` (z. B. `argentinia`) einen Unterordner erzeugen. |
| 4️⃣ Config-Dateien kopieren | `wardkeeper.cfg` und `.wardkeeperenv` aus dem Hauptverzeichnis kopieren und für den Agenten anpassen. |
| 5️⃣ Rechte setzen | Sicherstellen, dass nur der Agent bzw. die Host-Userin Zugriff auf seine Token-Datei hat (`chmod 600`). |

### 📂 Beispiel: Verzeichnisstruktur
```
WARDKEEPER/
└── VIKUNJA/
    ├── wardkeeper.py
    ├── wardkeeper.cfg               # globale Defaults
    ├── .wardkeeperenv               # Hauptinstanz
    └── AGENTS/
        ├── argentinia/
        │   ├── wardkeeper.cfg       # optional agent-spezifisch (z. B. anderes Projekt-Default)
        │   └── .wardkeeperenv       # enthält VIKUNJA_BEARER_TOKEN für argentinia
        └── inspirator/
            └── .wardkeeperenv
```

---

## 🔐 Inhalte der Konfigurationsdateien

### `wardkeeper.cfg`
```ini
[vikunja]
url = https://127.0.0.1:460

[database]
host = 127.0.0.1
port = 3306
name = wardkeeper
user = wardkeeper
```
> Tipp: Wenn Agents **nur** Vikunja nutzen sollen, kann der DB-Block unverändert bleiben. Sie greifen dann nicht auf MariaDB-Tabellen zu, solange sie keine `idea/belief/media`-Kommandos verwenden.

### `.wardkeeperenv`
```
# Kopie aus wardkeeperenv_example
VIKUNJA_BEARER_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
MARIADB_PW=yyyyyyyyyyyyyyyyyyyy
```
> Für reine Taskarbeit reicht `VIKUNJA_BEARER_TOKEN`. `MARIADB_PW` wird nur benötigt, wenn der Agent Ideen/Beliefs/Medien persistieren soll.

---

## 🏃‍♂️ Workflow aus Sicht eines Agents

1. **Aktivieren (optional)**
   ```bash
   cd ~/safrano9999/WARDKEEPER/VIKUNJA
   source venv/bin/activate
   ```
2. **Profil-Env laden** (nur wenn separater Ordner)
   ```bash
   export WARDKEEPER_ENV=AGENTS/argentinia/.wardkeeperenv
   export WARDKEEPER_CFG=AGENTS/argentinia/wardkeeper.cfg
   ```
   > (Falls wir das Skript erweitern, können wir `--env-file`/`--config` Flags anbieten; bis dahin per `export`.)
3. **Offene Tasks holen**
   ```bash
   python wardkeeper.py subtasks --open --json
   ```
4. **Task bearbeiten** → Code/Content schreiben.
5. **Status melden**
   ```bash
   python wardkeeper.py set subtask <ID> --done --text "Ergebnis xyz"
   python wardkeeper.py comment <task-id> --text "Deployment fertig"
   ```
6. **Ideen/Beliefs (optional)**
   ```bash
   python wardkeeper.py idea --project <ID> --text "💡 Neue Hypothese"
   ```

---

## 🧩 Orchestrator-Playbook

- **Projekt anlegen**: `python wardkeeper.py add project --name "Agent Missions"`
- **Tasks erstellen** (mit Zuweisung): API-Call `PUT /projects/{id}/tasks` und `assignees: ["agent-user"]` setzen oder in der UI zuweisen.
- **Subtasks** definieren / blockierende Beziehungen pflegen (`block/unblock`).
- **Monitoring**: `wardkeeper.py list --json` zeigt Baum inkl. Fortschritt + Blocker.
- **Feedback zurückspielen**: Agent-Status landet als Kommentar direkt im Task.

---

## 🚀 Erweiterungen & Ideen

- 🧩 **CLI-Flag für Profile**: `wardkeeper.py --profile argentinia subtasks …` (TODO: optional Feature einbauen).
- 🔄 **Automatische Sync-Loops**: Cronjob oder Agent-Heartbeat, der alle X Minuten `subtasks --open` zieht und Ergebnisse postet.
- 🗂️ **Team-basierte Rechte**: In Vikunja Teams/Namespaces nutzen, damit Agents nur „ihre“ Projekte sehen.
- 🛡️ **Token-Rotation**: Pro Agent Service-Account + regelmäßiges Rotieren der API Tokens.
- 🧠 **Self-Assignment**: Agents können via API auch selbst neue Tasks für Nebenprojekte anlegen (dann z. B. Tagging statt direkter Projektzuweisung).

---

## ✅ TL;DR

- Jeder Agent bekommt einen eigenen Ordner unter `VIKUNJA/AGENTS/` + eigenes `.wardkeeperenv` mit seinem Token.
- Orchestrator weist in Vikunja Aufgaben dem passenden Agent-User zu.
- Agent ruft `wardkeeper.py` mit seinem Profil auf, sieht nur seine Tasks und meldet Status zurück.
- So ersetzt Vikunja den klassischen “Mission Control”-Knoten und wird zur gemeinsamen Kommandozentrale für Agents **und** menschliche Operator.

Happy automating! 🤝
