# OpenClaw Playbook: Einen Agenten über Telegram-Topics in getrennte Session-Lanes splitten

## Ziel
Einen bestehenden Agenten (z. B. `archivar`) über **einen Telegram-Bot** in einer Supergruppe mit Topics in mehrere getrennte Session-Kontexte aufteilen.

Ergebnisbeispiel:
- `agent:archivar:telegram:group:-100...:topic:2`
- `agent:archivar:telegram:group:-100...:topic:4`

## Voraussetzungen
- OpenClaw läuft lokal und Telegram-Channel ist aktiv.
- Bot-Token ist bereits in `openclaw.json` vorhanden.
- Du hast Admin-Zugriff auf BotFather und die Telegram-Gruppe.

---

## Schritt-für-Schritt

### 1) BotFather: Privacy deaktivieren
In BotFather:
- `/setprivacy`
- Ziel-Bot auswählen
- **Disable**

Optional prüfen:
- `/setjoingroups` → Bot darf Gruppen beitreten

> Ohne deaktivierte Privacy kommen Group/Topic-Nachrichten oft nicht sauber als Updates an.

---

### 2) Bot in Supergruppe einladen
- Bot als Mitglied zur Supergruppe hinzufügen.
- Bei Problemen: Bot einmal entfernen und erneut hinzufügen.

---

### 3) Topics aktivieren + zwei Topics anlegen
In Gruppen-Einstellungen:
- **Themen/Forum** aktivieren
- Mindestens 2 Topics anlegen (z. B. `archivar-1`, `archivar-2`)

---

### 4) Gruppenlink holen
Beispiel-Link:
- `https://t.me/c/3833825679/2`

Dabei ist `3833825679` der relevante Teil.

---

### 5) Gruppen-ID in Telegram-Chat-ID umrechnen
Regel:
- `3833825679` → `-1003833825679`

Diese `-100...`-ID wird in OpenClaw verwendet.

---

### 6) Mention-Pflicht global für diese Gruppe deaktivieren (CLI)
```bash
openclaw config set channels.telegram.groups --strict-json '{"-1003833825679":{"requireMention":false}}'
```

Damit verarbeitet der Bot Nachrichten in der Gruppe ohne zwingendes Mention-Muster.

---

### 7) Binding auf den Ziel-Agent setzen (CLI)
Beispiel für `archivar` + `archivarbot`-Account:
```bash
openclaw config set bindings --strict-json '[{"agentId":"archivar","match":{"channel":"telegram","accountId":"archivarbot"}}]'
```

> Falls du mehrere bestehende Bindings hast, diese vorher sichern und dann merge-fähig ergänzen (nicht blind überschreiben).

---

### 8) Gateway neu starten
```bash
openclaw gateway restart
```

---

### 9) In beiden Topics je eine Testnachricht senden
- Topic 1: `test topic 1`
- Topic 2: `test topic 2`

Falls nötig, einmal mit Command testen:
- `/start`
- `@deinbot /start`

---

### 10) Prüfen, ob getrennte Session-Keys entstanden sind
Erwartung:
- `...:topic:<id1>`
- `...:topic:<id2>`

Damit ist der Split erfolgreich.

---

## Verifikation (schnell)
- OpenClaw-Logs: Group-Events kommen ohne `reason: no-mention`.
- Session-Liste zeigt zwei Topic-Lanes.
- Antworten in Topic 1 beeinflussen Kontext von Topic 2 nicht.

---

## Typische Fehlerbilder + Fix

### A) Bot antwortet im DM, aber nicht in Topics
Ursache meist Telegram-seitig (Privacy/Rechte/Bot nicht korrekt in Gruppe aktiv).

Fix:
1. Privacy disable prüfen
2. Bot raus/rein in Gruppe
3. Test erneut

### B) Logs zeigen `reason: no-mention`
`requireMention` ist effektiv noch aktiv.

Fix:
- Step 6 erneut setzen und Gateway restart.

### C) Keine getrennten Session-Lanes trotz Topics
Routing landet nicht topic-spezifisch (oder keine Topic-Updates kommen rein).

Fix:
- Topics wirklich aktiv?
- Nachrichten in verschiedenen Topics gesendet?
- Session-Keys nach `:topic:` prüfen.

---

## Architektur-Merksatz
- Ein Bot kann mehrere Topic-Lanes fahren.
- Jeder Topic-Thread erzeugt einen eigenen Session-Kontext.
- So bekommst du Split ohne `main2`-Hack.

---

## CLI-Only Ablauf (copy/paste)

```bash
# 1) Mention-Pflicht für die Zielgruppe aus
openclaw config set channels.telegram.groups --strict-json '{"-1003833825679":{"requireMention":false}}'

# 2) Group-Command-Autorisierung setzen
openclaw config set channels.telegram.groupAllowFrom --strict-json '["tg:5475045993","5475045993"]'

# 3) Binding auf archivar (Account-bezogen)
openclaw config set bindings --strict-json '[{"agentId":"archivar","match":{"channel":"telegram","accountId":"archivarbot"}}]'

# 4) Gateway neu laden
openclaw gateway restart
```

---

## Reifes Config-Muster (JSON, ohne Secrets)

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "groupPolicy": "open",
      "groupAllowFrom": [
        "tg:5475045993",
        "5475045993"
      ],
      "groups": {
        "-1003833825679": {
          "requireMention": false,
          "allowFrom": [
            "tg:5475045993"
          ]
        }
      },
      "accounts": {
        "archivarbot": {
          "name": "archivar",
          "enabled": true,
          "dmPolicy": "pairing",
          "groupPolicy": "open",
          "streaming": "partial",
          "botToken": "<REDACTED>"
        }
      }
    }
  },
  "bindings": [
    {
      "agentId": "archivar",
      "match": {
        "channel": "telegram",
        "accountId": "archivarbot"
      }
    }
  ]
}
```

> Hinweis: Session-Split über Topics entsteht zur Laufzeit automatisch als
> `agent:archivar:telegram:group:-1003833825679:topic:<id>`.
