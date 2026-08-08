# litellm_discovery — Multi-Consumer Dynamic Model Registry

## Vision
Build a reusable **Model Orchestrator Extension** that discovers, validates, and serves live model availability for:
- OpenClaw bots/agents
- Telegram AI bot
- Any other local services needing dynamic LLM routing

This should be Git-ready as a standalone module/service, not hardcoded into one app.

---

## Why
Current configs are often static (`openclaw.json`, app-local YAML/ENV), while real model ecosystems are dynamic:
- Ollama daemon appears/disappears
- provider model catalogs change
- account quotas and transient errors alter real availability

A shared orchestrator avoids duplicated logic across programs.

---

## Product Scope

### Core responsibilities
1. **Discover** models from multiple backends
2. **Probe** real availability/latency
3. **Normalize** into one canonical schema
4. **Policy-filter** by risk/profile/tenant
5. **Publish** to consumers via API + file outputs
6. **Notify** on changes (push events/webhooks)

### Non-goals (initial)
- Full conversational gateway replacement
- Vendor-specific prompt transformation engine
- Billing system

---

## High-Level Architecture

```text
[Collectors]
  - ollama
  - openai-compatible
  - anthropic
  - google
  - xai / others
       |
       v
[Normalizer] -> [Health Prober] -> [Policy Engine] -> [Registry Store]
                                                    |             |
                                                    v             v
                                           [HTTP API / WS]   [Rendered Outputs]
                                                             - openclaw.json patch
                                                             - .env/.yaml exports
```

---

## Canonical Model Schema (example)

```json
{
  "id": "ollama/qwen3.5:2b",
  "provider": "ollama",
  "family": "qwen",
  "input": ["text"],
  "reasoning": false,
  "contextWindow": 32768,
  "maxTokens": 8192,
  "capabilities": {
    "tools": false,
    "vision": false,
    "jsonMode": true,
    "streaming": true
  },
  "health": {
    "reachable": true,
    "p95LatencyMs": 420,
    "errorRate": 0.01,
    "lastCheckedAt": "2026-03-19T00:00:00Z"
  },
  "policyTags": ["local", "small", "needs-sandbox"],
  "cost": {
    "input": 0,
    "output": 0
  }
}
```

---

## Consumer Integration Modes

### 1) OpenClaw integration
- Render/patch `openclaw.json` model sections
- Preserve user-owned sections (merge-safe)
- Trigger hot reload/restart only on meaningful changes

### 2) Telegram AI bot integration
- Consume orchestrator API (`/models`, `/routes`, `/health`)
- Runtime route selection based on status and tags

### 3) Generic integration
- REST/WS API
- Optional generated files:
  - `models.snapshot.json`
  - `.env` exports
  - YAML route maps

---

## API Contract (MVP)

- `GET /v1/models` → full normalized catalog
- `GET /v1/models?tag=stable&provider=ollama`
- `GET /v1/routes/:profile` → resolved preferred model order
- `GET /v1/health` → backend/collector status
- `POST /v1/reload` → force rediscovery (auth required)
- `GET /v1/events` (SSE/WS) → model up/down + route change events

---

## Policy Engine

Policies should be profile-driven:
- `dev-flex`
- `prod-safe`
- `cost-optimized`
- `local-first`

Example rules:
- deny small models for privileged tasks
- require sandbox for models tagged `small`
- prefer local models unless latency/quality threshold is violated
- canary models only for selected agents

---

## Reliability / Safety

- Strict token redaction in logs
- Retry with backoff + circuit breaker per provider
- Last-known-good registry snapshot fallback
- Change debounce to avoid restart storms
- Signed snapshots optional for tamper detection

---

## Repo Layout (proposal)

```text
model-orchestrator/
  README.md
  docs/
    architecture.md
    api.md
    policy.md
  src/
    collectors/
    normalizer/
    probes/
    policy/
    renderers/
    api/
  examples/
    openclaw/
      renderer-config.yaml
    telegram-bot/
      client-example.ts
  deployments/
    systemd/
    docker/
    podman/
```

---

## MVP Milestones

### M1 — Core local value
- Ollama collector
- registry store
- `/v1/models` + `/v1/health`
- OpenClaw renderer (diff-write)

### M2 — Multi-provider
- OpenAI-compatible collector
- Anthropic/Google collectors
- health probe scoring
- route profile resolution

### M3 — Multi-consumer rollout
- Telegram bot client adapter
- events stream
- policy packs + canary routing

---

## Open Questions
1. Single global orchestrator vs one per host/tenant?
2. How strict should auth be for `/v1/reload` and `/v1/events`?
3. Should routing return one winner or ranked fallback list?
4. Centralized registry persistence (sqlite/postgres) vs local JSON snapshots only?

---

## Immediate Next Step
Create a public Git repo for this extension spec + minimal service skeleton, then integrate OpenClaw first as the reference consumer.
