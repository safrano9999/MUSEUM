# INSTRUCTIONS.md — Social Growth Agents Setup Guide

This file is written for the **setup agent** — the AI agent responsible for reading this file, interviewing the human, and spawning the 3-agent Social Growth team.

You are not one of the 3 agents. You are the agent that sets them up.

Follow this file top to bottom. Ask all required questions before spawning anything.

---

## Step 0: Pre-Spawn Interview

Before creating any agents, workspaces, or configuration, ask the human the following questions. Ask them one at a time. Wait for each answer before continuing.

**Required questions — do not skip any:**

1. "Which platform is the primary target for this account?"
   *(e.g. X/Twitter, LinkedIn, Instagram, Bluesky — one primary, one secondary optional)*

2. "What is the account handle or URL?"
   *(Used to anchor the account thesis in SETUP.md)*

3. "Give me a quick account thesis — niche, target audience, voice tone."
   *(2–4 sentences. This becomes the seed for ACCOUNT-THESIS.md)*

4. "Do you already have 3 Telegram bots created for this team, or should I walk you through creating them first?"
   *(If no: guide them through @BotFather before continuing)*

5. "Please send me the 3 bot tokens — one for each agent: Scout (Pulse), Strategist (Forge), Writer (Echo)."

6. "What is your Telegram supergroup ID?"
   *(If not created yet: guide them through creating a supergroup with Topics enabled)*

7. "What are the 3 topic IDs? — Signals, Strategy, Drafts"

8. "What is your Telegram user ID?"
   *(This goes into `groupAllowFrom` so only you can trigger the agents)*

9. "What username are you running OpenClaw as on this machine?"
   *(Used to build the workspace paths, e.g. `/home/USERNAME/.openclaw/...`)*

Once you have all answers, confirm everything back to the human in a short summary before proceeding:

> "I have everything I need. Here's what I'll set up: [summary]. Shall I proceed?"

Only continue after explicit confirmation.

Write all answers into `shared-context/SETUP.md` before spawning agents. This file is read by all 3 agents as shared context.

---

## What You Are Building

A 3-agent OpenClaw team for growing a social media account through:

- Trend scouting and signal detection
- Angle selection and content positioning
- Platform-native content creation
- Iterative learning from signal quality

This is **not** a posting bot. The purpose is to develop an account that becomes more valuable over time through clear niche positioning, recognizable voice, and repeatable content formats.

---

## Core Design Principle

The account must not become a generic engagement machine.

Optimize for:
- Durable niche identity over noise
- Follower quality over empty vanity metrics
- Repeatable content formats over random one-offs
- Learning loops over isolated posts
- Coherent voice over trend mimicry

---

## Team Structure

| Role | Agent ID | Name | Emoji | Priority |
|------|----------|------|-------|----------|
| Scout | scout | Pulse | 📡 | Required |
| Strategist | strategist | Forge | 🧠 | Required |
| Writer | writer | Echo | ✍️ | Required |

---

## Role Definitions

### Scout (Pulse 📡)
- Monitors platform trends, niche conversations, fast-moving arguments
- Collects examples, narratives, hooks, and audience reactions
- Distinguishes short-lived noise from niche-relevant opportunities
- Does not decide final account direction — provides signal only

### Strategist (Forge 🧠)
- Decides what the account should engage with
- Rejects trends that damage positioning
- Chooses angle, tone, and content format
- Decides whether a signal becomes one post, a thread, a reply campaign, or a series
- Gives the Writer a clear brief with: topic, angle, tone, format, what to avoid

### Writer (Echo ✍️)
- Writes posts, threads, hooks, reply ideas, and follow-up content
- Produces multiple variants when useful
- Adapts format to platform norms
- Preserves the intended voice and framing
- Does not blindly optimize for sensationalism

---

## Phase 1: Define the Account Thesis (Required First)

Before building the team, establish and write `ACCOUNT-THESIS.md`:

- Platform (primary and secondary)
- Niche (primary and adjacent)
- Intended audience (attract and avoid)
- Voice description and tone notes
- Content principles (prefer and avoid)
- Definition of good vs. bad engagement
- Growth goal
- Success signals

**Do not skip this step.** Without a defined thesis, the Strategist cannot function.

---

## Phase 2: Create Agent Workspaces

