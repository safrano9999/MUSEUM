# MAILMUSEUM — Mail Archive Intelligence

A 3-agent OpenClaw team that turns a historical email archive into statistics, patterns, and insights.

This is **not** an inbox assistant, email sorter, or triage bot.
The purpose is **archive archaeology** — extracting meaning from a lifetime of email.

---

## What It Does

- Syncs a Google backup account locally via `offlineimap` into Maildir
- Parses email metadata and imports it into MariaDB (no raw bodies in DB)
- Runs SQL-based analysis to surface patterns, contacts, domains, and timelines
- Delivers human-readable reports and insight summaries to Telegram topics
- Uses LLMs only for summarization — never for bulk body ingestion

---

## Agent Team

| Agent | Name | Emoji | Role |
|-------|------|-------|------|
| Orchestrator | Atlas | 🗺️ | Team lead, task delegation, human coordination |
| Archivist | Archive | 🗄️ | offlineimap → Maildir → MariaDB ingestion |
| Analyst | Vector | 📊 | SQL analysis, patterns, insight reports |

---

## Design Principles

**Metadata-first.** Only headers, dates, senders, subjects, and attachment flags go into the DB.
**Local-first.** The archive stays on your machine. Nothing is uploaded to external services.
**Low-token.** LLMs see summaries and samples — never the full 20k+ message corpus.
**Maildir as source of truth.** The DB is derived and reconstructable.

---

## Data Flow

```
Google backup account
        ↓ offlineimap
    Maildir (source of truth)
        ↓ local parser
    MariaDB (derived metadata)
        ↓ SQL / statistics
    Telegram summaries + reports
```

---

## Telegram Topics

| Topic | Primary Agent | Purpose |
|-------|--------------|---------|
| General | Orchestrator | Human requests, progress summaries, phase coordination |
| Ingest | Archivist | Sync status, import runs, data quality issues |
| Insights | Analyst | Statistics, findings, top domains, timeline analysis |

---

## Analysis Roadmap

**Round 1 — Archive shape**
Total emails, folder structure, year range, volume by year/month, top sender domains, attachment ratio

**Round 2 — Contact intelligence**
Top correspondents, contact longevity, domain categories, personal vs service-like senders

**Round 3 — Archive archaeology**
Historical peaks, dormant services, recurring subject themes, life/project phase inference

**Round 4 — Narrative outputs**
Yearly summaries, digital life timeline draft, optional sampled LLM interpretation

---

## First Deliverables

- `archive_ingest_report.md`
- `archive_first_stats.md`
- `top_domains.csv`
- `mail_volume_by_year.csv`
- `mail_volume_by_month.csv`
- `findings_round_1.md`

---

## Prerequisites

- OpenClaw installed and running
- LLM API key configured
- Telegram access (3 bots, 1 supergroup, 3 topics)
- MariaDB running on host
- Google backup account accessible via `offlineimap`

---

## Non-Goals

- Inbox zero
- Active mail triage or auto-replies
- Mass body summarization of the full archive
- Uploading archive to external services
- Replacing Gmail search

---

## Success Criteria

- Archive mirrored locally and importable reliably
- Metadata analysis runs without large token burn
- Human can ask exploratory questions via Telegram
- Reports reveal patterns that Gmail search alone cannot show
- Agents visibly collaborate in their respective Telegram topics
