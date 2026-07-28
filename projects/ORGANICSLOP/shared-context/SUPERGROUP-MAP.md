# SUPERGROUP-MAP.md — Telegram Team Map

Fill in during setup. Used for topic routing and agent coordination.

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

## Agents

| Agent | Display Name | Bot Username | Primary Topic | Emoji |
|-------|-------------|-------------|--------------|-------|
| scout | Pulse | FILL_ME | Signals | 📡 |
| strategist | Forge | FILL_ME | Strategy | 🧠 |
| writer | Echo | FILL_ME | Drafts | ✍️ |

---

## Topics

| Topic | Topic ID | Primary Agent | Purpose |
|-------|----------|--------------|---------|
| Signals | FILL_ME | scout | Trend scans, examples, risk assessments |
| Strategy | FILL_ME | strategist | Topic selection, angle, format decisions |
| Drafts | FILL_ME | writer | Posts, hooks, threads, replies, follow-ups |

---

## Routing Rules

- Each bot is primary in its own topic (`requireMention: false`)
- In all other topics, bots require explicit mention (`requireMention: true`)
- Agent-to-agent coordination uses `sessions_send` internally
- Human-visible output goes to Telegram topics

---

## Status Checklist

- [ ] Supergroup created with Topics enabled
- [ ] 3 bots created via @BotFather
- [ ] All bots added as supergroup admins
- [ ] Group ID collected
- [ ] Topic IDs collected (Signals / Strategy / Drafts)
- [ ] Bot tokens filled in openclaw.json
- [ ] Human user ID filled in openclaw.json
- [ ] ACCOUNT-THESIS.md filled in
- [ ] Routing validated (each bot responds in correct topic only)
