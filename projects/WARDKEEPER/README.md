# WARDKEEPER — Local Project Stewardship System

A 5-agent OpenClaw system for keeping projects alive in awareness through structured daily routines.

Everything is **Markdown-based** and **local-only**. No project vision, core ideas, or sensitive information leaves your environment.

---

## What It Does

- Runs a structured daily project reflection routine (ROUTINE.md)
- Maintains a `CORE.md` file per project (goals, milestones, tasks, next steps)
- Injects fresh ideas via a timestamped inspiration file
- Challenges assumptions on request via a Critic agent
- Tracks concrete next steps and outcomes via an Operator agent
- Maintains present-tense belief reinforcement via a Belief Agent

---

## Agent Team

| Agent | Name | Emoji | Role |
|-------|------|-------|------|
| Steward | Steward | 🧭 | Daily routine, CORE.md maintenance, session lead |
| Inspirator | Inspirator | 💡 | Cross-project idea generation, inspiration injection |
| Critic | Critic | 🪓 | Optional: challenges assumptions, questions direction |
| Operator | Operator | ⚙️ | Task tracking, .ics events, outcome recording |
| Belief Agent | BeliefAgent | 🌱 | beliefs.md maintenance, mental alignment support |

---

## Core Principles

**Air-gapped.** Nothing leaves the local environment. No external API calls from agents by design.
**Markdown-first.** All state lives in plain text files. No database needed.
**Routine-driven.** The same structured questions, every session, for every project.
**Concise by constraint.** Goals: max 3 sentences. Milestones: max 3 sentences. Tasks: bullets only.

---

## Workspace Structure

```
wardkeeper/
├── ROUTINE.md              ← Steward operating script
├── INSTRUCTIONS.md
├── agents/                 ← Agent SOUL.md + IDENTITY.md
├── templates/              ← CORE.md + beliefs.md templates
└── ROUTINES/               ← One folder per project
    ├── .template/          ← Copy this to start a new project
    ├── my-project/
    │   ├── CORE.md
    │   └── beliefs.md
    └── another-project/
        ├── CORE.md
        └── beliefs.md
```

---

## CORE.md Structure (per project)

Every project folder contains one `CORE.md` with these sections:

- **Goals** — S.M.A.R.T goals, max 3 sentences
- **Milestones** — steps toward goals, max 3 sentences each
- **Tasks** — short bullet points derived from milestones
- **Next Steps** — immediate micro steps only
- **Available Resources** — what is at hand right now
- **Vibe and Visualization** — feel of the finished project, max 3 sentences
- **AI Support** — how local AI can help, air-gapped preferred
- **Vision Image** — optional path to image file
- **Vision Video** — optional path to video file

---

## Daily Routine Flow

```
1. Greeting
2. Check inspiration inbox (ideas-YYYY-MM-DD.md if present)
3. Scan ROUTINES/ for all project folders
4. For each project: open CORE.md → ask standard questions → update CORE.md
5. End routine
```

---

## Starting a New Project

```bash
cp -r ROUTINES/.template ROUTINES/my-new-project
# Then open Steward and start the routine
```

---

## Non-Goals

- Cloud sync or external data upload
- Heavy database or SQL
- Real-time monitoring
- Replacing project management tools for teams
- Automatic code generation

---

## Success Criteria

- Every active project gets reviewed in each routine session
- CORE.md files stay concise and current
- The human maintains clear awareness of all projects
- Small steps accumulate into real progress
- Projects don't disappear into forgotten folders
