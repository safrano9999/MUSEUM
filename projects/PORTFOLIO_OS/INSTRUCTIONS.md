# INSTRUCTIONS.md — Portfolio OS Setup Guide

This file is written for the **setup agent** — the AI agent responsible for reading this file, interviewing the human, and spawning the 4-agent Portfolio OS team.

You are not one of the 4 agents. You are the agent that sets them up.

Follow this file top to bottom. Ask all required questions before spawning anything.

---

## Step 0: Pre-Spawn Interview

Before creating any agents, workspaces, or configuration, ask the human the following questions. Ask them one at a time. Wait for each answer before continuing.

**Required questions — do not skip any:**

1. "What is the full path to your portfolio directory?"
   *(e.g. `/home/rafael/safrano9999/PORTFOLIO_OS` — the folder containing all project subfolders)*

2. "Do you already have 4 Telegram bots created for this team, or should I walk you through creating them first?"
   *(If no: guide them through @BotFather before continuing)*

3. "Please send me the 4 bot tokens — one for each agent: Librarian, Critic, Curator, Researcher."

4. "What is your Telegram supergroup ID?"
   *(If not created yet: guide them through creating a supergroup with Topics enabled)*

5. "What are the 4 topic IDs? — Portfolio, Review, Decisions, Research"

6. "What is your Telegram user ID?"
   *(This goes into `groupAllowFrom` so only you can trigger the agents)*

7. "What username are you running OpenClaw as on this machine?"
   *(Used to build the workspace paths, e.g. `/home/USERNAME/.openclaw/...`)*

Once you have all answers, confirm everything back to the human in a short summary before proceeding:

> "I have everything I need. Here's what I'll set up: [summary]. Shall I proceed?"

Only continue after explicit confirmation.

Write all answers into `shared-context/SETUP.md` before spawning agents. This file is read by all 4 sub-agents as shared context.

---

## What You Are Building

A 4-agent OpenClaw team that continuously evaluates a folder of project ideas.

Each project exists in its own sibling directory. The team detects new and changed projects, evaluates their potential, criticizes weak assumptions, researches external reality, and curates a prioritized shortlist.

This is a **portfolio evaluation and falsification system** — not a code generator.

---

## Folder Assumption

```
project-portfolio/
  portfolio-os/
  mailmuseum/
  social-growth-agents/
  airgapsteward/
  pv-roof/
  <any-new-project>/
```

Each project folder may contain: `README.md`, `IDEA.md`, `INSTRUCTIONS.md`, `STATUS.md`, `FEEDBACK.md`, `EVALUATION.md`

Not all files must exist initially. The system works incrementally.

---

## Team Structure

| Role | Agent ID | Name | Emoji | Priority |
|------|----------|------|-------|----------|
| Librarian | librarian | Index | 📚 | Required |
| Critic | critic | Shard | 🪓 | Required |
| Curator | curator | Atlas | 🧭 | Required |
| Researcher | researcher | Pulse | 📡 | Required |

---

## Role Definitions

### Librarian (Index 📚)
- Inventories all project folders
- Detects new folders and changed markdown files
- Extracts structure and metadata from project descriptions
- Tracks whether `EVALUATION.md` exists per project
- Identifies missing core files
- Feeds clean portfolio state to Critic, Curator, and Researcher

### Critic (Shard 🪓)
- Evaluates whether a project is a genuine multi-agent fit or fake
- Distinguishes real feedback loops from simple linear pipelines
- Evaluates one-off vs. recurring vs. permanent-running classification
- Identifies overengineering, privacy risks, weak assumptions
- Proposes markdown improvements and internal TODOs
- Is skeptical and useful — not destructive

### Curator (Atlas 🧭)
- Prioritizes the portfolio and creates shortlists
- Decides what the human should build next
- Balances: novelty, low effort, star potential, monetization, multi-agent fit
- Turns criticism and research into concrete recommendations
- Forces decisions — does not produce endless "maybe" outputs

### Researcher (Pulse 📡)
- Scans GitHub, Reddit, X for similar projects and failure patterns
- Finds relevant repos, issues, PRs, and discussions
- Explains relevance — does not dump raw links
- Strengthens or weakens internal novelty claims with external evidence
- Surfaces missing angles and ideas from the outside world

---

## Phase 1: Create Agent Workspaces

```bash
mkdir -p ~/.openclaw/workspace/agents/librarian/
mkdir -p ~/.openclaw/workspace/agents/critic/
mkdir -p ~/.openclaw/workspace/agents/curator/
mkdir -p ~/.openclaw/workspace/agents/researcher/
mkdir -p ~/.openclaw/workspace/shared-context/
```

Copy shared context files:
- `shared-context/PORTFOLIO-THESIS.md`
- `shared-context/PROJECT-REGISTRY.md`
- `shared-context/SCORING-RUBRIC.md`
- `shared-context/EVALUATION-TEMPLATE.md`

---

## Phase 2: Create Telegram Bots

Create 4 bots via @BotFather:

