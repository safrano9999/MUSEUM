# ZeroInbox → OpenClaw / MCP Umbau auf Debian im Docker-Container

## Ziel

Es gibt **zwei Ersetzungen**:

1. **Telegram solo wird ersetzt durch OpenClaw als Multi-Channel-Frontdoor**
   - Telegram
   - Slack
   - Discord
   - iMessage / BlueBubbles
   - weitere OC-Kanäle

2. **`litellm`-Direktcall wird ersetzt durch `OpenClaw + MCP` als JSON-Entscheidungsweg**
   - bisher: Mailbody -> `litellm` -> JSON
   - neu: Mailbody -> `OpenClaw / MCP` -> JSON

Der bestehende Mail-Teil bleibt im Kern erhalten:

- `offlineimap` macht Sync
- neue Mails landen im `Maildir`
- lokaler Worker erkennt neue / unklassifizierte Mails
- JSON-Entscheidung wird angewendet
- Mail wird verschoben / markiert
- `offlineimap` pusht wieder hoch

---

## Zielbild gesamt

```text
Channels (Telegram / Slack / Discord / iMessage / ...)
                         ↓
                      OpenClaw
                         ↓
                    MCP / Toolcall
                         ↓
                 ZeroInbox Classification
                         ↓
                    JSON Decision
                         ↓
      Maildir Worker wendet Entscheidung lokal an
                         ↓
                 offlineimap pusht wieder hoch
```

---

## Was bleibt gleich

Diese Teile bleiben:

- Debian
- Docker-Container
- `offlineimap`
- `Maildir`
- lokaler Parser
- Verschieben / Markieren / Taggen
- PDF-Report-Erzeugung
- Rücksync über `offlineimap`

---

## Was ändert sich

Vorher:

```text
offlineimap sync
→ neue Mail liegt im Maildir
→ lokaler Worker liest Mail
→ `litellm`-Call
→ JSON kommt zurück
→ Mail wird verschoben
→ offlineimap sync zurück
```

Nachher:

```text
offlineimap sync
→ neue Mail liegt im Maildir
→ lokaler Worker liest Mail
→ OpenClaw / MCP JSON-Toolcall
→ JSON kommt zurück
→ Mail wird verschoben
→ offlineimap sync zurück
```

---

# Variante A: einfache synchrone Variante

## Idee

Der bestehende ZeroInbox-Worker bleibt erhalten und ersetzt **nur** den bisherigen `litellm`-Call durch einen synchronen Call an OpenClaw / MCP.

Das ist die direkte 1:1-Ersetzung.

## Ablauf

```text
offlineimap sync
→ neue Mail liegt im Maildir
→ Worker findet neue Mail
→ Worker baut JSON-Payload
→ Worker ruft OpenClaw / MCP synchron auf
→ OC/MCP klassifiziert
→ JSON kommt direkt zurück
→ Worker wendet Entscheidung an
→ Worker verschiebt / markiert Mail
→ offlineimap pusht zurück
```

## Rollen

### 1. offlineimap
- holt neue Mails
- pusht spätere Änderungen zurück

### 2. ZeroInbox Worker
- scannt `Maildir`
- erkennt neue/unverarbeitete Nachrichten
- extrahiert:
  - `message_id`
  - `from`
  - `subject`
  - `body`
  - optional Anhänge / Header / Datum
- ruft OC/MCP auf
- wendet JSON lokal an

### 3. OpenClaw
- ersetzt Telegram als Frontdoor
- ist Multi-Channel-Einstieg
- stößt den Klassifizierungsweg an
- liefert JSON zurück

### 4. MCP Tool / Classification Layer
- nimmt Payload entgegen
- macht die eigentliche Klassifikation
- liefert stabiles JSON-Schema zurück

## Beispielablauf

```text
Maildir Worker
→ classify_email(payload)
→ OpenClaw / MCP
→ JSON zurück
→ apply_decision(mail, json)
```

## Beispiel-Payload

```json
{
  "message_id": "abc-123",
  "from": "kunde@example.com",
  "subject": "Rechnung März",
  "body": "Hallo, anbei die Rechnung ..."
}
```

## Beispiel-Response

```json
{
  "category": "invoice",
  "priority": "low",
  "needs_reply": false,
  "target_folder": "Finance/Rechnungen",
  "summary": "Rechnung ohne Antwortbedarf"
}
```

