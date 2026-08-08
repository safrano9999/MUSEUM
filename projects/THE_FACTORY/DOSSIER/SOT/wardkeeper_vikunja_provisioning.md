# Plan: Vikunja Agent Provisioning

## Context

Vikunja läuft (wird gerade hierher umgezogen auf openclaw). Rafaels User ist angelegt. Jetzt müssen alle Agenten aus `openclaw.json` eigene Vikunja-User + API-Tokens bekommen, plus ein Skill und Heartbeat-Template pro Agent.

## Voraussetzung

- Vikunja-Container läuft lokal unter openclaw (podman exec Zugriff)
- PostgreSQL erreichbar vom Container

## Script: `provision_agents.py`

Ort: `/home/openclaw/safrano9999/WARDKEEPER/provision_agents.py`

### Was es tut:

1. **openclaw.json lesen** (`/home/openclaw/.openclaw/openclaw.json`)
   - Alle Agenten aus `agents.list` extrahieren (id, name, workspace)
   - `main` überspringen (das ist kein Wardkeeper-Agent)

2. **Pro Agent prüfen: existiert Vikunja-User?**
   - `podman exec vikunja /app/vikunja/vikunja user list` parsen (oder Login-Versuch via API)
   - Falls User existiert → weiter zu Token-Schritt
   - Falls nicht → interaktiv fragen ob anlegen (y/n)
   - Abgelehnte Agenten in einer lokalen `.provision_skipped` Datei merken
   - Bei `--ask-all` Flag: `.provision_skipped` ignorieren, nochmal alle fragen

3. **User anlegen** (falls bestätigt)
   - `podman exec vikunja /app/vikunja/vikunja user create -u <agent_id> -e <agent_id>@wardkeeper.local -p <generiertes_passwort>`
   - Passwort generieren (secrets.token_urlsafe) und lokal speichern

4. **API-Token holen**
   - Via Vikunja REST API: Login mit User/Passwort → JWT
   - JWT nutzen um API-Token zu erstellen (POST /api/v1/tokens)
   - Token lokal speichern als `.vikunjaenv` im Agent-Workspace

5. **Skill.md erstellen** im Agent-Workspace
   - Template mit Vikunja-Verbindungsinfos + API-Token-Referenz
   - Erklärt dem Agent wie er wardkeeper.py mit seinem Token nutzt
   - Zeigt auf die `.vikunjaenv` Datei

6. **Workspace-Verzeichnisse anlegen** falls nicht vorhanden

### Flags:
- `--ask-all` — fragt auch bei zuvor abgelehnten Agenten erneut
- `--dry-run` — zeigt was passieren würde ohne Änderungen

### State-Dateien:
- `.provision_skipped` — Liste abgelehnter Agent-IDs (im WARDKEEPER-Repo, gitignored)
- Pro Agent: `<workspace>/.vikunjaenv` — API-Token
- Pro Agent: `<workspace>/credentials.json` — User/Passwort (lokal, gitignored)

## Heartbeat-Template

Datei: `/home/openclaw/SKILLS/SOULS/_templates/HEARTBEAT_VIKUNJA.md`

Inhalt (wird pro Agent in dessen `HEARTBEAT.md` geschrieben):

```
1. Lies dein SKILL.md — dort steht wie du dich bei Vikunja anmeldest
2. Führe `wardkeeper.py list` aus mit deinem Token
3. Gibt es offene Tasks für dich? 
   - Ja → Informiere den User (über deinen Telegram-Bot), frag ob du anfangen sollst
   - Nein → Melde "Keine offenen Tasks" und beende
4. Arbeite den Task ab
5. Wenn fertig: `wardkeeper.py done <task_id>` — markiere als erledigt
6. Informiere den User über Telegram dass der Task erledigt ist
```

## Bestehender Code der wiederverwendet wird

- `wardkeeper.py` — VikunjaClient Klasse für API-Calls (`/home/openclaw/safrano9999/WARDKEEPER/wardkeeper.py:117`)
- `.vikunjaenv` Pattern — bereits etabliert für Token-Storage
- SOUL-Dateien unter `/home/openclaw/SKILLS/SOULS/` — Struktur ist bekannt

## Verifizierung

1. Script starten: `python3 provision_agents.py`
2. Prüfen ob User in Vikunja existieren: `podman exec vikunja /app/vikunja/vikunja user list`
3. Prüfen ob `.vikunjaenv` + `SKILL.md` in jedem Agent-Workspace liegen
4. Einen Agent manuell testen: mit seinem Token `wardkeeper.py list` aufrufen
