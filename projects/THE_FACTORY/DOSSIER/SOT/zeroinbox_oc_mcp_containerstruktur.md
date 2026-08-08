# ZeroInbox + OpenClaw + MCP auf Debian im Docker-Container
## konkrete Container- und Prozessstruktur

## Ziel

Dieses Dokument ergänzt die Architekturübersicht und beschreibt eine **praktische Container- und Prozessstruktur** für:

- `offlineimap`
- `Maildir`
- ZeroInbox-Worker
- optional Queue
- OpenClaw
- MCP-Klassifizierungsweg
- PDF-Report-Erzeugung

Schwerpunkt:
- alles in **einem Debian-Container**
- robust genug für echten Betrieb
- nicht unnötig verspielt
- gut an Agenten / "Hummer" delegierbar

---

# 1. Grundentscheidung

Für dein Setup würde ich drei sinnvolle Betriebsarten unterscheiden:

## A. Minimal
Ein Container, ein einfaches Startskript, wenige Prozesse.

Gut wenn:
- du schnell testen willst
- überschaubare Mailmenge
- wenig Overhead
- Debugging direkt per Shell

## B. Solide
Ein Container mit kleinem Prozessmanager, z. B. `supervisord`.

Gut wenn:
- mehrere dauerhafte Prozesse sauber laufen sollen
- Restart-Verhalten wichtig ist
- Logs pro Prozess hilfreich sind

## C. Strenger / produktionsnäher
Ein Container mit `s6-overlay` oder vergleichbarer sauberer Init-/Service-Struktur.

Gut wenn:
- du Container sehr strukturiert bauen willst
- mehrere Services strikt verwalten willst
- Agenten das später systematisch erweitern sollen

---

# 2. Meine Empfehlung

## Für deinen Fall:
**erst B, also `supervisord`**

Warum:

- einfacher als `s6`
- robuster als ein wildes `start.sh` mit mehreren `&`
- klar für Logs und Restarts
- für "Hummer" leicht verständlich
- gut auf Debian im Container

Also:
- **nicht zu minimal**
- **nicht unnötig kompliziert**
- **sauber genug**

---

# 3. Prozessmodell

## Variante A: synchroner einfacher Flow

### Prozesse

1. **OpenClaw**
   - Multi-Channel-Frontdoor
   - ersetzt Telegram solo

2. **Mail Watcher / ZeroInbox Worker**
   - scannt Maildir
   - erkennt neue Mails
   - ruft OC/MCP auf
   - wendet JSON an
   - erzeugt optional PDF

3. **offlineimap Loop**
   - synchronisiert rein und raus
   - läuft periodisch oder dauerhaft in Schleife

### Datenfluss

```text
offlineimap
→ Maildir
→ zeroinbox-worker
→ OpenClaw / MCP
→ JSON zurück
→ Mail verschieben / markieren
→ offlineimap push
```

---

## Variante B: Queue-Flow für viele Mails

### Prozesse

1. **OpenClaw**
   - Multi-Channel-Frontdoor

2. **Mail Detector**
   - erkennt neue Mails
   - erstellt Jobs

3. **Queue Consumer**
   - zieht Jobs
   - ruft OC/MCP auf
   - speichert Ergebnis

4. **Apply Worker**
   - liest fertige Entscheidungen
   - verschiebt / markiert / protokolliert

5. **offlineimap Loop**
   - sync rein / raus

6. **optional Report Worker**
   - erzeugt PDF-Zusammenfassungen separat

### Datenfluss

```text
offlineimap
→ Maildir
→ detector
→ queue
→ consumer
→ OpenClaw / MCP
→ decision store
→ apply worker
→ Maildir Änderungen
→ offlineimap push
```

---

# 4. Verzeichnisstruktur im Container

## Vorschlag

```text
/opt/zeroinbox/
├─ app/
│  ├─ worker.py
│  ├─ detector.py
│  ├─ consumer.py
│  ├─ apply_worker.py
│  ├─ report.py
│  ├─ oc_client.py
│  ├─ mcp_client.py
│  ├─ mail_parser.py
│  ├─ decision_schema.py
│  └─ utils.py
├─ config/
│  ├─ offlineimap.conf
│  ├─ supervisord.conf
│  ├─ zeroinbox.json
│  └─ openclaw.json
├─ state/
│  ├─ queue.sqlite
│  ├─ processed.sqlite
│  ├─ decisions/
│  ├─ reports/
│  └─ logs/
├─ mail/
│  └─ Maildir/
└─ bin/
   ├─ run_offlineimap_loop.sh
   ├─ run_worker.sh
   ├─ run_detector.sh
   ├─ run_consumer.sh
   ├─ run_apply.sh
   └─ run_report.sh
```

---

# 5. Warum diese Struktur gut ist

## `app/`
nur eigentliche Logik

## `config/`
klare Konfigurationen

## `state/`
alles Persistente:
- Queue
- Decisions
- Reports
- Logs
- DBs

