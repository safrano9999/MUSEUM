# SUPERGROUP-MAP.md — Telegram Routing Map

Fill in during setup. Used by the Archivist for topic routing.

---

## Supergroup

| Field | Value |
|-------|-------|
| Group name | FILL_ME |
| Group ID | FILL_ME |

## Human Access

| Field | Value |
|-------|-------|
| Human Telegram user ID | FILL_ME |

---

## Agent

| Agent | Display Name | Bot Username | Primary Topic |
|-------|-------------|-------------|--------------|
| archivist | Archive | FILL_ME | Archive |

---

## Topic

| Topic Name | Topic ID | Purpose |
|-----------|----------|---------|
| Archive | FILL_ME | Stats queries, ingestion status, archive exploration, findings |

---

## Routing Rules

- Archive Bot is the only agent. No `requireMention` logic needed.
- All messages in the Archive topic go to the Archivist.
- No agent-to-agent coordination — single agent setup.

---

## Status Checklist

- [ ] Supergroup created with Topics enabled
- [ ] 1 bot created via @BotFather
- [ ] Bot added as supergroup admin
- [ ] Group ID collected
- [ ] Topic ID collected (Archive)
- [ ] Bot token filled in openclaw.json
- [ ] Human user ID filled in openclaw.json
- [ ] Archivist responds correctly to a test question