## Vorteile

- kleinster Umbau
- nah am bestehenden Setup
- leicht debugbar
- direkte 1:1-Ersetzung für `litellm`
- gut für geringe bis mittlere Mailmengen

## Nachteile

- Worker wartet blockierend auf die Antwort
- bei vielen Mails langsamer
- wenn OC/MCP kurz hängt, hängt die Klassifikation mit
- weniger robust bei Peaks

## Wann diese Variante reicht

- kleine bis mittlere Mailmenge
- saubere Einzelklassifikation
- erst einmal möglichst wenig Umbau
- Fokus auf schnelles Live-Gehen

---

# Variante B: Queue-Variante für viele Emails

## Idee

Der Worker klassifiziert nicht mehr sofort synchron, sondern erstellt Jobs.  
Diese Jobs werden in eine Queue gelegt. Ein separater Consumer / Dispatcher spricht OpenClaw / MCP an. Die Antworten werden danach vom lokalen Apply-Schritt verarbeitet.

Das ist bei vielen Mails die sauberere Architektur.

## Ablauf

```text
offlineimap sync
→ neue Mails liegen im Maildir
→ Detector erkennt neue Mails
→ pro Mail wird ein Klassifizierungsjob erzeugt
→ Job landet in Queue
→ Queue-Worker zieht Jobs
→ Queue-Worker ruft OpenClaw / MCP auf
→ JSON kommt zurück
→ Ergebnis wird persistent gespeichert
→ Apply-Worker verschiebt / markiert Mail
→ offlineimap pusht zurück
```

## Logische Komponenten

### 1. Detector
- scannt Maildir
- erkennt neue Mails
- erzeugt Jobs

### 2. Queue
Mögliche Minimalformen im Container:
- Dateiqueue
- SQLite-Queue
- JSONL-Queue
- Redis wäre möglich, aber für lokal nicht zwingend nötig

Für dein Setup auf einem Debian-Docker wäre eine **SQLite-Queue** oder **Dateiqueue** oft am pragmatischsten.

### 3. Queue-Consumer
- nimmt Jobs in definierter Reihenfolge
- ruft OC/MCP auf
- schreibt Ergebnisse zurück

### 4. Apply-Worker
- liest fertige Entscheidungen
- verschiebt / markiert Mails
- führt lokale Nebenwirkungen aus

### 5. offlineimap
- pusht Änderungen hoch

## Datenfluss

```text
Maildir
→ Detector
→ Queue Job
→ OC/MCP Consumer
→ Decision Store
→ Apply Worker
→ Mail Move / Tag / Report
→ offlineimap push
```

## Beispiel-Job

```json
{
  "job_id": "job-001",
  "message_id": "abc-123",
  "from": "kunde@example.com",
  "subject": "Rechnung März",
  "body": "Hallo, anbei die Rechnung ...",
  "status": "queued"
}
```

## Beispiel-Decision

```json
{
  "job_id": "job-001",
  "message_id": "abc-123",
  "status": "done",
  "decision": {
    "category": "invoice",
    "priority": "low",
    "needs_reply": false,
    "target_folder": "Finance/Rechnungen"
  }
}
```

## Vorteile

- sauber bei vielen Mails
- robust gegen Bursts
- Retries möglich
- bessere Entkopplung
- OC/MCP kann langsamer sein, ohne den Detector zu blockieren
- gutes Logging / Audit pro Job
- spätere Parallelisierung möglich

## Nachteile

- mehr Komponenten
- mehr Zustand
- etwas mehr Code
- aufwendigeres Debugging als bei der synchronen Variante

## Wann diese Variante besser ist

- viele Mails in Wellen
- klare Wiederholbarkeit / Retry wichtig
- spätere Statistik / Monitoring gewünscht
- saubere Entkopplung ist wichtiger als Minimalismus

---

# Multi-Channel-Ersatz für Telegram solo

## Alt

```text
Telegram
→ Sortierroutine starten
→ PDF zurück
```

## Neu

```text
Telegram / Slack / Discord / iMessage / ...
                    ↓
                 OpenClaw
                    ↓
      run_inbox_sort / classify_email / get_report
                    ↓
                 ZeroInbox
```

## Bedeutung

Telegram ist dann nicht mehr die Sonderlogik.  
Telegram ist nur noch **ein Kanal unter mehreren**.

