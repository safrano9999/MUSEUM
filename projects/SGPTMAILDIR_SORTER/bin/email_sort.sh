#!/bin/bash
set -euo pipefail

if [ -f "$HOME/.bashrc_sgpt" ]; then
  # avoid leaking env output into prompt/logs (handle xtrace shells)
  _xtrace_was_on=0
  case "$-" in
    *x*) _xtrace_was_on=1; set +x ;;
  esac
  source "$HOME/.bashrc_sgpt" >/dev/null 2>&1
  if [ "$_xtrace_was_on" -eq 1 ]; then set -x; fi
fi

MAILBOXES=("gmail")
PDF_ENABLED="true"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# parse args (mailboxes + optional flags)
SKIP_OFFLINEIMAP="false"
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --pdf=false)
      PDF_ENABLED="false"
      ;;
    --pdf=true)
      PDF_ENABLED="true"
      ;;
    --no-offlineimap)
      SKIP_OFFLINEIMAP="true"
      ;;
    *)
      ARGS+=("$arg")
      ;;
  esac
done

if [ "${#ARGS[@]}" -gt 0 ]; then
  MAILBOXES=("${ARGS[@]}")
fi

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_BASE="${CONFIG_BASE:-$BASE_DIR}"
CONFIG_DIR="$CONFIG_BASE/rules"
LOCK_FILE="$BASE_DIR/email_sort.lock"
LOG_DIR="$BASE_DIR/LOGS"
EMAIL_RULES="$BASE_DIR/goodie_openclaw_low_llm_advises.txt"
SGPT_CONFIG_FILE="$CONFIG_BASE/sgpt_config.yaml"
SGPT_BIN="sgpt"
if [ -x "/opt/venv/bin/sgpt" ]; then
  SGPT_BIN="/opt/venv/bin/sgpt"
fi

# ---------- Read a key=value entry from sgpt_config.yaml ----------
# Usage: sgpt_cfg_get KEY [default]
sgpt_cfg_get() {
  local key="$1"
  local val=""
  if [ -f "$SGPT_CONFIG_FILE" ]; then
    val=$(grep -E "^${key}[[:space:]]*=" "$SGPT_CONFIG_FILE" 2>/dev/null \
          | head -1 | sed 's/^[^=]*=[[:space:]]*//' | tr -d '\r')
  fi
  printf '%s' "$val"
}

# Priority: sgpt_config.yaml → env var → last-resort default
# (per-mailbox JSON can override later in load_account_config)
MODEL=$(sgpt_cfg_get DEFAULT_MODEL)
API_BASE_URL=$(sgpt_cfg_get API_BASE_URL)
SGPT_API_KEY="${SGPT_API_KEY:-${OPENAI_API_KEY:-}}"

# Export all keys from sgpt_config.yaml as env vars (for LiteLLM provider routing)
if [ -f "$SGPT_CONFIG_FILE" ]; then
  set -a
  source "$SGPT_CONFIG_FILE" 2>/dev/null || true
  set +a
fi
# ------------------------------------------------------------------

SGPT_CMD=(env OPENAI_API_KEY="$SGPT_API_KEY" API_BASE_URL="$API_BASE_URL" SGPT_CONFIG="$SGPT_CONFIG_FILE" "$SGPT_BIN" --model "$MODEL" --no-md)
DEST_BASE="$BASE_DIR/Mail"
TMP_DIR="/tmp/email-sort-sgpt"
CORRECTIONS_DB="$BASE_DIR/corrections.jsonl"
PYTHON_BIN="python3"
if [ -x "/opt/venv/bin/python3" ]; then
  PYTHON_BIN="/opt/venv/bin/python3"
fi
mkdir -p "$LOG_DIR" "$TMP_DIR" "$CONFIG_DIR" "$BASE_DIR/ZEROINBOX"

if [ -f "$LOCK_FILE" ]; then
  echo "[email_sort] Lock file already present ($LOCK_FILE). Aborting." >&2
  exit 2
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

TS=$(date +%Y-%m-%d_%H-%M-%S)
MAIN_LOG="$LOG_DIR/email-sort-${TS}.md"

cat <<LOGHDR > "$MAIN_LOG"
# Email Run v07 $(date)
Rules File: $EMAIL_RULES
Model: $MODEL
API Base: $API_BASE_URL
LOGHDR

