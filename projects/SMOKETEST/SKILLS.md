# CLAWBRIDGE — Extension Development Guide

> This document is the authoritative reference for building a new CLAWBRIDGE extension.
> SMOKETEST itself is the minimal reference implementation — read it alongside this guide.
> Written for AI assistants and developers alike.

---

## 1. What is CLAWBRIDGE?

CLAWBRIDGE is the central dispatcher and Telegram bot for this ecosystem. It has two jobs:

1. **dispatcher.sh** — watches a directory (`TRIGGERDIR`) via `inotify`, picks up trigger files,
   looks up the matching job in the merged registry, checks actor policy, runs the script, sends
   Telegram feedback.

2. **bot_core.py** — Telegram bot that auto-discovers plugin commands and either drops a JSON
   command file for the dispatcher to pick up, or loads a Python handler directly.

Extensions (sibling projects) plug in via a single file: `clawbridge_plugin.json`.
No edits to CLAWBRIDGE itself are ever needed.

---

## 2. Ecosystem Layout

```
~/safrano9999/
├── CLAWBRIDGE/                  ← BOSS — venv, credentials, config live here
│   ├── venv/                    ← shared Python venv (all extensions install here)
│   ├── .botenv                  ← BOT_TOKEN, CHAT_ID  (never commit)
│   ├── .env                     ← LLM API keys         (never commit)
│   ├── .mysqlenv                ← DB credentials       (never commit)
│   ├── clawbridge.conf          ← path overrides (TRIGGERDIR, PROJECTS_DIR, LOG_DIR)
│   ├── dispatcher_filebased_rules.json
│   ├── clawbridge_plugin.json   ← CLAWBRIDGE's own jobs
│   ├── bin/
│   │   ├── clawbridge.sh        ← unified entry point (starts dispatcher + bot)
│   │   ├── dispatcher.sh        ← inotify loop + job runner
│   │   ├── bot_core.py          ← Telegram bot
│   │   └── setup.py             ← installs all sibling requirements into venv
│   └── TRIGGERDIR/              ← default; overridden by clawbridge.conf in production
│       ├── $USER/              ← actor subfolder (Telegram bot writes here)
│       ├── claude/              ← actor subfolder (Claude agent drops here)
│       ├── openclaw/            ← actor subfolder (internal/cron drops here)
│       └── OUTBOX/              ← drop any file here → sent to Telegram → deleted
│
├── MYPROJECT/                   ← your new extension
│   ├── clawbridge_plugin.json   ← THE integration file (only required file)
│   ├── bin/
│   │   ├── myscript.sh          ← job script
│   │   └── setup.py             ← venv setup (CLAWBRIDGE-aware)
│   ├── requirements.txt         ← pip deps (CLAWBRIDGE/bin/setup.py picks this up)
│   └── ...
│
└── SMOKETEST/                   ← minimal reference extension (read this)
```

**Rule:** CLAWBRIDGE is detected as a sibling directory. If `../CLAWBRIDGE/` exists,
extensions use its venv and credentials. If not, they run standalone with a local venv.

---

## 3. The Plugin File: `clawbridge_plugin.json`

This is the **only file** CLAWBRIDGE needs from you. Place it in your project root.
It is auto-discovered at CLAWBRIDGE startup — no registration, no symlinks needed.

### 3.1 Full Schema

```json
{
  "plugin": "myproject",
  "description": "One-line description (shown in /help)",

  "commands": {
    "mycommand": {
      "description": "What /mycommand does in Telegram",
      "mode": "job",
      "job": "my_job_name",
      "reply_before": "⚙️ Starting... (sent to user immediately, before job runs)"
    },
    "another": {
      "description": "Python-handled command (no mode = python default)",
    }
  },

  "handler": "myhandler.py",

  "jobs": {
    "my_job_name": {
      "description": "Internal description for logs",
      "command": "mycommand",
      "allowed_actors": ["$USER", "claude", "openclaw"],
      "script": "./bin/myscript.sh",
      "args": ["arg1", "arg2"],
      "feedback": {
        "on_success":     "✅ Done.",
        "on_error":       "❌ Failed.",
        "on_empty_exit":  2,
        "on_empty":       "📭 Nothing to do.",
        "on_locked_exit": 3,
        "on_locked":      "⏳ Already running.",
        "on_output":      false
      }
    }
  }
}
```

