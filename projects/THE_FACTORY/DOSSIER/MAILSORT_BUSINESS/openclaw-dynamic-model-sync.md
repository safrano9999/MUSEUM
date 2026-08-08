# OpenClaw Dynamic Model Sync (Idea Draft)

## Problem
OpenClaw model selection is stable and policy-friendly, but largely tied to static declarations in `openclaw.json`.
In contrast, adaptive systems (like the Telegram AI bot) can discover model availability at runtime (e.g., Ollama up/down, API model list changes) and update routing dynamically.

## Goal
Add a thin **dynamic model sync layer** in front of OpenClaw config so model inventory stays fresh automatically while preserving OpenClaw’s policy structure.

## Proposed Architecture

1. **Discovery Collectors**
   - Ollama collector: probes running daemon + installed models
   - Provider collectors: OpenAI-compatible, Anthropic, Gemini, etc. (where list APIs exist)
   - Optional local probes: lightweight health checks (`chat/completions` smoke test)

2. **Normalization Layer**
   - Convert discovered models into OpenClaw schema-compatible entries
   - Attach metadata: provider, context window, reasoning capability, cost, latency class
   - Map aliases (e.g. `flash`, `grok-code`, `GLM`)

3. **Policy Filter**
   - Include/deny lists per environment (dev/prod)
   - Safety gates (minimum model size, no-web for weak models, sandbox requirements)
   - Optional tags: `experimental`, `canary`, `stable`

4. **Config Renderer**
   - Render `models.providers` / `agents.defaults.models` sections
   - Preserve user-managed blocks (merge strategy)
   - Write only if diff detected

5. **Activation**
   - Trigger OpenClaw hot reload (or controlled restart)
   - Rollback to last known-good config on validation failure

## Update Modes
- **On startup**: sync once before OpenClaw starts
- **Periodic**: cron every X minutes
- **On signal**: manual command (`sync-models now`)

## Safety and Reliability
- Never overwrite auth tokens or unrelated config sections
- Keep last N rendered configs for rollback
- Dry-run mode (`--diff` only)
- Rate limit external provider API polling
- Debounce reloads (avoid restart storms)

## MVP Scope
1. Ollama-only discovery
2. Merge into `openclaw.json` model sections
3. Diff-based write + reload
4. Logging + rollback

## Phase 2
- Add provider API discovery (OpenAI-compatible, Gemini, etc.)
- Add health-scored routing classes
- Add canary promotion logic

## Expected Outcome
OpenClaw remains policy-first, but gains adaptive model availability similar to dynamic orchestration systems.
Best of both worlds: **runtime flexibility + governance stability**.