cp "$BASE_DIR/LOGS/EMAIL_SORT.md" "$BASE_DIR/LOGS/EMAIL_SORT-${TS}.md" 2>/dev/null || true

declare -A DEST_MAP=(
  [archiv_agb]="INBOX.Archiv.AGB"
  [archiv_bezahlt]="INBOX.Archiv.bezahlt"
  [freitag]="INBOX.Freitag"
  [loeschen]="INBOX.loeschen"
  [welcome]="INBOX.Archiv.welcome"
  [system]="INBOX.Archiv.Systemmeldungen"
  [kommunikation]="INBOX.Archiv.Kommunikation"
  [newsletter]="INBOX.Archiv.newsletter"
  [uncertain]="INBOX.sort_ai_uncertain"
)

load_account_config() {
  local mailbox="$1"
  local cfg="$CONFIG_DIR/${mailbox}.json"
  if [ -f "$cfg" ]; then
    # per-mailbox JSON: model/api_base_url fall back to sgpt_config.yaml values
    MODEL=$(jq -r --arg def "$(sgpt_cfg_get DEFAULT_MODEL)" '.model // $def' "$cfg")
    API_BASE_URL=$(jq -r --arg def "$(sgpt_cfg_get API_BASE_URL)" '.api_base_url // $def' "$cfg")
    EMAIL_RULES=$(jq -r '.rules_file // empty' "$cfg")
    # Re-source config for updated keys
    if [ -f "$SGPT_CONFIG_FILE" ]; then
      set -a; source "$SGPT_CONFIG_FILE" 2>/dev/null || true; set +a
    fi
    SGPT_CMD=(env OPENAI_API_KEY="$SGPT_API_KEY" API_BASE_URL="$API_BASE_URL" SGPT_CONFIG="$SGPT_CONFIG_FILE" "$SGPT_BIN" --model "$MODEL" --no-md)
    DEST_MAP=()
    while IFS=$'\t' read -r key val; do
      [ -n "$key" ] || continue
      DEST_MAP[$key]="$val"
    done < <(jq -r '.dest_map | to_entries[] | "\(.key)\t\(.value)"' "$cfg")
  else
    # fallback: re-read from sgpt_config.yaml (single source of truth)
    EMAIL_RULES="$BASE_DIR/goodie_openclaw_low_llm_advises.txt"
    MODEL=$(sgpt_cfg_get DEFAULT_MODEL)
    API_BASE_URL=$(sgpt_cfg_get API_BASE_URL)
    SGPT_CONFIG_FILE="$CONFIG_BASE/sgpt_config.yaml"
    # Re-source config for keys
    if [ -f "$SGPT_CONFIG_FILE" ]; then
      set -a; source "$SGPT_CONFIG_FILE" 2>/dev/null || true; set +a
    fi
    SGPT_CMD=(env OPENAI_API_KEY="$SGPT_API_KEY" API_BASE_URL="$API_BASE_URL" SGPT_CONFIG="$SGPT_CONFIG_FILE" "$SGPT_BIN" --model "$MODEL" --no-md)
    DEST_MAP=(
      [archiv_agb]="INBOX.Archiv.AGB"
      [archiv_bezahlt]="INBOX.Archiv.bezahlt"
      [freitag]="INBOX.Freitag"
      [loeschen]="INBOX.loeschen"
      [welcome]="INBOX.Archiv.welcome"
      [system]="INBOX.Archiv.Systemmeldungen"
      [kommunikation]="INBOX.Archiv.Kommunikation"
      [newsletter]="INBOX.Archiv.newsletter"
      [uncertain]="INBOX.sort_ai_uncertain"
    )
  fi
}

extract_email_json() {
  local file="$1"
  "$PYTHON_BIN" - <<'PY' "$file"
import email, email.policy, json, sys
from pathlib import Path
path = Path(sys.argv[1])
with open(path, 'rb') as fp:
    msg = email.message_from_binary_file(fp, policy=email.policy.default)
parts = []
if msg.is_multipart():
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            try:
                parts.append(part.get_content())
            except Exception:
                continue
else:
    if msg.get_content_type() == 'text/plain':
        try:
            parts.append(msg.get_content())
        except Exception:
            pass
body = "\n\n".join(parts)
info = {
    "subject": msg.get('Subject', ''),
    "from": msg.get('From', ''),
    "date": msg.get('Date', ''),
    "headers": {k: v for k, v in msg.items()},
    "body_snippet": body[:4000],
}
print(json.dumps(info))
PY
}

