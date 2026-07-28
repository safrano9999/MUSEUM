#!/bin/bash
set -euo pipefail

BRIDGE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Defaults — can be overridden by clawbridge.conf
TRIGGERDIR="$BRIDGE_DIR/TRIGGERDIR"
LOG_DIR="$BRIDGE_DIR/logs"
export TRIGGERDIR

# Load deployment config (path overrides, no credentials)
# shellcheck disable=SC1091
[ -f "$BRIDGE_DIR/clawbridge.conf" ] && source "$BRIDGE_DIR/clawbridge.conf"

RULES_RUNTIME="$LOG_DIR/.jobs_runtime.json"
FILE_RULES="$BRIDGE_DIR/dispatcher_filebased_rules.json"
LOG_FILE="$LOG_DIR/CLAWBRIDGE.log"
DROP_LOG="$LOG_DIR/DROP.log"
BOTENV="$BRIDGE_DIR/.botenv"

mkdir -p "$LOG_DIR"

# Build merged job registry from all clawbridge_plugin.json files:
# own directory first, then all sibling project directories.
# Script paths are resolved to absolute so callers don't need to know the plugin dir.
build_job_registry() {
    python3 - "$BRIDGE_DIR" "$RULES_RUNTIME" <<'PYEOF'
import sys, json
from pathlib import Path

bridge_dir   = Path(sys.argv[1])
out_file     = Path(sys.argv[2])
projects_dir = bridge_dir.parent
registry     = {}

def resolve(script, base):
    p = Path(script)
    return str((base / p).resolve()) if not p.is_absolute() else script

def load_plugin(pj):
    try:
        with open(pj) as f:
            config = json.load(f)
    except Exception:
        return
    for job, meta in config.get("jobs", {}).items():
        if job in registry:
            print(f"WARNING: duplicate job '{job}' in {pj}", file=sys.stderr)
            continue
        if "script" in meta:
            meta["script"] = resolve(meta["script"], pj.parent)
        registry[job] = meta

# Own clawbridge_plugin.json first
own = bridge_dir / "clawbridge_plugin.json"
if own.exists():
    load_plugin(own)

# All sibling clawbridge_plugin.json files
for pj in sorted(projects_dir.glob("*/clawbridge_plugin.json")):
    if pj.parent == bridge_dir:
        continue
    load_plugin(pj)

with open(out_file, "w") as f:
    json.dump({"jobs": registry}, f, indent=2)
PYEOF
}

build_job_registry
RULES="$RULES_RUNTIME"