### 3.2 Fields Explained

#### Top level

| Field | Required | Description |
|-------|----------|-------------|
| `plugin` | yes | Unique plugin name. Used in /help grouping and logs. |
| `description` | yes | One-liner shown in /help. |
| `commands` | no | Telegram bot commands registered by bot_core.py. |
| `handler` | no | Path to Python handler file, relative to project root. Only needed for `mode: python` commands. |
| `jobs` | no | Jobs that the dispatcher can execute. |

#### `commands[name]` fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | yes | Shown in /help. |
| `mode` | no | `"job"` or `"python"` (default: `"python"`). |
| `job` | if `mode: job` | Job name — must exist in the `jobs` section of any plugin. |
| `reply_before` | no | Text sent to Telegram immediately when command is received, before job executes. |

#### `jobs[name]` fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | yes | Internal label for logs. |
| `command` | no | Telegram command alias (used for bare trigger-file matching). |
| `allowed_actors` | no | List of actor names allowed to run this job. Omit = any actor allowed. |
| `script` | yes | Path to executable. Relative to plugin root (`./bin/...`) or absolute. |
| `args` | no | JSON array of fixed arguments passed to the script. |
| `feedback` | no | Telegram messages keyed by outcome (see below). |

#### `feedback` fields

| Field | Type | Description |
|-------|------|-------------|
| `on_success` | string | Sent when `exit_code == 0`. |
| `on_error` | string | Sent when `exit_code != 0` and no special exit code matches. |
| `on_empty_exit` | int | Exit code that means "nothing to do" (e.g. `2`). |
| `on_empty` | string | Message sent when exit code matches `on_empty_exit`. |
| `on_locked_exit` | int | Exit code that means "already running" (e.g. `3`). |
| `on_locked` | string | Message sent when exit code matches `on_locked_exit`. |
| `on_output` | bool | If `true`, the full stdout/stderr of the script is also sent to Telegram. |

**Exit code priority:** `on_locked_exit` is checked first, then `on_empty_exit`, then 0/non-zero.

---

## 4. TRIGGERDIR — How Files Flow

```
CLAWBRIDGE/TRIGGERDIR/    (or /srv/TRIGGERDIR from clawbridge.conf)
├── $USER/               ← Telegram bot (bot_core.py) drops JSON commands here
├── claude/               ← Claude agent drops trigger files here
├── openclaw/             ← Internal / cron drops trigger files here
└── OUTBOX/               ← DROP any file here → sent to Telegram → deleted
```

### 4.1 Two Trigger Mechanisms

#### Mechanism A: JSON Command Payload

Drop a `.json` file into `TRIGGERDIR/<actor>/`:

```json
{
  "type": "command",
  "job": "my_job_name",
  "id": "abc123",
  "reply_before": ""
}
```

- `type` must be `"command"` — anything else is dropped.
- `job` must exist in the merged job registry.
- `id` is used for logging only (make it unique per call, e.g. a short hash).
- `reply_before` is sent to Telegram before job runs (usually empty when triggering manually).
- The file is deleted by the dispatcher before the job runs.

#### Mechanism B: Bare Trigger File

Drop a file (any extension, even empty) whose **basename** matches a job name or its `command` alias:

```bash
touch "$TRIGGERDIR/claude/my_job_name"
# or
touch "$TRIGGERDIR/claude/mycommand"   # if jobs[...].command == "mycommand"
```

Useful for cron jobs, shell scripts, or Claude dropping a trigger without constructing JSON.

### 4.2 File-based Rules (non-JSON drops)

Defined in `CLAWBRIDGE/dispatcher_filebased_rules.json`:

```json
{
  "file_rules": [
    { "match_ext": [".pdf", ".md", ".txt"], "action": "tg_send_document" }
  ]
}
```

When an actor (`$USER`, `claude`, `openclaw`) drops a non-JSON file whose extension matches
a rule, the dispatcher executes the action (currently only `tg_send_document` is supported).
The file is sent to Telegram and deleted. **This is how PDF reports reach the user.**

### 4.3 OUTBOX — Send Any File to Telegram

Drop any file (PDF, log, image, etc.) into `TRIGGERDIR/OUTBOX/`:

```bash
cp report.pdf "$TRIGGERDIR/OUTBOX/"
```

