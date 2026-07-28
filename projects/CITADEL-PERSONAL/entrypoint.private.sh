#!/bin/bash
set -euo pipefail

SUPERVISOR_CONF="/etc/supervisord.private.conf"

log() {
    printf '[private-entrypoint] %s\n' "$*"
}

trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

load_env_file() {
    local file="$1"
    [[ -f "$file" ]] || return 0

    while IFS= read -r raw || [[ -n "$raw" ]]; do
        local line key value
        line="$(trim "${raw%$'\r'}")"
        [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
        [[ "$line" == *"="* ]] || continue

        key="$(trim "${line%%=*}")"
        value="$(trim "${line#*=}")"

        [[ "$value" == \"*\" && "$value" == *\" ]] && value="${value:1:${#value}-2}"
        [[ "$value" == \'*\' && "$value" == *\' ]] && value="${value:1:${#value}-2}"

        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            # Respect explicitly injected env vars from run/quadlet.
            [[ -n "${!key+x}" ]] && continue
            export "$key=$value"
        fi
    done < "$file"
}

ensure_kv() {
    local file="$1" key="$2" value="$3"
    touch "$file"
    if grep -qE "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

set_pv_default_model() {
    local file="$1" model="$2" tmp
    tmp="$(mktemp)"
    awk -v model="$model" '
        BEGIN { in_vision=0; replaced=0 }
        /^\[vision\][[:space:]]*$/ { in_vision=1; print; next }
        in_vision && /^\[/ {
            if (!replaced) {
                print "model = \"" model "\""
                replaced=1
            }
            in_vision=0
            print
            next
        }
        in_vision && /^[[:space:]]*model[[:space:]]*=/ {
            if (!replaced) {
                print "model = \"" model "\""
                replaced=1
            }
            next
        }
        { print }
        END {
            if (in_vision && !replaced) {
                print "model = \"" model "\""
            }
        }
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

set_napoleon_default_model() {
    local file="$1" model="$2"
    touch "$file"
    if grep -qE "^default_model:" "$file"; then
        sed -i "s|^default_model:.*|default_model: ${model}|" "$file"
    else
        printf '\ndefault_model: %s\n' "$model" >> "$file"
    fi
}

ensure_node_cli_tools() {
    local cli
    local missing=()
    for cli in claude codex openclaw; do
        if ! command -v "$cli" >/dev/null 2>&1; then
            missing+=("$cli")
        fi
    done

    if [[ ${#missing[@]} -eq 0 ]]; then
        log "Node CLIs already available: claude codex openclaw"
        return 0
    fi

    log "Installing missing Node CLIs: ${missing[*]}"
    if npm install -g --no-audit --no-fund --ignore-scripts \
        @anthropic-ai/claude-code @openai/codex openclaw; then
        npm cache clean --force >/dev/null 2>&1 || true
        hash -r
    else
        log "Node CLI install failed; continuing startup"
    fi
}

is_enabled() {
    local v="${1:-}"
    v="$(printf '%s' "$v" | tr '[:upper:]' '[:lower:]')"
    case "$v" in
        1|true|yes|y|on) return 0 ;;
        *) return 1 ;;
    esac
}

append_supervisor_program() {
    local name="$1" priority="$2" command="$3"
    cat >> "$SUPERVISOR_CONF" <<EOF
[program:${name}]
command=/bin/bash -lc '${command}'
autostart=true
autorestart=true
startsecs=1
priority=${priority}
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

EOF
}

append_supervisor_oneshot() {
    local name="$1" priority="$2" command="$3"
    cat >> "$SUPERVISOR_CONF" <<EOF
[program:${name}]
command=/bin/bash -lc '${command}'
autostart=true
autorestart=false
startsecs=0
priority=${priority}
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

EOF
}

build_supervisor_config() {
    cat > "$SUPERVISOR_CONF" <<'EOF'
[supervisord]
nodaemon=true
logfile=/dev/null
pidfile=/var/run/supervisord.pid
user=root

[unix_http_server]
file=/tmp/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

EOF

    append_supervisor_program "php-fpm" 20 "exec php-fpm -F"
    append_supervisor_program "caddy" 30 "exec caddy run --config /etc/caddy/Caddyfile"
    append_supervisor_program "citadel-hello-world" 40 "exec /opt/citadel/hello_world/venv/bin/python /opt/citadel/hello_world/app.py"

    if is_enabled "${ENABLE_PV_DACH:-1}"; then
        append_supervisor_program "pv-d-a-ch" 100 "cd /opt/apps/PV_D-A-CH && exec ./venv/bin/python webui.py"
    else
        log "PV_D-A-CH disabled via ENABLE_PV_DACH=${ENABLE_PV_DACH:-}"
    fi

    if is_enabled "${ENABLE_JUGO:-1}"; then
        append_supervisor_program "jugo" 110 "cd /opt/apps/JUGO && exec ./venv/bin/python server.py"
    else
        log "JUGO disabled via ENABLE_JUGO=${ENABLE_JUGO:-}"
    fi

    if is_enabled "${ENABLE_CODEANALYST:-1}"; then
        append_supervisor_program "codeanalyst" 120 "cd /opt/apps/CODEANALYST && exec ./venv/bin/python app.py"
    else
        log "CODEANALYST disabled via ENABLE_CODEANALYST=${ENABLE_CODEANALYST:-}"
    fi

    if is_enabled "${ENABLE_NAPOLEON:-1}"; then
        append_supervisor_program "napoleon-web" 130 "cd /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES && exec ./venv/bin/python mastermind_web.py"
    else
        log "NAPOLEON disabled via ENABLE_NAPOLEON=${ENABLE_NAPOLEON:-}"
    fi

    append_supervisor_oneshot "citadel-scan" 900 "sleep 3; /opt/citadel/scan.sh || true"
}

# Host-network defaults: set before credentials load, so secret files
# cannot override injected run/quadlet values.
export OPENAI_API_BASE="${OPENAI_API_BASE:-http://127.0.0.1:4000/v1}"
export DB_HOST="${DB_HOST:-127.0.0.1}"

CREDENTIALS_FILE="${PV_CREDS_FILE:-/run/secrets/pv_creds}"
if [[ ! -f "$CREDENTIALS_FILE" && -f "/srv/shared/openclaw/.PV" ]]; then
    CREDENTIALS_FILE="/srv/shared/openclaw/.PV"
fi
if [[ -f "$CREDENTIALS_FILE" ]]; then
    log "Loading credentials from ${CREDENTIALS_FILE}"
    load_env_file "$CREDENTIALS_FILE"
else
    log "No credentials file found at ${CREDENTIALS_FILE}; continuing with current env"
fi

export DEFAULT_MODEL="${DEFAULT_MODEL:-openai/gpt-5.4}"

export PV_DACH_PORT="${PV_DACH_PORT:-8080}"
export CODEANALYST_PORT="${CODEANALYST_PORT:-820}"
export JUGO_PORT="${JUGO_PORT:-840}"
export NAPOLEON_PORT="${NAPOLEON_PORT:-7700}"
export HTTPS_PORT="${HTTPS_PORT:-9443}"
export ENABLE_PV_DACH="${ENABLE_PV_DACH:-1}"
export ENABLE_CODEANALYST="${ENABLE_CODEANALYST:-1}"
export ENABLE_JUGO="${ENABLE_JUGO:-1}"
export ENABLE_NAPOLEON="${ENABLE_NAPOLEON:-1}"

# Prepare PV_D-A-CH env file
PV_ENV="/opt/apps/PV_D-A-CH/.PV_D-A-CHenv"
if [[ -f "$CREDENTIALS_FILE" ]]; then
    cp "$CREDENTIALS_FILE" "$PV_ENV"
elif [[ ! -f "$PV_ENV" ]]; then
    cp /opt/apps/PV_D-A-CH/.PV_D-A-CHenv.example "$PV_ENV"
fi
ensure_kv "$PV_ENV" PORT "$PV_DACH_PORT"
ensure_kv "$PV_ENV" OPENAI_API_BASE "$OPENAI_API_BASE"
[[ -n "${OPENAI_API_KEY:-}" ]] && ensure_kv "$PV_ENV" OPENAI_API_KEY "${OPENAI_API_KEY}"
[[ -n "${DB_BACKEND:-}" ]] && ensure_kv "$PV_ENV" DB_BACKEND "${DB_BACKEND}"
[[ -n "${DB_HOST:-}" ]] && ensure_kv "$PV_ENV" DB_HOST "${DB_HOST}"
[[ -n "${DB_PORT:-}" ]] && ensure_kv "$PV_ENV" DB_PORT "${DB_PORT}"
[[ -n "${DB_USER:-}" ]] && ensure_kv "$PV_ENV" DB_USER "${DB_USER}"
[[ -n "${DB_PASSWORD:-}" ]] && ensure_kv "$PV_ENV" DB_PASSWORD "${DB_PASSWORD}"
[[ -n "${DB_NAME:-}" ]] && ensure_kv "$PV_ENV" DB_NAME "${DB_NAME}"
set_pv_default_model "/opt/apps/PV_D-A-CH/PV_D-A-CH.toml" "$DEFAULT_MODEL"

# Prepare NAPOLEON env/config
NAP_ENV="/opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/.env"
if [[ -f "$CREDENTIALS_FILE" ]]; then
    cp "$CREDENTIALS_FILE" "$NAP_ENV"
elif [[ ! -f "$NAP_ENV" ]]; then
    : > "$NAP_ENV"
fi
ensure_kv "$NAP_ENV" OPENAI_API_BASE "$OPENAI_API_BASE"
ensure_kv "$NAP_ENV" EDITOR_PORT "$NAPOLEON_PORT"
[[ -n "${OPENAI_API_KEY:-}" ]] && ensure_kv "$NAP_ENV" OPENAI_API_KEY "${OPENAI_API_KEY}"
set_napoleon_default_model "/opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/mastermind_config.md" "$DEFAULT_MODEL"

# Prepare JUGO env
JUGO_ENV="/opt/apps/JUGO/.env"
if [[ ! -f "$JUGO_ENV" && -f "/opt/apps/JUGO/.env_example" ]]; then
    cp /opt/apps/JUGO/.env_example "$JUGO_ENV"
fi
ensure_kv "$JUGO_ENV" PORT "$JUGO_PORT"
[[ -n "${DEEPL_KEY:-}" ]] && ensure_kv "$JUGO_ENV" DEEPL_KEY "${DEEPL_KEY}"

# Prepare CODEANALYST bind config
cat > /opt/apps/CODEANALYST/codeanalyst.server.conf <<EOF
# Auto-generated by private entrypoint
host=0.0.0.0
port=${CODEANALYST_PORT}
EOF

ensure_node_cli_tools

log "Starting tailscaled"
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
sleep 2

if [[ -z "${TS_HOSTNAME:-}" ]]; then
    TS_HOSTNAME="citadel-private"
fi

if [[ -n "${TS_AUTHKEY:-}" ]]; then
    tailscale up --hostname="${TS_HOSTNAME}" --authkey="${TS_AUTHKEY}" || true
else
    tailscale up --hostname="${TS_HOSTNAME}" || true
fi

TS_DOMAIN="$(tailscale status --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('Self',{}).get('DNSName','').rstrip('.'))" 2>/dev/null || true)"
TS_CERT_DIR="/var/lib/tailscale/certs"
mkdir -p "$TS_CERT_DIR"

if [[ -n "$TS_DOMAIN" ]]; then
    tailscale cert --cert-file="$TS_CERT_DIR/cert.pem" --key-file="$TS_CERT_DIR/key.pem" "$TS_DOMAIN" || true
fi

LOCAL_CERT_DIR="/opt/citadel/certs"
mkdir -p "$LOCAL_CERT_DIR"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -days 3650 -nodes \
    -keyout "$LOCAL_CERT_DIR/local-key.pem" \
    -out "$LOCAL_CERT_DIR/local.pem" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    2>/dev/null

if [[ ! -s "$TS_CERT_DIR/cert.pem" || ! -s "$TS_CERT_DIR/key.pem" ]]; then
    cp "$LOCAL_CERT_DIR/local.pem" "$TS_CERT_DIR/cert.pem"
    cp "$LOCAL_CERT_DIR/local-key.pem" "$TS_CERT_DIR/key.pem"
    TS_DOMAIN="${TS_DOMAIN:-localhost}"
fi

cp /opt/citadel/deploy/Caddyfile /etc/caddy/Caddyfile
# Host-network mode: expose Caddy directly on configurable host port.
sed -i -E "s/\\{TS_DOMAIN\\}:443[[:space:]]*\\{/{TS_DOMAIN}:${HTTPS_PORT} {/" /etc/caddy/Caddyfile
sed -i -E "s#https://:443[[:space:]]*\\{#https://:${HTTPS_PORT} {#" /etc/caddy/Caddyfile
sed -i "s|{TS_DOMAIN}|${TS_DOMAIN:-localhost}|g" /etc/caddy/Caddyfile

mkdir -p /opt/citadel/CADDYFILES
if [[ ! -f /opt/citadel/CADDYFILES/00-bootstrap.caddy ]]; then
    cat > /opt/citadel/CADDYFILES/00-bootstrap.caddy <<'EOF'
# Created by private entrypoint during bootstrap.
EOF
fi

build_supervisor_config
log "Starting services via supervisord"
exec supervisord -c "$SUPERVISOR_CONF"