```bash
mkdir -p ~/.openclaw/workspace/agents/scout/
mkdir -p ~/.openclaw/workspace/agents/strategist/
mkdir -p ~/.openclaw/workspace/agents/writer/
mkdir -p ~/.openclaw/workspace/shared-context/
```

Copy shared context files:
- `shared-context/ACCOUNT-THESIS.md` (filled in)
- `shared-context/SIGNAL-LOG.md`
- `shared-context/FORMAT-LIBRARY.md`
- `shared-context/SUPERGROUP-MAP.md`

---

## Phase 3: Telegram Bots

Create 3 bots via @BotFather:

| Bot Name | Agent |
|----------|-------|
| Pulse Bot | scout |
| Forge Bot | strategist |
| Echo Bot | writer |

For each: `/newbot` → token, `/setjoingroups` → enable, `/setprivacy` → disable.

---

## Phase 4: Supergroup and Topics

Create a Telegram supergroup with Topics enabled.

| Topic | Primary Agent | Purpose |
|-------|--------------|---------|
| Signals | Scout | Trend scans, examples, risk notes, momentum |
| Strategy | Strategist | Topic selection, angle, format, rejection rationale |
| Drafts | Writer | Posts, hooks, threads, replies, follow-ups |

Collect: group ID, all 3 topic IDs, human Telegram user ID.

---

## Phase 5: Agent Identity Files

```bash
cp agents/scout/SOUL.md ~/.openclaw/workspace/agents/scout/SOUL.md
cp agents/scout/IDENTITY.md ~/.openclaw/workspace/agents/scout/IDENTITY.md
# repeat for strategist, writer
```

---

## Phase 6: Handoff Standard

Use `sessions_send` for agent-to-agent coordination.

**Scout → Strategist example:**
```
from: scout
to: strategist
task_id: signal_batch_001
priority: high
summary: New niche-relevant signals for review
done_when:
- 3–5 signals reviewed
- selected or rejected with rationale
- suggested content angle defined
```

**Strategist → Writer example:**
```
from: strategist
to: writer
task_id: draft_set_001
priority: high
summary: Draft content based on selected trend angle
context: [angle, tone, format, what to avoid]
done_when:
- 3 hook variants created
- 1 primary post or thread drafted
- 2 follow-up or reply ideas proposed
```

---

## Phase 7: Daily Growth Loop

```
Step 1 — Scout     → signals, examples, momentum, risk notes
Step 2 — Strategist → topic selection, angle, format, rejection rationale
Step 3 — Writer     → hooks, post drafts, threads, reply ideas
Step 4 — Feedback   → update SIGNAL-LOG.md and FORMAT-LIBRARY.md
```

The team learns from each cycle. Track what works and update shared context files.

---

## Phase 8: Recommended Metrics

Track more than likes:

- Follower growth (quality vs. volume)
- Reply quality and relevance
- Repost / share rate
- Saves and bookmarks (where available)
- Impressions-to-follow ratio
- Repeat engagement from the right audience
- Series continuation success
- Topic hit rate

The Strategist should care about what builds the account, not just what spikes.

---

## Phase 9: Testing Checklist

- [ ] Message in Signals → Scout responds
- [ ] Message in Strategy → Strategist responds
- [ ] Message in Drafts → Writer responds
- [ ] Scout sends signal batch to Strategist
- [ ] Strategist produces a clear brief for Writer
- [ ] Writer produces at least 3 hook variants
- [ ] Feedback cycle updates SIGNAL-LOG.md

---

## Failure Modes to Avoid

| Problem | Cause | Fix |
|---------|-------|-----|
| Trend spam | Scout dominates strategy | Give Strategist stronger veto |
| Random voice | Writer drafts without thesis | Enforce account thesis |
| Generic posts | Weak angle selection | Force Strategist to define stronger framing |
| Content slop | Too much volume, low editing | Reduce output, improve quality |
| No learning loop | Nobody tracks what worked | Maintain signal and format logs |

---

## Non-Goals

- Spam automation
- Fake engagement or botnet behavior
- Generic content spraying without identity
- Manipulative platform abuse
- Destroying account coherence for short-term numbers

---

## Success Criteria

- Account develops a clear, recognizable niche identity
- Team spots useful trends early, before saturation
- Content feels coherent and platform-native
- Strategy improves from cycle to cycle
- Account attracts the intended audience
- The content system becomes more effective over time
