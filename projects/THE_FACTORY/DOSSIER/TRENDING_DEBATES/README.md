# Trending Debates Project

**Goal:** Daily controversial topic coverage with opposing perspectives on X/Twitter.

## Agents

- **uk (rafael_cos_bot)** — Crawler: Finds sources, validates topic, creates brief
- **serbia** — Bullish take: Writes positive/opportunity angle
- **russia (healer9999bot)** — Bearish take: Writes critical/risk angle
- **main (magabuttlerbot)** — Coordinator: Manages flow, approves content, posts

## Daily Workflow

1. **You provide thesis** → Fill `today-thesis.md`
2. **uk crawls** → Gathers sources, creates `crawler-brief.md`
3. **serbia writes bullish** → Creates `bullish-thread.md`
4. **russia writes bearish** → Creates `bearish-thread.md`
5. **main approves** → Reviews, makes final edits
6. **Post to X** → Both threads drop simultaneously

## Files

- `today-thesis.md` — Your daily topic + angle (you fill this)
- `crawler-brief.md` — Research findings (uk creates)
- `bullish-thread.md` — Bullish X thread (serbia creates)
- `bearish-thread.md` — Bearish X thread (russia creates)
- `posted.md` — Log of posted content

## Models

- uk/russia: gemini-flash-latest (snappy, creative)
- serbia: gpt-5.1-codex (strong narrative)
- main: claude-haiku (coordinator)
