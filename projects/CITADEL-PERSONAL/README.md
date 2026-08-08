PRIVATE CITADEL profile (4 extra repos + URL-based LLM routing)

This setup extends CITADEL with:
- `PV_D-A-CH` (default port `8080`)
- `CODEANALYST` (default port `820`)
- `JUGO` (default port `840`)
- `NAPOLEON_HILLS_AI_MASTERMIND_CLASSES` web editor (default port `7700`)

Preinstalled extra CLIs (not auto-started, no login required during build):
- `claude` (from `@anthropic-ai/claude-code`)
- `codex` (from `@openai/codex`)
- `openclaw`
- `hermes` and `hermes-agent` (from `NousResearch/hermes-agent`)

All model calls are configured for OpenAI-compatible URL mode by default:
- `OPENAI_API_BASE=http://127.0.0.1:4000/v1`
- `DEFAULT_MODEL=openai/gpt-5.4`

Credentials injection:
- Mount host file `/srv/shared/openclaw/.PV` as read-only into container.
- Entry point loads key/value pairs from that file and applies them to PV + Napoleon.

Build

Use `/home/openclaw/safrano9999` as build context:

```bash
podman build \
  -f /home/openclaw/safrano9999/CITADEL/PERSONAL/Dockerfile \
  -t localhost/CITADELPRIVATE:latest \
  /home/openclaw/safrano9999
```

Run (host network, LiteLLM at 127.0.0.1:4000)

```bash
podman run -d --name CITADELPRIVATE \
  --network host \
  --cap-add NET_ADMIN --cap-add NET_RAW \
  --device /dev/net/tun \
  -v /srv/shared/openclaw/.PV:/run/secrets/pv_creds:ro,Z \
  -e PV_CREDS_FILE=/run/secrets/pv_creds \
  -e OPENAI_API_BASE=http://127.0.0.1:4000/v1 \
  -e DEFAULT_MODEL=openai/gpt-5.4 \
  localhost/CITADELPRIVATE:latest
```

Notes

- Entry point starts services via `supervisord` (PID1), not shell background jobs.
- Service toggles:
  - `ENABLE_PV_DACH=1|0`
  - `ENABLE_CODEANALYST=1|0`
  - `ENABLE_JUGO=1|0`
  - `ENABLE_NAPOLEON=1|0`
- It injects model/base-url defaults into:
  - `PV_D-A-CH/.PV_D-A-CHenv`
  - `PV_D-A-CH/PV_D-A-CH.toml` (`[vision].model`)
  - `NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/.env`
  - `NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/mastermind_config.md` (`default_model`)
- After service start, CITADEL runs `/opt/citadel/scan.sh`.