log()  { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"; }
dlog() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$DROP_LOG"; }

# Load Telegram credentials if available
BOT_TOKEN=""
CHAT_ID=""
if [ -f "$BOTENV" ]; then
    # shellcheck disable=SC1090
    source "$BOTENV"
fi

tg_send() {
    local text="$1"
    [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ] && return
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        --data-urlencode "text=${text}" > /dev/null
}

tg_send_document() {
    local filepath="$1"
    [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ] && return
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F "chat_id=${CHAT_ID}" \
        -F "document=@${filepath}" > /dev/null
}

# Parse rules.json — returns job field via python3
get_job_field() {
    local job="$1" field="$2"
    python3 - "$RULES" "$job" "$field" <<'PYEOF'
import sys, json
rules_file, job, field = sys.argv[1], sys.argv[2], sys.argv[3]
with open(rules_file) as f:
    rules = json.load(f)
jobs = rules.get("jobs", {})
if job not in jobs:
    sys.exit(1)
val = jobs[job].get(field)
if val is None:
    sys.exit(1)
if isinstance(val, (dict, list)):
    print(json.dumps(val))
else:
    print(val)
PYEOF
}

job_exists() {
    python3 - "$RULES" "$1" <<'PYEOF'
import sys, json
rules_file, job = sys.argv[1], sys.argv[2]
with open(rules_file) as f:
    rules = json.load(f)
sys.exit(0 if job in rules.get("jobs", {}) else 1)
PYEOF
}

# Returns 0 if actor is allowed to trigger job, 1 if denied.
# No allowed_actors field in rules.json = any actor is allowed.
check_policy() {
    local job="$1" actor="$2"
    python3 - "$RULES" "$job" "$actor" <<'PYEOF'
import sys, json
rules_file, job, actor = sys.argv[1], sys.argv[2], sys.argv[3]
with open(rules_file) as f:
    rules = json.load(f)
allowed = rules.get("jobs", {}).get(job, {}).get("allowed_actors")
if allowed is None:
    sys.exit(0)  # no restriction — any actor allowed
sys.exit(0 if actor in allowed else 1)
PYEOF
}

# Safely JSON-encode a string value (handles quotes, newlines, etc.)
json_str() {
    python3 -c "import sys,json; print(json.dumps(sys.argv[1]))" "$1"
}

# Append one JSON-Lines entry to the current job's log file (set by run_job)
jlog() {
    echo "$1" >> "$JOB_LOG"
}


get_reply_before() {
    local job="$1"
    python3 - "$RULES" "$job" <<'PYEOF'
import sys, json
rules_file, job = sys.argv[1], sys.argv[2]
with open(rules_file) as f:
    rules = json.load(f)
# reply_before lives in telegram_actions, not rules.json
# clawbridge receives it embedded in the command payload
sys.exit(1)
PYEOF
}

run_job() {
    local actor="$1" job="$2" id="$3" reply_before="$4"

    # Per-job execution log: CLAWBRIDGE/logs/<actor>/<start-timestamp>.json
    local log_dir="$LOG_DIR/$actor"
    mkdir -p "$log_dir"
    JOB_LOG="$log_dir/$(date -Iseconds).json"

    local script args_json
    script=$(get_job_field "$job" script) || { log "[$actor] ERROR job '$job' not in rules.json"; return; }
    # Resolve relative paths from BRIDGE_DIR
    [[ "$script" == ./* ]] && script="$BRIDGE_DIR/${script#./}"

    args_json=$(get_job_field "$job" args) || args_json="[]"

    if [ ! -x "$script" ]; then
        log "[$actor] ERROR script not executable: $script"
        jlog "{\"event\":\"ERROR\",\"job\":$(json_str "$job"),\"id\":$(json_str "$id"),\"reason\":\"script not executable\",\"timestamp\":\"$(date -Iseconds)\"}"
        return
    fi

    # Build args array
    mapfile -t args < <(python3 -c "import sys,json; [print(a) for a in json.loads(sys.argv[1])]" "$args_json")

    log "[$actor] START $job  (id=$id)"
    jlog "{\"event\":\"START\",\"job\":$(json_str "$job"),\"id\":$(json_str "$id"),\"actor\":$(json_str "$actor"),\"timestamp\":\"$(date -Iseconds)\"}"

    set +e
    local tmpout
    tmpout=$(mktemp)
    "$script" "${args[@]}" 2>&1 | tee "$tmpout"
    exit_code=${PIPESTATUS[0]}
    output=$(cat "$tmpout")
    rm -f "$tmpout"
    set -e

    # Write each output line as its own event
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        jlog "{\"event\":\"OUTPUT\",\"line\":$(json_str "$line"),\"timestamp\":\"$(date -Iseconds)\"}"
    done <<< "$output"

    local status on_empty_exit_code on_locked_exit_code
    read -r on_empty_exit_code on_locked_exit_code < <(python3 - "$RULES" "$job" <<'PYEOF'
import sys, json
rules_file, job = sys.argv[1], sys.argv[2]
with open(rules_file) as f:
    rules = json.load(f)
fb = rules.get("jobs", {}).get(job, {}).get("feedback", {})
print(fb.get("on_empty_exit", ""), fb.get("on_locked_exit", ""))
PYEOF
)
    if [ "$exit_code" -eq 0 ]; then
        status="ok"
    elif [ -n "$on_locked_exit_code" ] && [ "$exit_code" -eq "$on_locked_exit_code" ]; then
        status="locked"
    elif [ -n "$on_empty_exit_code" ] && [ "$exit_code" -eq "$on_empty_exit_code" ]; then
        status="empty"
    else
        status="error"
    fi
    jlog "{\"event\":\"END\",\"job\":$(json_str "$job"),\"id\":$(json_str "$id"),\"status\":\"$status\",\"exit_code\":$exit_code,\"timestamp\":\"$(date -Iseconds)\"}"

    log "[$actor] $([ "$status" = "error" ] && echo ERROR || echo OK)    $job  (exit=$exit_code, status=$status)"


    # Send Telegram feedback if configured
    local feedback_json
    feedback_json=$(get_job_field "$job" feedback) || feedback_json="{}"

    python3 - "$feedback_json" "$exit_code" "$output" "$BOT_TOKEN" "$CHAT_ID" <<'PYEOF'
import sys, json, urllib.request, urllib.parse

feedback  = json.loads(sys.argv[1])
exit_code = int(sys.argv[2])
output    = sys.argv[3]
bot_token = sys.argv[4]
chat_id   = sys.argv[5]

if not bot_token or not chat_id or bot_token == "...":
    sys.exit(0)

def send(msg):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{bot_token}/sendMessage", data)

on_empty_exit  = feedback.get("on_empty_exit")
on_locked_exit = feedback.get("on_locked_exit")
if on_locked_exit is not None and exit_code == on_locked_exit:
    msg = feedback.get("on_locked")
    if msg:
        send(msg)
elif on_empty_exit is not None and exit_code == on_empty_exit:
    msg = feedback.get("on_empty")
    if msg:
        send(msg)
elif exit_code == 0:
    msg = feedback.get("on_success")
    if msg:
        send(msg)
else:
    msg = feedback.get("on_error")
    if msg:
        send(msg)

if feedback.get("on_output", False) and output:
    send(output)
PYEOF
}

process_file() {
    local filepath="$1"
    local actor subfolder filename

    # Extract top-level actor from path
    # filepath: .../TRIGGERDIR/ACTOR/file.json  or  .../TRIGGERDIR/ACTOR/subdir/file
    local rel="${filepath#$TRIGGERDIR/}"
    local actor="${rel%%/*}"
    local subfolder
    subfolder=$(basename "$(dirname "$filepath")")
    filename=$(basename "$filepath")

    # Skip hidden / temp files
    [[ "$filename" == .* ]] && return
    [ -f "$filepath" ] || return

    case "$actor" in
        OUTBOX)
            log "[OUTBOX] sending document: $filename"
            tg_send_document "$filepath"
            rm -f "$filepath"
            log "[OUTBOX] sent and deleted: $filename"
            return
            ;;
        rafael|claude|openclaw)
            # Check dispatcher_filebased_rules.json for non-JSON files
            if [[ "$filename" != *.json ]] && [ -f "$FILE_RULES" ]; then
                ext=".${filename##*.}"
                action=$(python3 - "$FILE_RULES" "$ext" <<'PYEOF'
import sys, json
rules_file, ext = sys.argv[1], sys.argv[2]
with open(rules_file) as f:
    rules = json.load(f)
for rule in rules.get("file_rules", []):
    if ext in rule.get("match_ext", []):
        print(rule.get("action", ""))
        break
PYEOF
)
                if [ "$action" = "tg_send_document" ]; then
                    log "[$actor] file_rule: sending document: $filename"
                    tg_send_document "$filepath"
                    rm -f "$filepath"
                    log "[$actor] sent and deleted: $filename"
                    return
                fi
            fi
            # Trigger file: bare filename matches a job name or job's command alias
            bare="${filename%.*}"
            job_to_run=$(python3 - "$RULES" "$bare" <<'PYEOF'
import sys, json
rules_file, name = sys.argv[1], sys.argv[2]
with open(rules_file) as f:
    rules = json.load(f)
jobs = rules.get("jobs", {})
if name in jobs:
    print(name); sys.exit(0)
for jname, meta in jobs.items():
    if meta.get("command") == name:
        print(jname); sys.exit(0)
sys.exit(1)
PYEOF
) || job_to_run=""
            if [ -n "$job_to_run" ]; then
                log "[$actor] trigger file: $filename → job $job_to_run"
                rm -f "$filepath"
                run_job "$actor" "$job_to_run" "trigger-$$" ""
                return
            fi
            ;;
        *)
            dlog "DROPPED [$actor/$subfolder] $filename"
            return
            ;;
    esac

    # Parse JSON payload
    local type job id reply_before
    read -r type job id reply_before < <(python3 - "$filepath" <<'PYEOF'
import sys, json
try:
    with open(sys.argv[1]) as f:
        p = json.load(f)
    print(p.get("type",""), p.get("job",""), p.get("id",""), p.get("reply_before",""))
except Exception as e:
    print("", "", "", "")
PYEOF
)

    if [ "$type" != "command" ] || [ -z "$job" ] || [ -z "$id" ]; then
        dlog "DROPPED [$actor] $filename (not a valid command payload)"
        rm -f "$filepath"
        return
    fi

    if ! job_exists "$job"; then
        dlog "DROPPED [$actor] $filename (unknown job: $job)"
        rm -f "$filepath"
        return
    fi

    if ! check_policy "$job" "$actor"; then
        log "[$actor] DENIED $job — actor not in allowed_actors"
        local deny_dir="$LOG_DIR/$actor"
        mkdir -p "$deny_dir"
        echo "{\"event\":\"DENIED\",\"job\":$(json_str "$job"),\"id\":$(json_str "$id"),\"actor\":$(json_str "$actor"),\"reason\":\"actor not in allowed_actors\",\"timestamp\":\"$(date -Iseconds)\"}" \
            >> "$deny_dir/$(date -Iseconds)_denied.json"
        rm -f "$filepath"
        return
    fi

    # Remove trigger file before running
    rm -f "$filepath"

    run_job "$actor" "$job" "$id" "$reply_before"
}

log "clawbridge started (PID $$) — watching $TRIGGERDIR"

# Process any files already present at startup
find "$TRIGGERDIR" -maxdepth 2 -type f ! -name '.*' | while IFS= read -r f; do
    process_file "$f"
done

# Main inotify loop
inotifywait -m -r -e close_write,moved_to --format '%w%f' "$TRIGGERDIR" | \
while IFS= read -r filepath; do
    process_file "$filepath" &
done
