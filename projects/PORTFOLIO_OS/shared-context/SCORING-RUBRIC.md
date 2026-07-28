# SCORING-RUBRIC.md — Evaluation Scoring Guide

Used by the Critic and Curator to produce consistent, comparable evaluations across projects.

---

## Multi-Agent Fit (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Single agent or script is clearly better. Multi-agent adds complexity with no benefit. |
| 2 | Multi-agent possible but not justified. Would work fine as one agent with tools. |
| 3 | Multi-agent optional. Real benefits exist but a single agent could do 80% of it. |
| 4 | Multi-agent natural. Different roles have genuinely different concerns and contexts. |
| 5 | Multi-agent essential. True feedback loops or competing perspectives are core to the system. |

**Red flags for low scores:**
- Serial handoffs disguised as agent collaboration
- Agents that share the same context and just relay messages
- No real feedback loop — just A → B → C pipeline
- One agent does all reasoning, others just format output

---

## Effort to MVP (1–5)

| Score | Meaning |
|-------|---------|
| 1 | 1–3 days. Mostly glue code and prompt engineering. |
| 2 | 1–2 weeks. Some integration work, known patterns. |
| 3 | 2–4 weeks. Real implementation work, a few unknowns. |
| 4 | 1–3 months. Significant engineering, research needed. |
| 5 | 3+ months or unclear. Many unknowns, risky assumptions. |

---

## GitHub-Star Potential (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Niche personal tool, no discoverability. |
| 2 | Useful but only for a small specific audience. |
| 3 | Solid niche tool. Would attract stars from a defined community. |
| 4 | Strong showcase potential. Novel approach or good timing. |
| 5 | Breakout potential. Solves a widespread pain in a novel way. |

**Factors that raise score:**
- Solves a problem developers encounter frequently
- Novel combination of tools or approach
- Clean CLI or API that others can build on
- Good README and demo potential

---

## Monetization Potential (1–5)

| Score | Meaning |
|-------|---------|
| 1 | No clear monetization path. Pure open-source utility. |
| 2 | Indirect monetization only (portfolio showcase, consulting leads). |
| 3 | Plausible SaaS or API model, but market is uncertain. |
| 4 | Clear monetization path with identifiable paying customers. |
| 5 | Strong direct revenue potential. Existing market with known willingness to pay. |

---

## Novelty Score (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Multiple mature projects already do this. No clear differentiation. |
| 2 | Existing solutions exist but this would be better in a specific way. |
| 3 | Some competition, but the niche or angle is not well-served. |
| 4 | Fresh approach to a known problem. Few direct competitors. |
| 5 | Genuinely new. No comparable project does this today. |

---

## Success Likelihood (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Core assumption is likely wrong. High failure risk. |
| 2 | Technically feasible but significant unknowns remain. |
| 3 | Feasible with effort. Some risks are present but manageable. |
| 4 | High likelihood of working. Core approach is validated or low-risk. |
| 5 | Near-certain to produce something useful. Clear path, known patterns. |

---

## State / Storage Assessment

Classify the appropriate storage model for each project:

| Category | Meaning |
|----------|---------|
| `markdown-first` | Plain text files are sufficient. No DB needed. |
| `markdown + scripts` | Text files plus simple shell/Python helpers. |
| `json/yaml enough` | Structured config or state, no relational queries needed. |
| `sqlite recommended` | Local structured queries justified. |
| `sql justified now` | Relational DB needed from day one. |
| `sql later, not now` | Start simple; DB becomes justified if scale increases. |
| `heavy db overkill` | Full DB would be overengineering for the scope. |

**Threshold questions:**
- Is the state mainly narrative or structured?
- Will things need to be filtered, joined, or aggregated frequently?
- Are there many objects or just a few central documents?
- Is history or queryability a core workflow requirement?
- Is parallelism, multi-user, or automation at scale a requirement?

---

## Scoring Guidance

**Avoid score inflation.** If everything scores 4–5, the rubric is not being used honestly.

**Justify every score below 3 or above 4.** These outliers carry the most decision weight.

**Use 3 as the honest middle.** A 3 is not a failure — it means "real, but limited."

**Do not score what you have not evaluated.** Leave fields blank rather than guess.