## `mail/`
Maildir klar getrennt

## `bin/`
kleine Startskripte pro Prozess, gut für Supervisor

---

# 6. Persistenz / Volumes

Im Container sollten mindestens diese Pfade persistent sein:

```text
/opt/zeroinbox/state
/opt/zeroinbox/mail
```

Optional auch:

```text
/opt/zeroinbox/config
```

wenn du Konfiguration extern überschreiben willst.

## Minimal sinnvoll
- `mail/` persistent
- `state/` persistent

Denn sonst verlierst du:
- Maildir
- Queue
- Reports
- Entscheidungszustände
- verarbeitete IDs

---

# 7. Einfachste Startvariante ohne Supervisor

## Nur für schnellen Test

Ein einzelnes `start.sh` könnte starten:

- OpenClaw
- offlineimap loop
- zeroinbox-worker

### Nachteile
- schwaches Restart-Verhalten
- Logs unordentlich
- Signalhandling unsauber
- bei mehreren Prozessen schnell nervig

## Fazit
Nur zum schnellen Probieren.

---

# 8. Empfohlene Startvariante mit supervisord

## Warum `supervisord`
- auf Debian simpel
- Prozess-Restarts
- getrennte Logs
- klar lesbar
- kein unnötiger Kult

## Logische Programme

### Bei synchroner Variante
- `openclaw`
- `offlineimap-loop`
- `zeroinbox-worker`

### Bei Queue-Variante
- `openclaw`
- `offlineimap-loop`
- `mail-detector`
- `queue-consumer`
- `apply-worker`
- optional `report-worker`

---

# 9. Beispiel: supervisor-Logik

## Synchron

```ini
[supervisord]
nodaemon=true

[program:openclaw]
command=/usr/local/bin/openclaw run
autorestart=true
priority=10

[program:offlineimap]
command=/opt/zeroinbox/bin/run_offlineimap_loop.sh
autorestart=true
priority=20

[program:zeroinbox-worker]
command=/opt/zeroinbox/bin/run_worker.sh
autorestart=true
priority=30
```

## Queue

```ini
[supervisord]
nodaemon=true

[program:openclaw]
command=/usr/local/bin/openclaw run
autorestart=true
priority=10

[program:offlineimap]
command=/opt/zeroinbox/bin/run_offlineimap_loop.sh
autorestart=true
priority=20

[program:mail-detector]
command=/opt/zeroinbox/bin/run_detector.sh
autorestart=true
priority=30

[program:queue-consumer]
command=/opt/zeroinbox/bin/run_consumer.sh
autorestart=true
priority=40

[program:apply-worker]
command=/opt/zeroinbox/bin/run_apply.sh
autorestart=true
priority=50
```

---

# 10. Empfehlung für Queue-Speicher

## Am pragmatischsten: SQLite

Warum:
- lokal
- kein extra Redis
- in einem Container leicht
- robust genug
- Queries / Retries / Status einfach

## Beispieltabellen

### `jobs`
- `job_id`
- `message_id`
- `status`
- `created_at`
- `updated_at`
- `payload_json`
- `attempts`
- `last_error`

### `decisions`
- `job_id`
- `message_id`
- `decision_json`
- `completed_at`

### `processed_messages`
- `message_id`
- `applied_at`
- `target_folder`

Damit kannst du sauber verhindern:
- Doppelverarbeitung
- verlorene Zustände
- unklare Retries

---

# 11. Logik für Retries

## Synchron
Einfacher:
- bei Fehler Mail als `pending` markieren
- später erneut probieren

## Queue
Sauberer:
- `status = queued`
- `status = processing`
- `status = done`
- `status = error`
- `attempts += 1`

Mit z. B. Max-Versuchen:
- 3
- 5
- oder unbegrenzt mit Backoff

---

# 12. Wie OpenClaw hier sitzt

OpenClaw sitzt im selben Container als eigener Prozess.

## Rolle
- Multi-Channel-Eingang
- ersetzt Telegram solo
- nimmt Commands / Requests aus mehreren Kanälen an
- stößt den Klassifizierungsweg an bzw. nimmt ihn entgegen

## Wichtige Trennung
OpenClaw soll **nicht** `offlineimap` ersetzen.  
OpenClaw soll **nicht** `Maildir` scannen.  
Das bleibt lokal.

OpenClaw ist hier:
- Frontdoor
- Decision Path
- Channel Layer

---

# 13. Wie MCP hier sitzt

MCP sitzt logisch zwischen OpenClaw und Klassifizierungslogik.

## In deinem Zielbild
`litellm` fliegt raus aus dem Klassifizierungsweg und wird ersetzt durch:

```text
worker / consumer
→ OpenClaw
→ MCP Toolcall
→ JSON zurück
```

Das heißt:
- dein lokaler Code schickt Payload an OC/MCP
- JSON kommt zurück
- lokale Action wird angewendet