The dispatcher detects it, sends it via Telegram `sendDocument`, then deletes it.
No JSON needed. Works from any language or shell script.

**Note:** The OUTBOX dir is checked first and does not go through actor/policy logic.

### 4.4 Actor Policy Check

When a JSON command arrives, the dispatcher:

1. Checks `job_exists(job)` — drops file if unknown.
2. Checks `allowed_actors` for the job — if the actor is not listed, the job is **denied**
   (logged to `CLAWBRIDGE/logs/<actor>/..._denied.json`).
3. If no `allowed_actors` field → any actor is allowed.

Currently recognised actor subdirs: `$USER`, `claude`, `openclaw`.
Anything else is silently dropped to `DROP.log`.

---

## 5. Job Execution — Step by Step

When the dispatcher runs a job:

1. Resolves `script` path (relative `./bin/...` → absolute from plugin root).
2. Checks the script is executable (`chmod +x` it!).
3. Reads `args` from the plugin JSON — passed as positional arguments.
4. Runs: `"$script" "${args[@]}" 2>&1`
5. Captures all stdout+stderr as `$output`.
6. Writes a JSON-Lines execution log to `CLAWBRIDGE/logs/<actor>/<timestamp>.json`
   with events: `START`, `OUTPUT` (one per line), `END`.
7. Maps exit code to a status string:
   - `0` → `ok`
   - matches `on_locked_exit` → `locked`
   - matches `on_empty_exit` → `empty`
   - anything else → `error`
8. Sends the appropriate Telegram feedback message.
9. If `on_output: true`, also sends the full script output to Telegram.

**The script runs in its own subshell with no special environment beyond what the
OS provides. Do NOT assume any env vars are set — source what you need explicitly.**

---

## 6. Script Requirements

Your job script must:

- Be executable: `chmod +x bin/myscript.sh`
- Accept positional arguments if `args` is set in the plugin JSON
- Use exit codes consistently:
  - `0` = success
  - `2` = nothing to do (if using `on_empty_exit: 2`)
  - `3` = already running / locked (if using `on_locked_exit: 3`)
  - anything else = error
- Write all output to stdout/stderr (both are captured together)

**Minimal example:**

```bash
#!/bin/bash
set -euo pipefail
LOG="$(dirname "$(realpath "$0")")/../myproject.log"
echo "$(date -Iseconds) OK" >> "$LOG"
echo "Done."
```

---

## 7. CLAWBRIDGE Integration in Shell Scripts

When your script needs CLAWBRIDGE's venv, API keys, or TRIGGERDIR path:

```bash
#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── CLAWBRIDGE integration detection ─────────────────────────────────────────
CLAWBRIDGE_DIR="$(dirname "$BASE_DIR")/CLAWBRIDGE"
if [ -d "$CLAWBRIDGE_DIR" ]; then
    PYTHON="$CLAWBRIDGE_DIR/venv/bin/python"
    # Load API keys / LLM credentials
    if [ -f "$CLAWBRIDGE_DIR/.env" ]; then
        set -a
        source "$CLAWBRIDGE_DIR/.env"
        set +a
    fi
    # Read TRIGGERDIR from clawbridge.conf (fallback to default)
    _tdir=$(grep -E '^[[:space:]]*TRIGGERDIR=' "$CLAWBRIDGE_DIR/clawbridge.conf" 2>/dev/null \
            | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
    TRIGGERDIR="${_tdir:-$CLAWBRIDGE_DIR/TRIGGERDIR}"
else
    # Standalone mode — no CLAWBRIDGE present
    PYTHON="$BASE_DIR/venv/bin/python"
    TRIGGERDIR=""
fi
[ ! -x "$PYTHON" ] && PYTHON="python3"
```

**Delivering a file to Telegram from your script:**

```bash
# Method 1: via OUTBOX (works always, even without a JSON command flow)
[ -n "$TRIGGERDIR" ] && cp myreport.pdf "$TRIGGERDIR/OUTBOX/"

# Method 2: via file-based rule (drop into actor dir, ext must match dispatcher_filebased_rules.json)
[ -n "$TRIGGERDIR" ] && cp myreport.pdf "$TRIGGERDIR/$USER/REPORTS/"
```

---

## 8. Python Handler Mode (bot_core.py)