call_sgpt() {
  local email_json="$1"
  local prev_dest_label="${2:-}"
  local corrections_block="${3:-}"
  local allowed_list="${4:-}"
  local prompt
  prompt=$(cat <<PROMPT
You are an email sorting agent. Follow the directives.

=== RULE SUMMARY ===
$(sed -n '1,200p' "$EMAIL_RULES")

=== EXCLUSION DIRECTIVE ===
${prev_dest_label}

=== CORRECTIONS HISTORY (ONLY USE IF RELEVANT) ===
${corrections_block}

Return strict JSON with keys:
summary, unsubscribe, destination, reason
Destination must be one of: ${allowed_list}

Email JSON:
$email_json
PROMPT
  )
  printf '%s' "$prompt" | "${SGPT_CMD[@]}"
}

log_entry() {
  local info_json="$1" sgpt_json="$2" filepath="$3" dest_path="$4" action="$5" prev_dest="$6"
  local subject from date summary unsub reason dest
  subject=$(echo "$info_json" | jq -r '.subject')
  from=$(echo "$info_json" | jq -r '."from"')
  date=$(echo "$info_json" | jq -r '.date')
  summary=$(echo "$sgpt_json" | jq -r '.summary')
  unsub=$(echo "$sgpt_json" | jq -r '.unsubscribe')
  reason=$(echo "$sgpt_json" | jq -r '.reason')
  dest=$(echo "$sgpt_json" | jq -r '.destination')
  cat <<ENTRY | tee -a "$MAIN_LOG"
## $subject
- mailbox: $MAILBOX_LABEL
- from: $from
- date: $date
- summary: $summary
- unsubscribe: $unsub
- decision: $dest ($reason)
$( [ -n "$prev_dest" ] && echo "- prev_decision: $prev_dest" )
- action: $action
ENTRY
}

move_email() {
  local src="$1" dest_dir="$2"
  mkdir -p "$dest_dir"
  mv "$src" "$dest_dir/"
  echo "mv $src -> $dest_dir/"
}

find_prev_destinations() {
  local filepath="$1"
  local fname
  fname=$(basename "$filepath")
  # all logged destinations for this filename (unique, ordered)
  grep -F "- action: mv " "$LOG_DIR"/email-sort-*.md 2>/dev/null | grep -F "$fname" | sed 's/.*-> \(.*\)\/$/\1/' | awk '!seen[$0]++' || true
}