---

# 14. Welche Python-Dateien die Hummer bauen sollen

## Minimalvariante

### `mail_parser.py`
- liest Rohmail
- extrahiert Felder

### `oc_client.py`
- spricht den neuen OC/MCP-Weg an
- liefert JSON-Entscheidung zurück

### `worker.py`
- Maildir scannen
- neue Mails finden
- `parse -> classify -> apply`

### `report.py`
- PDF-Bericht

### `decision_schema.py`
- validiert Rückgabe
- defaults
- Fallbacks

---

## Queue-Variante zusätzlich

### `detector.py`
- erkennt neue Mails
- erzeugt Jobs

### `consumer.py`
- nimmt Jobs
- ruft OC/MCP
- speichert Resultat

### `apply_worker.py`
- wendet Resultate an

### `queue_store.py`
- SQLite-Zugriffe
- Statusverwaltung
- Retries

---

# 15. Wie ich die Startreihenfolge wählen würde

## Synchron
1. OpenClaw
2. offlineimap loop
3. zeroinbox worker

## Queue
1. OpenClaw
2. offlineimap loop
3. detector
4. consumer
5. apply worker
6. optional report worker

Warum:
- OpenClaw sollte vor dem Consumer / Worker da sein
- sonst laufen gleich Fehler in der Klassifikation

---

# 16. Praktische Betriebsmodi

## Modus 1: Polling
Worker scannt alle X Sekunden `Maildir`.

Vorteile:
- simpel
- robust
- in Containern oft gut genug

## Modus 2: inotify
Direkte Reaktion auf neue Dateien.

Vorteile:
- schneller
- eleganter

Nachteile:
- etwas empfindlicher / komplexer
- in Container-Setups manchmal unnötig

## Empfehlung
Erst **Polling**, z. B. alle 10–30 Sekunden.  
Reicht für Mail völlig.

---

# 17. PDF-Report-Platzierung

PDF-Report nicht direkt in den Klassifizierungsprozess pressen, wenn viele Mails kommen.

## Synchron
ok, kann direkt im Worker passieren

## Queue
besser:
- separater Report-Worker
- oder on-demand Report-Build

So bleibt die eigentliche Sortierung schnell.

---

# 18. Fehlerbehandlung

## Was sauber protokolliert werden sollte
- Message-ID
- Subject
- Klassifizierungsrequest
- Rohantwort / validierte Antwort
- Zielordner
- Fehler beim Verschieben
- Retry-Zähler

## Wichtiger Punkt
Bei unbrauchbarem JSON:
- nicht hart crashen
- Mail in `Review` oder `Unsorted`
- Fehler loggen
- optional Report-Eintrag machen

---

# 19. Was ich den Hummern als klare Aufgabe geben würde

## Phase 1: synchron
- Debian-Container bauen
- `supervisord` einrichten
- `offlineimap` integrieren
- Maildir persistent machen
- Worker bauen
- `oc_client.py` als Ersatz für `litellm`
- PDF-Report belassen
- OpenClaw als Multi-Channel-Frontdoor aufnehmen

## Phase 2: Queue
- SQLite-Queue ergänzen
- Detector / Consumer / Apply-Worker splitten
- Retry-Logik
- Reports entkoppeln
- Monitoring / Statuskommandos ergänzen

---

# 20. Meine klare Endempfehlung

## Für den ersten realistischen Umbau
Nimm:

- **Debian-Container**
- **`supervisord`**
- **synchrone Variante**
- **persistente Volumes für Maildir und State**
- **Polling statt inotify**

Das ist der beste Kompromiss aus:
- Einfachheit
- Robustheit
- Delegierbarkeit
- echter Umsetzbarkeit

## Für die zweite Ausbaustufe
Wenn Mails zunehmen:

- SQLite-Queue
- Detector / Consumer / Apply-Aufteilung
- optional separater Report-Worker

---

# 21. Kurzfassung

## Containerbasis
- Debian
- ein Container
- mehrere Prozesse

## Prozessmanager
- Empfehlung: `supervisord`

## Persistenz
- `/opt/zeroinbox/mail`
- `/opt/zeroinbox/state`

## Start klein
- OpenClaw
- offlineimap loop
- synchroner Worker

## Später sauber skalieren
- Detector
- SQLite Queue
- Consumer
- Apply Worker

## Strategischer Schnitt
- **OpenClaw ersetzt Telegram solo durch Multi-Channel**
- **OC/MCP ersetzt `litellm` im JSON-Klassifizierungsweg**
- **offlineimap + Maildir + lokale Anwendung bleiben**

---

# 22. Ein Satz für die Hummer

**Baut zuerst einen Debian-Container mit `supervisord`, persistentem Maildir/State, `offlineimap`, OpenClaw und einem synchronen ZeroInbox-Worker; danach trennt ihr bei Bedarf in Detector + SQLite-Queue + Consumer + Apply-Worker auf.**
