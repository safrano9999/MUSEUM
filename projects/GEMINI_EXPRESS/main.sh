#!/bin/bash
source /home/rafael/RR2025/AI/GEMINI/functions.sh

KEYS=("KEY_1" "KEY_2" "KEY_3" "KEY_4" "KEY_5")
MODELS=("gemini-3-flash-preview" "gemini-2.0-flash" "gemini-1.5-flash")
LOG_DIR="/home/rafael/RR2025/AI/GEMINI"
LAST_PROJ_FILE="$LOG_DIR/.last_project"

# 1. Projekt-Logik
PROMPT="$1"
if [ -n "$2" ]; then
    PROJEKT="$2"
    echo "$PROJEKT" > "$LAST_PROJ_FILE"
else
    PROJEKT=$(cat "$LAST_PROJ_FILE" 2>/dev/null || echo "default")
fi

LOG_FILE="$LOG_DIR/${PROJEKT}.md"
HTML_FILE="$LOG_DIR/${PROJEKT}.html"

# 2. API Abfrage (nur wenn Prompt da)
if [ -n "$PROMPT" ]; then
    echo "********************************************************************************"
    echo "PROJEKT: $PROJEKT | FRAGE: $PROMPT"
    echo "********************************************************************************"
    
    [ -f "$LOG_FILE" ] && sed -i 's/<[^>]*>//g' "$LOG_FILE"
    KONTEXT=$(tail -c 15000 "$LOG_FILE" 2>/dev/null)
    JSON_DATA=$(jq -n --arg ctx "$KONTEXT" --arg p "$PROMPT" '{contents: [{role: "user", parts: [{text: "Kontext:\n" + $ctx + "\n\nFrage: " + $p}]}]}')
    
    START_TIME=$(date +%s.%N)
    TEXT=""
    KEY_IDX=1
    for K in "${KEYS[@]}"; do
        for M in "${MODELS[@]}"; do
            echo "Key #$KEY_IDX | $M ..."
            RESPONSE=$(send_gemini_request "$K" "$M" "$JSON_DATA")
            TEXT=$(echo "$RESPONSE" | jq -r '.candidates[0].content.parts[0].text // empty' 2>/dev/null)
            if [ -n "$TEXT" ] && [ "$TEXT" != "null" ]; then
                AKTIVES_MODEL="$M"
                echo "✅ Erfolg!"
                break 2
            fi
        done
        ((KEY_IDX++))
    done

    if [ -n "$TEXT" ]; then
        DURATION=$(echo "scale=2; ($(date +%s.%N) - $START_TIME) / 1" | bc)
        echo -e "\n---\n### $(date '+%H:%M:%S')\n\`\`\`yaml\nModell: $AKTIVES_MODEL\nDauer: ${DURATION}s\nFrage: $PROMPT\n\`\`\`\n\n$TEXT\n" >> "$LOG_FILE"
    fi
fi

# 3. HTML & Dropdown regenerieren
OPTIONS=$(generate_dropdown_options "$LOG_DIR" "$PROJEKT")
CONTENT=$(pandoc -f markdown-metadata_blocks -t html "$LOG_FILE" 2>/dev/null || echo "<pre>$(cat "$LOG_FILE" 2>/dev/null)</pre>")

write_html_file "$HTML_FILE" "$PROJEKT" "$OPTIONS" "$CONTENT"

export DISPLAY=:0
xdg-open "$HTML_FILE" >/dev/null 2>&1 &
