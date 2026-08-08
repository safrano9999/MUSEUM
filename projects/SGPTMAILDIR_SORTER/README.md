# ZeroInbox 2026 – SGPT Maildir Sorter 📬

This project implements a deterministic, local ZeroInbox workflow: email is classified from Maildir, moved into explicit target folders, logged, and summarized into a PDF report. The result is a reproducible pipeline that minimizes manual inbox review.

---

## Scope and Guarantees
- **Local-first** processing (Maildir on disk)
- **Explainable rules** (JSON-based)
- **Audit trail** (structured logs + PDF report)
- **Correction feedback loop** for systematic error reduction

---

## Prerequisites (LLM/SGPT Configuration) for bare metal
You must provide:
- A working `sgpt` installation with an updated `litellm`
- A project-local sgpt config: copy `sgpt_config.yaml_example` to `sgpt_config.yaml`, insert your API keys (e.g., `OPENAI_API_KEY`, `XAI_API_KEY`, etc.), and set `DEFAULT_MODEL` to your preferred provider (e.g., `xai/grok-4-1-fast-reasoning` or `openai/gpt-4o-mini`). To switch models, simply change the `DEFAULT_MODEL` line.

---

## Required Setup Order (Do Not Reorder)
1) **Configure `offlineimaprc`**
   - File: `offlineimaprc`
   - Template: `offlineimaprc_example`
   - Insert your Gmail accounts and app passwords (example, works of course also with icloud.com etc)

2) **Run an initial sync**
   ```bash
   bin/mail_sync.sh gmail
   ```

3) **Generate the mirror JSON**
   ```bash
   bin/mirror.sh Mail/gmail
   ```

4) **Assign folder flags in `mirror_dir_*.json`**
   Each folder can be tagged with three boolean roles:
   - `is_source` → scanned by the sorter
   - `is_destination` → allowed target
   - `is_fallback` → uncertain destination

5) **Run the sorter**
   ```bash
   bin/email_sort.sh gmail
   ```
   (Optional: disable PDF) 
   ```bash
   bin/email_sort.sh --pdf=false gmail
   ```

---

## Correction Loop (False Positives)
When a message is misclassified:
1) Move it into `sort_ai_correction`
2) The sorter excludes all previous destinations for that file
3) The corrected result is appended to `corrections.jsonl`

Over time, you can feed `corrections.jsonl` to a model and request **rule/keyword optimization**.

---

## Cron Job Note
If you run scheduled syncs (e.g., `mail_routine.sh`):
- A lockfile prevents overlapping runs
- Logs and PDFs are generated automatically
- PDFs are written to `ZEROINBOX/`
- OpenClaw delivers the PDF report, eliminating manual inbox inspection

---

## Docker (Alpine, No Chroot Required)
Build and run everything inside a minimal Alpine container. PDFs are written to the bind-mounted `ZEROINBOX/` directory.

### Build
```bash
docker build -t sgptmaildir .
```

### Run (Docker Compose)
```bash
docker compose up --build
```

### Required Bind Mounts
The compose file binds:
- `maildata` → `/app/Mail` (Maildir)
- `logsdata` → `/app/LOGS` (logs)
- `./ZEROINBOX` → `/app/ZEROINBOX` (PDF reports)
- `./offlineimaprc` (config)
- `./rules/rules_custom.json` (private rules)
- `./mirror_dir_gmail.json` (folder map)

Ensure `sgpt_config.yaml` is present (project-local) and contains your keys.

---

## Project Structure (Minimal)
```
SGPTMAILDIR_SORTER/
├─ bin/
│  ├─ email_sort.sh
│  ├─ mail_sync.sh
│  ├─ mirror.sh
├─ Mail/                # Maildir root
├─ LOGS/                # Logs
├─ ZEROINBOX/           # PDF reports
├─ rules/
│  ├─ rules_generic.json
│  ├─ rules_custom.json (ignored)
├─ mirror_dir_gmail.json_example
├─ offlineimaprc_example
```

---

## ML-Oriented Rule Refinement (Optional)
Workflow:
1) Accumulate corrections in `corrections.jsonl`
2) Ask a model to propose keyword/rule adjustments
3) Apply changes to the JSON rules

---

## Summary
- **ZeroInbox without UI fatigue**
- **PDF-first reporting**
- **Rules + corrections → continuous improvement**
