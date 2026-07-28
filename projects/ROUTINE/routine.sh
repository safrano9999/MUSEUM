#!/bin/bash
# routine.sh — standalone terminal interface for the daily routine
#
# Usage:
#   ./routine.sh              — show today's checklist
#   ./routine.sh toggle <id>  — toggle item by ID
#   ./routine.sh reset        — uncheck all items for today

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Load DB creds from CLAWBRIDGE if present, fallback to local
if [ -f "$SCRIPT_DIR/../CLAWBRIDGE/.mysqlenv" ]; then
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/../CLAWBRIDGE/.mysqlenv"
elif [ -f "$SCRIPT_DIR/.mysqlenv" ]; then
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/.mysqlenv"
fi

DB_DRIVER="${DB_DRIVER:-mysql}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_NAME="${DB_NAME:-telegram_bot}"
DB_USER="${DB_USER:-botuser}"

if [ "$DB_DRIVER" = "pgsql" ]; then
    DB_PORT="${DB_PORT:-5432}"
else
    DB_PORT="${DB_PORT:-3306}"
fi

TODAY=$(date +%Y-%m-%d)

db() {
    if [ "$DB_DRIVER" = "pgsql" ]; then
        PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -tA -F $'\t' -c "$1" 2>/dev/null
    else
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -sNe "$1" 2>/dev/null
    fi
}

init_session() {
    for i in $(seq 1 15); do
        if [ "$DB_DRIVER" = "pgsql" ]; then
            db "INSERT INTO routine_log (session_date, item_id) VALUES ('$TODAY', $i) ON CONFLICT DO NOTHING;"
        else
            db "INSERT IGNORE INTO routine_log (session_date, item_id) VALUES ('$TODAY', $i);"
        fi
    done
}

show() {
    init_session
    local done_count total
    total=15
    done_count=$(db "SELECT COUNT(*) FROM routine_log WHERE session_date='$TODAY' AND checked_at IS NOT NULL;")

    echo ""
    echo "📋 Tagesroutine — $done_count/$total erledigt  ($TODAY)"
    echo "─────────────────────────────────────────"

    if [ "$DB_DRIVER" = "pgsql" ]; then
        db "SELECT ri.id, ri.label, CASE WHEN rl.checked_at IS NOT NULL THEN 1 ELSE 0 END
            FROM routine_items ri
            JOIN routine_log rl ON ri.id = rl.item_id AND rl.session_date = '$TODAY'
            ORDER BY ri.id;"
    else
        db "SELECT ri.id, ri.label, IF(rl.checked_at IS NOT NULL, 1, 0)
            FROM routine_items ri
            JOIN routine_log rl ON ri.id = rl.item_id AND rl.session_date = '$TODAY'
            ORDER BY ri.id;"
    fi | \
    while IFS=$'\t' read -r id label checked; do
        [ "$checked" = "1" ] && icon="✅" || icon="☐ "
        printf "  %s  [%2d] %s\n" "$icon" "$id" "$label"
    done

    echo ""
}

toggle() {
    local id="$1"
    local current
    if [ "$DB_DRIVER" = "pgsql" ]; then
        current=$(db "SELECT CASE WHEN checked_at IS NOT NULL THEN 1 ELSE 0 END FROM routine_log WHERE session_date='$TODAY' AND item_id=$id;")
    else
        current=$(db "SELECT IF(checked_at IS NOT NULL, 1, 0) FROM routine_log WHERE session_date='$TODAY' AND item_id=$id;")
    fi
    if [ "$current" = "1" ]; then
        db "UPDATE routine_log SET checked_at=NULL WHERE session_date='$TODAY' AND item_id=$id;"
        echo "☐  Item $id unchecked"
    else
        db "UPDATE routine_log SET checked_at=NOW() WHERE session_date='$TODAY' AND item_id=$id;"
        echo "✅ Item $id checked"
    fi
    show
}

reset_today() {
    db "UPDATE routine_log SET checked_at=NULL WHERE session_date='$TODAY';"
    echo "🔄 All items reset for $TODAY"
    show
}

case "${1:-show}" in
    show|"")   show ;;
    toggle)    [ -z "$2" ] && { echo "Usage: $0 toggle <id>"; exit 1; }; toggle "$2" ;;
    reset)     reset_today ;;
    *)         echo "Usage: $0 [show|toggle <id>|reset]"; exit 1 ;;
esac