Use this when a Telegram command needs interactive behaviour: inline keyboards, multi-step
flows, free-text responses. The dispatcher is not involved — bot_core.py handles it directly.

### 8.1 Plugin JSON

```json
{
  "plugin": "myproject",
  "description": "...",
  "handler": "myhandler.py",
  "commands": {
    "mycommand":  { "description": "Primary command" },
    "mysecond":   { "description": "Secondary command" }
  }
}
```

- `handler` is relative to the project root.
- `mode` is omitted (defaults to `python`).

### 8.2 Handler File Interface

```python
# myhandler.py  (in project root, same level as clawbridge_plugin.json)

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def mycommand_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from myproject!")

async def mysecond_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Second command!")

def register(app: Application):
    app.add_handler(CommandHandler("mycommand", mycommand_handler))
    app.add_handler(CommandHandler("mysecond",  mysecond_handler))
    # Also works: CallbackQueryHandler, MessageHandler, etc.
```

`register(app)` is the **only required interface**. bot_core.py calls it after importing
the module.

### 8.3 Free-text Handler (catches all non-command messages)

**Only ONE plugin may register a free-text handler** across the whole ecosystem.
Expose it as `FREE_TEXT_HANDLER` — bot_core.py registers it last, after all other handlers.

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")

FREE_TEXT_HANDLER = handle_message  # bot_core.py picks this up automatically

def register(app: Application):
    pass  # do NOT add the free-text handler here
