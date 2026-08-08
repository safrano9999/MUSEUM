# PORTFOLIO OS — Project Portfolio Operating System

A 4-agent OpenClaw team that continuously evaluates, criticizes, and prioritizes a folder of project ideas.

This is not a code generator. This is a **portfolio evaluation and falsification system**.

---

## What It Does

- Detects new and changed project folders
- Evaluates each project for architecture honesty, multi-agent fit, and effort realism
- Researches similar external projects to test novelty claims
- Prioritizes the portfolio and recommends what to build next
- Writes and updates `EVALUATION.md` per project with timestamped assessments

---

## Agent Team

| Agent | Name | Emoji | Role |
|-------|------|-------|------|
| Librarian | Index | 📚 | Portfolio inventory, change detection, structure extraction |
| Critic | Shard | 🪓 | Falsification, architecture honesty, multi-agent fit judgment |
| Curator | Atlas | 🧭 | Prioritization, shortlisting, decision support |
| Researcher | Pulse | 📡 | External scanning: GitHub, Reddit, X, issues, PRs |

---

## How It Works

```
Loop 1 — Detect    → Librarian scans portfolio, detects new/changed/missing
Loop 2 — Evaluate  → Critic assesses architecture, multi-agent fit, effort
Loop 3 — Research  → Researcher checks external reality (GitHub, Reddit, X)
Loop 4 — Curate    → Curator prioritizes and recommends next build
```

Each loop produces structured output. The Curator makes the final call.

---

## Output Per Project

Each project folder eventually receives an `EVALUATION.md` containing:

- Timestamp
- Build Mode (one-off / iterative / permanent-running)
- Agent Fit (single-agent better / multi-agent natural / artificial)
- Effort to MVP
- GitHub-star potential (1–5)
- Monetization potential (1–5)
- Weaknesses and falsification angles
- State/Storage Assessment (markdown-first → SQLite → full DB)
- Recommended next step

---

## Folder Structure

```
project-portfolio/
├── portfolio-os/           ← this system
├── mailmuseum/
├── social-growth-agents/
├── airgapsteward/
├── pv-roof/
└── <your-next-project>/
    ├── README.md
    ├── INSTRUCTIONS.md
    └── EVALUATION.md       ← written by this system
```

---

## Telegram Topics

| Topic | Primary Agent | Purpose |
|-------|--------------|---------|
| Portfolio | Librarian | Inventory updates, change detection, missing files |
| Review | Critic | Architecture critiques, multi-agent honesty checks |
| Decisions | Curator | Shortlists, rankings, build recommendations |
| Research | Researcher | External findings, similar repos, market signals |

---

## Triggers

- New sibling folder appears
- Existing project markdown changes
- Human requests re-evaluation
- Daily or twice-daily portfolio scan
- Project marked as implemented or falsified

---

## Quick Start

1. Install OpenClaw and configure your LLM API key
2. Copy `openclaw.json` snippet into `~/.openclaw/openclaw.json`
3. Create 4 Telegram bots (one per agent) via @BotFather
4. Create a supergroup with 4 topics (Portfolio / Review / Decisions / Research)
5. Fill in tokens, group ID, and topic IDs in `openclaw.json`
6. Restart OpenClaw
7. Message the Librarian in the Portfolio topic: `scan portfolio`

See `INSTRUCTIONS.md` for full setup guide.

---

## Non-Goals

- Mindless idea hoarding
- Pretending every project is equally good
- Forcing multi-agent onto everything
- Building projects automatically
- Generating massive text with no decisions

---

## Success Criteria

The system works when:
- Weak ideas are filtered out consistently
- Promising ideas rise clearly with supporting evidence
- `EVALUATION.md` files improve with each revision cycle
- The human gets useful, opinionated decision support
- The portfolio develops memory and selection pressure
