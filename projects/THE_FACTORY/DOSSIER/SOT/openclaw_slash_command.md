# /foobar Slash-Command für Agent `main`

## Ziel

Ein spezieller Agent (`main`) soll einen Slash-Command bekommen:

/foobar

Dieser Command soll **deterministisch (ohne Modell)** das Skript ausführen:

~/scripts/foobar.sh

---

## Architektur

User (Telegram / Slack / Discord / iMessage / ...)
            ↓
         OpenClaw
            ↓
        /foobar
            ↓
        Skill Dispatch
            ↓
      Tool (bash / wrapper)
            ↓
    ~/scripts/foobar.sh
            ↓
        Output zurück

---

## 1. Ort des Skills (wichtig)

~/.openclaw/agents/main/agent/skills/foobar/SKILL.md

👉 nicht global speichern, sonst ist er für alle Agenten sichtbar.

---

## 2. SKILL.md

---
name: foobar
description: Führt das lokale foobar.sh Skript aus
user-invocable: true
disable-model-invocation: true

command-dispatch: tool
command-tool: bash
command-arg-mode: raw
---

Runs the foobar script.

Usage:
  /foobar

This command executes a predefined local script.

---

## 3. Technischer Ablauf

Eingabe:
/foobar

Interne Übergabe:

{
  "command": "",
  "commandName": "foobar",
  "skillName": "foobar"
}

→ wird direkt an das Tool `bash` übergeben.

---

## 4. Mapping auf dein Skript

Direkt:
/home/USER/scripts/foobar.sh

⚠️ Unsicher / nicht sauber kontrolliert

---

## 5. Saubere Variante (empfohlen)

Wrapper:

~/scripts/run_foobar.sh

#!/bin/bash
set -e
exec ~/scripts/foobar.sh

chmod +x ~/scripts/run_foobar.sh

---

## Angepasstes SKILL.md

---
name: foobar
description: Führt das lokale foobar.sh Skript aus
user-invocable: true
disable-model-invocation: true

command-dispatch: tool
command-tool: bash
command-arg-mode: raw
---

~/scripts/run_foobar.sh

---

## 6. Best Practice

Eigenes Tool statt bash:

---
name: foobar
description: Führt foobar.sh aus
user-invocable: true
disable-model-invocation: true

command-dispatch: tool
command-tool: run_foobar
---

Tool führt intern aus:

~/scripts/foobar.sh

---

## 7. Multi-Channel

Funktioniert über:

- Telegram
- Slack
- Discord
- iMessage

---

## 8. Verhalten

/foobar → Skript läuft

- kein LLM
- deterministisch
- direkt

---

## 9. Debug

/help
/tools

---

## 10. Sicherheit

Nicht:
- offene Shell
- ungefilterter Input

Ja:
- festes Skript
- Wrapper oder eigenes Tool

---

## 11. Kurzfassung

- Skill im Agent-Workspace
- `/foobar` verfügbar
- kein Modell
- Tool führt Skript aus
- OpenClaw = Multi-Channel

---

## 12. Ein Satz

/foobar ist ein deterministischer Multi-Channel-Trigger, der dein Skript direkt ausführt.