```

### 8.4 Plugin Loading Details

bot_core.py:
1. Globs `PROJECTS_DIR/*/clawbridge_plugin.json` (sorted alphabetically).
2. Builds `COMMAND_REGISTRY` — exits hard if any command name is duplicated.
3. For each plugin: registers `mode: job` commands as job handlers.
4. If `handler` key is set: imports the `.py` file, calls `register(app)`.
5. Registers the free-text handler last (if any plugin exposed `FREE_TEXT_HANDLER`).

**Credentials available inside handler files** (already loaded by bot_core.py):
- `.botenv` → `BOT_TOKEN`, `CHAT_ID`
- `.env` → LLM API keys
- `.mysqlenv` → DB credentials

Access via `os.getenv("KEY")` — no need to load dotenv yourself.

---

## 9. Setup Pattern (`bin/setup.py`)

Every extension should have a `bin/setup.py` that handles both modes:

```python
#!/usr/bin/env python3
"""
Standalone setup for MYPROJECT.
If CLAWBRIDGE is present as a sibling, installs into its central venv.
Otherwise creates a local venv.
"""
import subprocess, sys
from pathlib import Path

PROJECT_DIR  = Path(__file__).resolve().parent.parent
CENTRAL_VENV = PROJECT_DIR.parent / "CLAWBRIDGE" / "venv"
LOCAL_VENV   = PROJECT_DIR / "venv"

def run(cmd):
    subprocess.run(cmd, check=True)

def main():
    if CENTRAL_VENV.exists():
        venv = CENTRAL_VENV
        print(f"CLAWBRIDGE venv found — installing into central venv: {venv}")
    else:
        venv = LOCAL_VENV
        if not venv.exists():
            print(f"Creating local venv at {venv} ...")
            run([sys.executable, "-m", "venv", str(venv)])
        else:
            print(f"Using existing local venv: {venv}")

    pip = venv / "bin" / "pip"
    run([str(pip), "install", "--upgrade", "pip", "-q"])

    req = PROJECT_DIR / "requirements.txt"
    if req.exists():
        print(f"Installing {req} ...")
        run([str(pip), "install", "-r", str(req)])
    else:
        print("No requirements.txt — nothing to install.")

    print(f"\n  Done. Venv: {venv}")

if __name__ == "__main__":
    main()
```

**CLAWBRIDGE's own `bin/setup.py`** also iterates all `../*/requirements.txt` and installs
them into the central venv — so running it once from CLAWBRIDGE covers everything.

---

## 10. Logging

| File | Content |
|------|---------|
| `CLAWBRIDGE/logs/CLAWBRIDGE.log` | Timestamped human-readable event log (start, ok, error, denied) |
| `CLAWBRIDGE/logs/DROP.log` | Files dropped by the dispatcher (unknown actor, bad payload) |
| `CLAWBRIDGE/logs/<actor>/<timestamp>.json` | Full JSON-Lines execution log per job run |
| `CLAWBRIDGE/logs/<actor>/<timestamp>_denied.json` | Policy denial records |

Per-job log format (JSON-Lines, one object per line):

```jsonl
{"event":"START",  "job":"my_job", "id":"abc123", "actor":"claude", "timestamp":"2026-03-03T10:00:00+00:00"}
{"event":"OUTPUT", "line":"Logged to: /path/to/file", "timestamp":"2026-03-03T10:00:01+00:00"}
{"event":"END",    "job":"my_job", "id":"abc123", "status":"ok", "exit_code":0, "timestamp":"2026-03-03T10:00:01+00:00"}
```

---

## 11. Duplicate Command Names

Command names must be **globally unique** across all plugins.
bot_core.py exits with a hard error if two plugins register the same `/command`.
Job names must be **unique across all `jobs` sections** — the dispatcher logs a warning
and skips duplicates (first one wins).

Before choosing a name: check all existing `clawbridge_plugin.json` files in sibling dirs.

---

## 12. SMOKETEST — The Reference Implementation

SMOKETEST is the minimal extension. Study it to understand the pattern:

**`clawbridge_plugin.json`:**
```json
{
  "plugin": "smoketest",
  "description": "Smoke test — verifies CLAWBRIDGE job dispatch end-to-end",
  "commands": {
    "smoketest": {
      "description": "Append a timestamped line to smoketest.log",
      "mode": "job",
      "job": "smoketest",
      "reply_before": "🔧 Running smoke test..."
    }
  },
  "jobs": {
    "smoketest": {
      "description": "Append timestamp to smoketest.log",
      "allowed_actors": ["TELEGRAM", "CLAUDE", "CRON"],
      "script": "./bin/smoketest.sh"
    }
  }
}
```

**`bin/smoketest.sh`:**
```bash
#!/bin/bash
LOG="$(dirname "$(realpath "$0")")/../smoketest.log"
echo "$(date -Iseconds) smoketest OK" >> "$LOG"
echo "Logged to: $LOG"
```

This tests the complete dispatch chain: Telegram → bot_core.py → TRIGGERDIR → dispatcher →
script → log → Telegram feedback.

---

## 13. Checklist for a New Extension

- [ ] `clawbridge_plugin.json` in project root
- [ ] `plugin` name is unique across all sibling plugins
- [ ] All command names unique (grep `clawbridge_plugin.json` across siblings before naming)
- [ ] All job names unique across all plugins
- [ ] Job script is executable (`chmod +x`)
- [ ] Script uses the correct exit codes (`0`/`2`/`3`) if using `on_empty_exit`/`on_locked_exit`
- [ ] `args` in plugin JSON matches what the script expects as positional arguments
- [ ] `allowed_actors` set correctly (use `["$USER", "claude", "openclaw"]` for typical jobs)
- [ ] If `mode: job`: `job` key matches a name in the `jobs` section
- [ ] If `mode: python`: `handler` key points to `.py` file, file exposes `register(app)`
- [ ] If free-text handler: `FREE_TEXT_HANDLER` exposed, NOT added inside `register(app)`
- [ ] `bin/setup.py` uses the CLAWBRIDGE venv detection pattern
- [ ] `requirements.txt` present if the project has Python deps
- [ ] Credential files (`.botenv`, `.env`) gitignored; `.example` files committed
- [ ] Restart CLAWBRIDGE after adding the plugin (dispatcher rebuilds job registry on start)

---

## 14. What NOT to Do

- **Never edit CLAWBRIDGE files** to register your plugin. Discovery is automatic.
- **Never hardcode** `BOT_TOKEN`, `CHAT_ID`, or API keys in scripts or plugin JSON.
- **Never drop files into `TRIGGERDIR/RESP/`** — that folder is written by the dispatcher only.
- **Never use an actor name not in the dispatcher's allow-list** (`$USER`, `claude`, `openclaw`) — files will be silently dropped to `DROP.log`.
- **Never make a job script block forever** — the dispatcher runs jobs in background subshells; a hung script will hold a subshell open until it's killed.
- **Never put `.md` or other non-PDF files into a REPORTS delivery dir** — TRIGGERDIR/OUTBOX and file-based rules send everything they see; only PDFs belong there.
- **Never suppress output** — write all diagnostic info to stdout/stderr so it appears in the job log and can be sent via `on_output`.
