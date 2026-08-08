# INSTRUCTIONS.md — MAILMUSEUM Setup Guide

This file is written for the **setup agent** — the AI agent responsible for reading this file, interviewing the human, and configuring the MAILMUSEUM system.

MAILMUSEUM is not a multi-agent system. It is a **metadata pipeline** with a single specialized agent as the query interface.

Follow this file top to bottom. Ask all required questions before creating any configuration.

---

## Step 0: Pre-Spawn Interview

Before creating any workspace or configuration, ask the human the following questions. Ask them one at a time. Wait for each answer before continuing.

**Required questions — do not skip any:**

1. "What is the full path to your local Maildir directory?"
   *(e.g. `/home/rafael/maildir/mailmuseum/` — where offlineimap will sync to)*

2. "What are your IMAP server and credentials for offlineimap?"
   *(host, username, password — stays local in SETUP.md, used only for offlineimap config)*

3. "What are your MariaDB connection details?"
   *(host, database name, username, password — stored locally in SETUP.md)*

4. "Do you already have a Telegram bot created for the Archivist, or should I walk you through creating one first?"
   *(If no: guide them through @BotFather before continuing)*

5. "Please send me the bot token for the Archivist (Archive Bot)."

6. "What is your Telegram supergroup ID?"
   *(A supergroup with one topic called "Archive" — guide them through creation if needed)*

7. "What is the topic ID for the Archive topic?"

8. "What is your Telegram user ID?"
   *(This goes into `groupAllowFrom` so only you can trigger the agent)*

9. "What username are you running OpenClaw as on this machine?"
   *(Used to build the workspace paths, e.g. `/home/USERNAME/.openclaw/...`)*

Once you have all answers, confirm everything back to the human in a short summary before proceeding:

> "I have everything I need. Here's what I'll set up: [summary]. Shall I proceed?"

Only continue after explicit confirmation.

Write all answers into `shared-context/SETUP.md` before proceeding.

---

## What You Are Building

A **metadata pipeline** for historical email archive intelligence, with one agent as the human-facing query interface.

```
offlineimap → Maildir → Python ingest script → MariaDB
                                                   ↑
                                              Archivist (OpenClaw agent)
                                              answers stats questions via Telegram
```

**Core constraint:** Do not send email bodies through an LLM. Follow the metadata-first pipeline.

---

## Core Design Principle: Metadata-First

```
1. Sync archive locally → Maildir
2. Parse metadata locally (headers, dates, senders, subjects, attachments)
3. Store derived metadata in MariaDB
4. Run statistical analysis with SQL
5. Use the Archivist agent only for: answering questions, summarizing findings, exploring patterns
```

The agent is the **query interface** — not the ingest engine. Ingestion is done by Python scripts.

---

## The Single Agent: Archivist (Archive 🗄️)

One agent. One topic. One purpose: make the archive answerable.

| Field | Value |
|-------|-------|
| Agent ID | archivist |
| Display Name | Archive |
| Emoji | 🗄️ |
| Primary Topic | Archive |
| Role | Stats queries, Maildir navigation, archive archaeology |

---

## Prerequisites

Before setup, confirm:
- [ ] OpenClaw installed and running
- [ ] LLM API key configured
- [ ] Telegram access
- [ ] MariaDB running on host
- [ ] `offlineimap` installed (system binary, not pip)
- [ ] Local Maildir path decided

---

## Phase 1: Create Agent Workspace

```bash
mkdir -p ~/.openclaw/workspace/agents/archivist/
mkdir -p ~/.openclaw/workspace/shared-context/
```

Copy shared context files into `~/.openclaw/workspace/shared-context/`:
- `shared-context/SETUP.md`
- `shared-context/PROJECT-THESIS.md`
- `shared-context/MAIL-ARCHIVE-MAP.md`
- `shared-context/FINDINGS-LOG.md`

---

## Phase 2: Database Setup

```sql
CREATE DATABASE mailmuseum CHARACTER SET utf8mb4;
```

Apply schema:
```bash
mysql -u <user> -p mailmuseum < db/schema.sql
```

Key tables: `emails`, `attachments`, `participants`, `import_batches`

---

## Phase 3: offlineimap Configuration

Configure offlineimap to sync the Google backup account to local Maildir.

The human must provide:
- IMAP server and credentials
- Local Maildir root path (from SETUP.md)

The Maildir is the **source of truth**. The DB is derived and reconstructable.

---

## Phase 4: Run Ingest Script

```bash
python3 pipeline/ingest.py --maildir /path/to/maildir --db-url mysql://user:pass@localhost/mailmuseum
```

The ingest script is a standalone Python script — not an agent task. Run it once to populate the DB.

Re-running is safe: it only imports new records (idempotent via `message_id` UNIQUE constraint).

---

## Phase 5: Agent Identity Files

```bash
cp agents/archivist/SOUL.md ~/.openclaw/workspace/agents/archivist/SOUL.md
cp agents/archivist/IDENTITY.md ~/.openclaw/workspace/agents/archivist/IDENTITY.md
```

---

## Phase 6: Configure openclaw.json

Back up first:
```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
```

Fill in from `shared-context/SETUP.md`:
- `ARCHIVIST_BOT_TOKEN`
- `GROUP_ID`
- `TOPIC_ARCHIVE`
- `HUMAN_TELEGRAM_USER_ID`
- `USER` (your system username)

The Archivist is the only agent. No `requireMention` needed — it owns its topic exclusively.

---

## Phase 7: Testing

- [ ] Message in Archive topic → Archivist responds
- [ ] Ask: "How many emails are in the archive?" → Archivist queries DB and answers
- [ ] Ask: "What are the top 10 sender domains?" → Archivist runs SQL and summarizes
- [ ] Ask: "Find emails from domain X between 2018 and 2020" → Archivist queries and reports

---

## Phase 8: First Analysis Roadmap

Start in this order — do not attempt all at once:

**Round 1 — Archive shape**
Total emails, year range, volume by year/month, top sender domains, attachment ratio

**Round 2 — Contact intelligence**
Top correspondents, contact longevity, domain categories, service vs personal senders

**Round 3 — Archive archaeology**
Historical peaks, dormant services, subject themes, candidate years for deeper review

**Round 4 — Optional narrative**
Yearly summaries, digital life timeline, sampled LLM interpretation

---

## Failure Modes to Avoid

| Problem | Cause | Fix |
|---------|-------|-----|
| Agent tries to ingest emails | Role confusion | Ingestion is Python scripts only |
| LLM reads all email bodies | Architecture drift | Only metadata in DB — no body text |
| Token cost spikes | Too much LLM on raw data | Restrict to summaries and SQL results |
| Duplicate records on re-run | Missing idempotency | Check `message_id` UNIQUE constraint |

---

## Non-Goals

- Multi-agent coordination
- Inbox zero or active triage
- Auto-replies
- Mass body summarization
- Uploading archive to external services

---

## Success Criteria

- Archive mirrored locally into Maildir
- Metadata imported reliably into MariaDB
- Archivist can answer exploratory questions via Telegram
- Reports reveal patterns that Gmail search alone cannot show