| Bot Name | Username | Agent |
|----------|----------|-------|
| Index Bot | index_portfolio_bot | librarian |
| Shard Bot | shard_portfolio_bot | critic |
| Atlas Bot | atlas_portfolio_bot | curator |
| Pulse Bot | pulse_portfolio_bot | researcher |

For each bot:
1. `/newbot` → save token
2. `/setjoingroups` → enable
3. `/setprivacy` → disable

---

## Phase 3: Create Supergroup and Topics

Create a Telegram supergroup with Topics enabled.

| Topic Name | Primary Agent | Purpose |
|-----------|--------------|---------|
| Portfolio | Librarian | Inventory, change detection, missing files |
| Review | Critic | Architecture critiques, multi-agent honesty |
| Decisions | Curator | Shortlists, rankings, build recommendations |
| Research | Researcher | External findings, similar repos, signals |

Collect: group ID, all 4 topic IDs, human Telegram user ID.

---

## Phase 4: Configure openclaw.json

Back up first:
```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
```

Use the `openclaw.json` template in this directory. Fill in:
- `LIBRARIAN_BOT_TOKEN`, `CRITIC_BOT_TOKEN`, `CURATOR_BOT_TOKEN`, `RESEARCHER_BOT_TOKEN`
- `GROUP_ID`
- `TOPIC_PORTFOLIO`, `TOPIC_REVIEW`, `TOPIC_DECISIONS`, `TOPIC_RESEARCH`
- `HUMAN_TELEGRAM_USER_ID`
- `USER` (your system username)

---

## Phase 5: Agent Identity Files

Copy `SOUL.md` and `IDENTITY.md` for each agent into their workspace:

```bash
cp agents/librarian/SOUL.md ~/.openclaw/workspace/agents/librarian/SOUL.md
cp agents/librarian/IDENTITY.md ~/.openclaw/workspace/agents/librarian/IDENTITY.md
# repeat for critic, curator, researcher
```

---

## Phase 6: EVALUATION.md Structure

Each project must eventually receive an `EVALUATION.md` with these fields:

1. Timestamp
2. Project summary
3. Build Mode: `one-off` / `iterative` / `permanent-running` / `unclear`
4. Agent Fit: `single-agent better` / `multi-agent natural` / `multi-agent optional` / `multi-agent artificial`
5. Agent Count suggestion
6. Recommended Operating Model
7. Effort to MVP (days / weeks / months)
8. GitHub-star potential (1–5)
9. Monetization potential (1–5)
10. Success likelihood (1–5)
11. Weaknesses and falsification angles
12. State/Storage Assessment (markdown-first → SQLite → full DB)
13. Internal TODOs for improving markdown files
14. Recommended next step

Use `shared-context/EVALUATION-TEMPLATE.md` as the base.

---

## Phase 7: Review Loop

```
Loop 1 — Detect   (Librarian)   → new folders, changed files, missing EVALUATION.md
Loop 2 — Evaluate (Critic)      → architecture honesty, multi-agent fit, effort realism
Loop 3 — Research (Researcher)  → external GitHub/Reddit/X reality check
Loop 4 — Curate   (Curator)     → prioritize, shortlist, recommend next build
```

---

## Phase 8: Trigger Model

Recommended triggers (do not run at full intensity continuously):

- New sibling folder appears
- Existing project markdown changes
- Human requests re-evaluation
- Daily or twice-daily portfolio scan
- Project marked as implemented or falsified

Recommended intake: 1–3 new projects per day (ideal), 3–7 (acceptable), above 7 = backlog only.

---

## Phase 9: Testing Checklist

- [ ] Message in Portfolio topic → Librarian responds
- [ ] Message in Review topic → Critic responds
- [ ] Message in Decisions topic → Curator responds
- [ ] Message in Research topic → Researcher responds
- [ ] Librarian can detect a new test folder
- [ ] Critic evaluates a sample project correctly
- [ ] Curator produces a ranked shortlist
- [ ] Researcher returns relevant external findings with explanations

---

## Failure Modes to Avoid

| Problem | Cause | Fix |
|---------|-------|-----|
| Every idea gets praised | Critic too weak | Strengthen falsification prompts |
| Endless re-reviewing | No state tracking | Maintain timestamps in EVALUATION.md |
| No external reality check | Researcher too passive | Enforce research summaries per project |
| Too many ideas, no decisions | Curator too soft | Force ranked shortlist output |
| Fake multi-agent inflation | Poor architectural honesty | Explicit single-agent evaluation required |
| Portfolio becomes a graveyard | No maturity labels | Require status field in every EVALUATION.md |

---

## Non-Goals

- Mindless idea hoarding
- Pretending all ideas are equally good
- Forcing multi-agent onto every project
- Building selected projects automatically
- Replacing actual implementation work
- Generating massive text without making decisions

---

## Success Criteria

- Every project folder can be evaluated consistently
- New folders are detected and reviewed
- `EVALUATION.md` files improve with each revision
- Weak ideas are filtered out with clear reasoning
- Promising ideas rise with supporting evidence
- The human gets useful, opinionated decision support
- The portfolio develops memory and selection pressure over time
