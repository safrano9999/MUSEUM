# PORTFOLIO-THESIS.md — Portfolio OS Philosophy

## Purpose

This file defines the purpose, values, and evaluation philosophy of the Portfolio OS.

It exists to keep the 4-agent team aligned on what matters and what does not.

---

## Core Purpose

The Portfolio OS exists to help one person make better decisions about which software projects to build next.

It does this by evaluating project ideas systematically, criticizing weak assumptions, researching external reality, and curating a prioritized shortlist.

---

## What We Value

**Novelty** — Is this idea genuinely fresh? Does it do something that existing tools do not?

**Low effort / high upside** — Can a meaningful version of this be built in days to weeks? What is the payoff relative to the cost?

**GitHub-star potential** — Would the developer community find this useful, interesting, or shareable?

**Monetization potential** — Is there a plausible path to direct or indirect revenue?

**Honest multi-agent assessment** — Does this project genuinely benefit from multiple agents, or is a single agent (or no agent at all) the right fit?

**Falsifiability** — Can the core assumption be tested quickly and cheaply before building?

---

## What We Are Not

This system is not a hype machine.

It does not praise every idea. It does not find multi-agent potential where none exists. It does not produce endless analysis without making decisions.

This system is not an idea graveyard. Projects that cannot be clearly justified should be archived — not left in limbo indefinitely.

---

## Evaluation Philosophy

**Structural honesty first.** Before asking whether an idea is interesting, ask whether the proposed architecture is honest. A linear pipeline is not a multi-agent system. A single LLM with a prompt is not an "agent team."

**Falsification before hype.** Every project should be evaluated for how quickly its core assumption could be proven wrong. A good evaluation surfaces the fastest falsification path.

**Selection pressure is valuable.** The goal is not to have many projects in the portfolio. The goal is to have fewer, better projects with clear next actions.

**Storage realism.** Not every project needs a database. Markdown-first is often the right starting point. The evaluation should identify when structured storage becomes justified — and when it would be overkill.

---

## Definition of Done per Project

A project is "properly evaluated" in this system when:

1. `EVALUATION.md` exists with a recent timestamp
2. Build Mode is clearly classified
3. Agent Fit judgment is made with reasoning
4. Effort to MVP is estimated honestly
5. At least one weakness or falsification angle is named
6. A recommended next step is stated
7. State/Storage Assessment is completed

---

## Portfolio Health Indicators

The portfolio is healthy when:
- Most projects have recent `EVALUATION.md` files
- The shortlist has ≤ 5 projects
- At least 1 project per month is archived or selected
- Weak ideas are removed, not kept alive indefinitely
- The human has a clear answer to: "What should I build next?"
