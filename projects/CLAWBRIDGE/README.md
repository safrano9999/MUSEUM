# CLAWBRIDGE

Central inotify dispatcher + Telegram bot for the safrano9999 ecosystem.

---

## 📁 TRIGGERDIR — Directory Structure & Permissions

### Overview

TRIGGERDIR is the central drop zone that CLAWBRIDGE watches via `inotify`.
Any actor (a user, a script, a Claude agent, a cron job) drops a file into their
actor subdirectory and the dispatcher picks it up, runs the matching job, and sends
Telegram feedback.

```
TRIGGERDIR/
├── rafael/       ← actor: Telegram bot (bot_core.py drops JSON commands here)
├── claude/       ← actor: Claude agent drops trigger files here
├── openclaw/     ← actor: internal / cron jobs
└── OUTBOX/       ← drop any file here → sent to Telegram → deleted
```

---

### 👥 The Group Permission Pattern

The dispatcher service runs as a specific OS user (e.g. `rafael`).
Actor subdirectories may be owned by a different user (e.g. `claude`).

For the dispatcher to work correctly on an actor subdirectory it needs to:

| Action | Why |
|--------|-----|
| 📂 Enter the directory | To access files inside |
| 👁️ Watch via inotify | To detect new files instantly |
| 📄 Read the trigger file | To parse job name / JSON payload |
| 🗑️ Delete the trigger file | To clean up after the job runs |

Deleting a file requires **write permission on the directory**, not on the file itself.
This is a common Unix gotcha — `rm` modifies the directory, not the file.

---

### ✅ Correct Setup

**Step 1 — Create a shared group** that includes both the directory owner and the
dispatcher service user:

```bash
# Create the group (if it doesn't exist yet)
groupadd CLAWBRIDGE

# Add both users to it
usermod -aG CLAWBRIDGE rafael   # dispatcher service user
usermod -aG CLAWBRIDGE claude   # actor that writes trigger files
```

> 💡 After `usermod`, the users need to log out and back in (or start a new shell)
> for the group membership to take effect.

**Step 2 — Set ownership and permissions on the actor subdirectory:**

```bash
# Owner = the actor user, Group = shared group
chown claude:CLAWBRIDGE /srv/TRIGGERDIR/claude/

# 775 = owner rwx, group rwx, others r-x
chmod 775 /srv/TRIGGERDIR/claude/
```

Why `775` and not `770`?
- `rwx` for owner (`claude`) → can create trigger files
- `rwx` for group (`CLAWBRIDGE`) → dispatcher (`rafael`) can enter, watch, read, and **delete**
- `r-x` for others → harmless read access; use `770` if you want stricter isolation

**Step 3 — Verify:**

```bash
ls -la /srv/TRIGGERDIR/
```

Expected output:
```
drwxrwxrwx  5 rafael openclaw  4096 ... .
drwxr-xr-x  2 claude CLAWBRIDGE 4096 ... claude/
drwxr-xr-x  2 rafael rafael    4096 ... rafael/
drwxr-xr-x  2 openclaw openclaw 4096 ... openclaw/
drwxrwxrwx  2 rafael rafael    4096 ... OUTBOX/
```

---

### 🔍 How to Debug Permission Issues

**Symptom:** Dispatcher picks up the file, runs the job, but then logs:
```
rm: cannot remove '/srv/TRIGGERDIR/claude/calendar': Permission denied
```

**Cause:** The dispatcher user is not in the group with write access to the directory,
or the directory is missing the group write bit.

**Check current permissions:**
```bash
ls -la /srv/TRIGGERDIR/
getfacl /srv/TRIGGERDIR/claude/
```

**Check group membership:**
```bash
groups rafael
groups claude
```

**Fix:**
```bash
chown claude:CLAWBRIDGE /srv/TRIGGERDIR/claude/
chmod 775 /srv/TRIGGERDIR/claude/
```

---

### ⚡ How inotify Watching Works

The dispatcher sets up a **recursive** inotify watch on the entire TRIGGERDIR at startup:

```bash
inotifywait -m -r -e close_write,moved_to --format '%w%f' "$TRIGGERDIR" | \
while IFS= read -r filepath; do
    process_file "$filepath" &
done
```

- `-m` — monitor mode (runs forever, doesn't exit after first event)
- `-r` — recursive (watches all subdirectories)
- `-e close_write,moved_to` — triggers on completed writes and on files moved in
- `process_file ... &` — each file is processed in a background subshell (non-blocking)

> ⚠️ If the dispatcher user cannot enter a subdirectory at startup (missing `x` bit),
> inotify **will not watch that subdirectory** — events will be silently missed.
> Always verify permissions before starting the service.

---

### 📝 Trigger File Mechanisms

#### Mechanism A — Bare trigger file

Drop an empty file whose name matches a job name or its `command` alias:

```bash
touch /srv/TRIGGERDIR/claude/calendar
# or via script:
touch "$TRIGGERDIR/claude/myjobalias"
```

The dispatcher matches the basename against the job registry and runs the job.

#### Mechanism B — JSON command payload

Drop a `.json` file for more control:

```json
{
  "type": "command",
  "job": "calendar",
  "id": "abc123",
  "reply_before": ""
}
```

The file is parsed, the job is looked up, actor policy is checked, then the job runs.
The file is deleted before the job starts.

#### Mechanism C — OUTBOX (send any file to Telegram)

Drop any file into `TRIGGERDIR/OUTBOX/`:

```bash
cp report.pdf /srv/TRIGGERDIR/OUTBOX/
```

The dispatcher sends it via Telegram `sendDocument` and deletes it. No job needed.

---

### 🔐 Actor Policy

Each job in `clawbridge_plugin.json` can restrict which actors may trigger it:

```json
"allowed_actors": ["rafael", "claude", "openclaw"]
```

If the actor subdirectory name is not in the list → job is **denied** and logged to
`logs/<actor>/<timestamp>_denied.json`. Omitting `allowed_actors` allows any actor.
