# PROJECT-THESIS.md — MAILMUSEUM

## Purpose

Turn a large historical email archive into statistics, patterns, contact intelligence, and timeline insights — without uploading it anywhere, without mass LLM body ingestion, and without turning it into an inbox tool.

---

## Core Design Constraints

**Metadata-first.** Only headers, dates, senders, subjects, and attachment flags go into MariaDB. Email bodies stay in Maildir.

**Local-first.** The archive stays on the host machine. No email content is uploaded to external services or APIs.

**Low-token.** LLMs receive summaries and small representative samples. They never process the full 20k–30k message corpus.

**Maildir as source of truth.** The database is derived and fully reconstructable from Maildir at any time.

**Reproducible.** Import runs are idempotent. Re-running the pipeline does not create duplicates.

---

## What This Is For

- Archive archaeology: understanding the history and character of a digital life in email
- Contact intelligence: who were the most consistent correspondents across years?
- Domain intelligence: which services, organizations, and relationships appear in the archive?
- Timeline analysis: when were the high-volume periods? What might explain them?
- Pattern discovery: reply rates, attachment habits, communication shifts over time

---

## What This Is NOT For

- Inbox zero or email triage
- Auto-replies or active mail handling
- Mass LLM summarization of all emails
- Replacing Gmail search
- Uploading the archive to external AI services

---

## Token Budget Philosophy

The LLM is the curator, not the processor.

Acceptable LLM usage:
- Summarizing SQL query results (already reduced to a table)
- Naming observed patterns from statistical output
- Interpreting a small representative sample (e.g. 20–50 emails from a specific period)
- Writing the final narrative report from structured findings

Unacceptable LLM usage:
- Sending raw email bodies for analysis
- Processing more than ~100 emails in a single LLM call
- Using LLMs to extract metadata that can be parsed deterministically

---

## Data Flow

```
Google backup account (IMAP)
    ↓ offlineimap
Maildir (source of truth — never modified)
    ↓ archivist: parser + normalizer
MariaDB — emails, attachments, participants (derived, reconstructable)
    ↓ analyst: SQL + statistics
Aggregated findings (counts, domains, timelines)
    ↓ LLM (small summaries only)
Telegram insight reports + markdown files
```