process_file() {
  local mailbox="$1" sub="$2" file="$3"
  local info_json sgpt_json dest_key dest_rel dest_dir subfolder
  info_json=$(extract_email_json "$file")
  prev_dest_label=""
  corrections_block=""
  prev_dests=()
  allowed_keys="archiv_agb, archiv_bezahlt, freitag, loeschen, welcome, system, kommunikation, newsletter, uncertain"

  if [[ "$sub" == sort_ai_correction/* ]]; then
    mapfile -t prev_dests < <(find_prev_destinations "$file")
    if [ "${#prev_dests[@]}" -gt 0 ]; then
      # build exclusion label with all previous destinations
      prev_list=$(printf '%s, ' "${prev_dests[@]}")
      prev_list=${prev_list%, }
      prev_dest_label="EXCLUDE previous destinations: $prev_list. If unsure, choose uncertain."
      # remove all previous destinations from allowed list
      for prev_dest in "${prev_dests[@]}"; do
        prev_rel=${prev_dest#"$DEST_BASE/$mailbox/"}
        for k in "${!DEST_MAP[@]}"; do
          if [ "${DEST_MAP[$k]}" = "$prev_rel" ]; then
            allowed_keys=$(echo "$allowed_keys" | sed "s/\b$k\b, *//; s/, *$k\b//")
          fi
        done
      done
    fi
    if [ -f "$CORRECTIONS_DB" ]; then
      corrections_block=$(cat "$CORRECTIONS_DB")
    fi
  fi
  sgpt_raw=$(call_sgpt "$info_json" "$prev_dest_label" "$corrections_block" "$allowed_keys") || {
    printf '[email_sort] sgpt failed for %s\n' "$file" >&2
    printf '%s' "$info_json" > "$TMP_DIR/$(basename "$file").info.json"
    return 1
  }
  sgpt_json=$(echo "$sgpt_raw" | sed 's/^```json//; s/^```//; s/```$//')
  if ! echo "$sgpt_json" | jq . >/dev/null 2>&1; then
    printf '[email_sort] sgpt returned invalid JSON for %s\n' "$file" >&2
    printf '%s' "$sgpt_raw" > "$TMP_DIR/$(basename "$file").sgpt.json"
    return 1
  fi
  dest_key=$(echo "$sgpt_json" | jq -r '.destination // "uncertain"')
  dest_rel="${DEST_MAP[$dest_key]}"
  dest_rel=${dest_rel:-INBOX.sort_ai_uncertain}
  case "$sub" in
    sort_ai_correction/cur) subfolder="cur" ;;
    new) subfolder="new" ;;
    cur) subfolder="cur" ;;
    *) subfolder="cur" ;;
  esac
  dest_dir="$DEST_BASE/$mailbox/$dest_rel/$subfolder"
  prev_dest=""
  if [[ "$sub" == sort_ai_correction/* ]]; then
    mapfile -t prev_dests < <(find_prev_destinations "$file")
    if [ "${#prev_dests[@]}" -gt 0 ]; then
      prev_dest=${prev_dests[-1]}
    fi
  fi
  action=$(move_email "$file" "$dest_dir")
  # store corrections only for correction pool (when previous decision existed)
  if [[ "$sub" == sort_ai_correction/* ]] && [ -n "$prev_dest" ]; then
    "$PYTHON_BIN" - <<'PY' "$CORRECTIONS_DB" "$info_json" "$prev_dest" "$dest_rel"
import json
import sys
from datetime import datetime

path = sys.argv[1]
info = json.loads(sys.argv[2])
prev_dest = sys.argv[3]
new_dest = sys.argv[4]

entry = {
  "ts": datetime.utcnow().isoformat() + "Z",
  "mailbox": "${MAILBOX_LABEL}",
  "from": info.get("from", ""),
  "subject": info.get("subject", ""),
  "snippet": info.get("body_snippet", "")[:400],
  "prev_destination": prev_dest,
  "corrected_destination": new_dest
}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY
  fi
  log_entry "$info_json" "$sgpt_json" "$file" "$dest_dir" "$action" "$prev_dest"
}

process_mailbox() {
  local mailbox="$1"
  MAILBOX_LABEL="$mailbox"
  load_account_config "$mailbox"
  local base_inbox="$DEST_BASE/$mailbox/INBOX"
  local base_dot="$DEST_BASE/$mailbox/INBOX.sort_ai_correction"

  # sort_ai_correction can be a dot-folder (INBOX.sort_ai_correction) or subfolder (INBOX/sort_ai_correction)
  local corr_base=""
  if [ -d "$base_dot" ]; then
    corr_base="$base_dot"
  elif [ -d "$base_inbox/sort_ai_correction" ]; then
    corr_base="$base_inbox/sort_ai_correction"
  fi

  # process correction mailbox first if present
  if [ -n "$corr_base" ]; then
    for sub in cur new; do
      local dir="$corr_base/$sub"
      [ -d "$dir" ] || continue
      for file in "$dir"/*; do
        [ -f "$file" ] || continue
        process_file "$mailbox" "sort_ai_correction/$sub" "$file"
      done
    done
  fi

  # normal INBOX paths
  for sub in new cur; do
    local dir="$base_inbox/$sub"
    [ -d "$dir" ] || continue
    for file in "$dir"/*; do
      [ -f "$file" ] || continue
      process_file "$mailbox" "$sub" "$file"
    done
  done
}

for mb in "${MAILBOXES[@]}"; do
  process_mailbox "$mb"
done

printf "\n## Final Counts\n" | tee -a "$MAIN_LOG"
for mb in "${MAILBOXES[@]}"; do
  # correction (dot folder preferred)
  corr_dot="$DEST_BASE/$mb/INBOX.sort_ai_correction"
  corr_sub="$DEST_BASE/$mb/INBOX/sort_ai_correction"
  for sub in cur new; do
    if [ -d "$corr_dot/$sub" ]; then
      dir="$corr_dot/$sub"
      label="INBOX.sort_ai_correction/$sub"
    else
      dir="$corr_sub/$sub"
      label="INBOX/sort_ai_correction/$sub"
    fi
    if [ -d "$dir" ]; then
      count=$(find "$dir" -type f 2>/dev/null | wc -l)
    else
      count=0
    fi
    printf -- "- %s %s: %s\n" "$mb" "$label" "$count" | tee -a "$MAIN_LOG"
  done

  for sub in new cur; do
    dir="$DEST_BASE/$mb/INBOX/$sub"
    if [ -d "$dir" ]; then
      count=$(find "$dir" -type f 2>/dev/null | wc -l)
    else
      count=0
    fi
    printf -- "- %s INBOX/%s: %s\n" "$mb" "$sub" "$count" | tee -a "$MAIN_LOG"
  done
done

printf "\n## OfflineIMAP\n" | tee -a "$MAIN_LOG"
OFFLINEIMAP_BIN=""
if [ -x "/opt/venv/bin/offlineimap" ]; then
  OFFLINEIMAP_BIN="/opt/venv/bin/offlineimap"
elif [ -x "/opt/venv/bin/offlineimap3" ]; then
  OFFLINEIMAP_BIN="/opt/venv/bin/offlineimap3"
elif command -v offlineimap >/dev/null 2>&1; then
  OFFLINEIMAP_BIN="offlineimap"
elif command -v offlineimap3 >/dev/null 2>&1; then
  OFFLINEIMAP_BIN="offlineimap3"
fi

if [ -z "$OFFLINEIMAP_BIN" ]; then
  echo "[email_sort] offlineimap binary not found (expected offlineimap or offlineimap3)." >&2
  exit 127
fi

if [ "$SKIP_OFFLINEIMAP" != "true" ]; then
  (cd "$BASE_DIR" && FLAG=true "$OFFLINEIMAP_BIN" -c "$CONFIG_BASE/offlineimaprc" -o -a "${MAILBOXES[0]}") | tee -a "$MAIN_LOG"
else
  echo "[email_sort] offlineimap skipped (--no-offlineimap)." | tee -a "$MAIN_LOG"
fi

if [ "$PDF_ENABLED" = "true" ]; then
  PDF_OUT="$BASE_DIR/ZEROINBOX/email-sort-${TS}.pdf"
  "$PYTHON_BIN" - "$MAIN_LOG" "$PDF_OUT" <<'PYDOC'
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

log_path, pdf_path = sys.argv[1:]
lines = Path(log_path).read_text().splitlines()

c = canvas.Canvas(pdf_path, pagesize=A4)
width, height = A4
margin = 18 * mm
line_height = 6 * mm
y_pos = height - margin
c.setTitle("ZeroInbox Report")

header_font = ("Helvetica-Bold", 14)
subheader_font = ("Helvetica-Bold", 11)
body_font = ("Helvetica", 10)

max_width = width - 2 * margin

def ensure_space():
    global y_pos
    if y_pos < margin:
        c.showPage()
        y_pos = height - margin

def draw_line(text, font_tuple, color=colors.black):
    global y_pos
    font_name, font_size = font_tuple
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    content = text.strip()
    while content:
        ensure_space()
        split = len(content)
        while c.stringWidth(content[:split]) > max_width and split > 1:
            split -= 1
        c.drawString(margin, y_pos, content[:split])
        content = content[split:].lstrip()
        y_pos -= line_height

def add_gap(mult=1):
    global y_pos
    y_pos -= line_height * mult

for raw in lines:
    line = raw.rstrip()
    if not line:
        add_gap()
        continue
    if line.startswith('# '):
        add_gap(1.5)
        draw_line(line[2:], header_font)
        add_gap(0.5)
        continue
    if line.startswith('## '):
        add_gap(0.8)
        draw_line(line[3:], subheader_font, colors.darkblue)
        continue
    if line.startswith('- decision:'):
        draw_line(line, subheader_font, colors.darkred)
        continue
    if line.startswith('- '):
        draw_line(line, body_font)
        continue
    draw_line(line, body_font)

c.save()
PYDOC
else
  echo "[email_sort] PDF generation disabled (--pdf=false)." | tee -a "$MAIN_LOG"
fi