Die eigentliche Logik sitzt dahinter:

- Sortierroutine
- Klassifikation
- PDF-Generierung
- Ergebnisbereitstellung

## Was OpenClaw in dieser Architektur übernimmt

- einheitlicher Eingang über mehrere Kanäle
- kanalübergreifende Trigger
- derselbe Befehl kann von jedem Kanal kommen
- derselbe Report kann über verschiedene Kanäle bereitgestellt werden

## Was OpenClaw nicht übernehmen muss

- Maildir-Scan
- IMAP-Sync
- lokales Verschieben von Dateien
- lokale Anwendung der Entscheidung

Diese Dinge bleiben lokal im ZeroInbox-Container-Teil.

---

# Wo genau OC + MCP eingreifen

Wichtig:

**Nicht** `offlineimap` spricht direkt mit OC.  
**Nicht** `Maildir` spricht direkt mit OC.

Sondern:

**der lokale Worker / Detector / Queue-Consumer** ersetzt an der bisherigen Klassifizierungsstelle den `litellm`-Call durch einen OC/MCP-Call.

Also genau hier:

```text
Mail entdeckt
→ classify(...)
→ JSON zurück
→ anwenden
```

Vorher:

```python
decision = litellm_classify(payload)
```

Nachher:

```python
decision = oc_mcp_classify(payload)
```

---

# Empfohlene Trennung der Verantwortlichkeiten

## offlineimap
- Sync rein
- Sync raus

## Maildir Detector / Worker
- neue Mails erkennen
- Maildaten extrahieren
- OC/MCP anstoßen oder Queue erzeugen

## OpenClaw
- Multi-Channel-Frontdoor
- Trigger / Steuerung
- kanalübergreifende Eingangsseite

## MCP / Classification Tool
- JSON-Klassifikation
- stabiles Entscheidungsschema

## Apply Layer
- Folder anwenden
- Tags anwenden
- PDF erzeugen
- Ergebnis protokollieren

---

# Docker / Debian Gesamtschnitt

## Alles auf einem Debian im Docker-Container

Ziel: alles lokal in **einem Debian-Container**.

### Enthaltene Prozesse
- `offlineimap`
- ZeroInbox Detector / Worker
- optional Queue / Queue-Consumer
- OpenClaw
- MCP-Tool / Adapter
- PDF-Generator

## Einfache Variante im Container

```text
[ Debian Container ]
  ├─ offlineimap
  ├─ maildir
  ├─ zeroinbox-worker
  ├─ openclaw
  └─ mcp classification path
```

## Queue-Variante im Container

```text
[ Debian Container ]
  ├─ offlineimap
  ├─ maildir
  ├─ detector
  ├─ queue store
  ├─ queue consumer
  ├─ apply worker
  ├─ openclaw
  └─ mcp classification path
```

---

# Empfehlung

## Wenn du schnell produktiv umbauen willst
Nimm zuerst **Variante A**:

- direkte synchrone Ersetzung
- wenig Umbau
- schnell testbar
- leicht zu verstehen

## Wenn du schon weißt, dass Mailmengen groß werden
Plane **Variante B**:

- Queue sauberer
- stabiler bei Peaks
- langfristig besser
- besser für Logging und Retries

---

# Klare Kurzfassung

## Was wird ersetzt?
- **Telegram solo** → durch **OpenClaw Multi-Channel**
- **`litellm`-JSON-Call** → durch **OC/MCP JSON-Toolcall**

## Was bleibt?
- `offlineimap`
- `Maildir`
- lokaler Parser
- lokale Anwendung der Entscheidung
- Rücksync

## Wo sitzt der neue Call?
- genau dort, wo heute `litellm_classify(...)` sitzt

## Welche zwei Varianten gibt es?
- **Variante A:** synchron, einfach, direkt
- **Variante B:** Queue, sauber bei vielen Mails

---

# Praktischer Schluss

Der technisch kleinste erste Umbau ist:

1. `offlineimap` bleibt
2. `Maildir` bleibt
3. Worker bleibt
4. nur die Funktion `classify_mail(payload)` wird ersetzt:
   - alt: `litellm`
   - neu: `OC/MCP`
5. danach optional Ausbau zu Queue

Das ist der sauberste Pfad von deinem heutigen System in die neue Architektur.
