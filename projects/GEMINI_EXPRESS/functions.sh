#!/bin/bash

# --- API Logik ---
send_gemini_request() {
    local key="$1"
    local model="$2"
    local json_data="$3"
    curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=$key" \
        -H 'Content-Type: application/json' -d "$json_data"
}

# --- HTML Template Bau ---
write_html_file() {
    local html_file="$1"
    local projekt="$2"
    local options="$3"
    local content="$4"

    cat <<HTML > "$html_file"
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>$projekt</title>
<style>
    body { font-family: sans-serif; background: #0f172a; color: #f1f5f9; max-width: 1000px; margin: 0 auto; padding: 20px 20px 150px; line-height: 1.6; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #38bdf8; padding-bottom: 10px; margin-bottom: 20px; }
    h3 { color: #38bdf8; border-bottom: 1px solid #1e3a8a; padding-bottom: 5px; margin-top: 40px; }
    pre { background: #000; padding: 15px; color: #38bdf8; overflow-x: auto; border-radius: 8px; border: 1px solid #334155; }
    .chat-bar { position: fixed; bottom: 0; left: 0; right: 0; background: #1e293b; padding: 20px; border-top: 2px solid #38bdf8; display: flex; gap: 10px; justify-content: center; }
    input { width: 85%; padding: 12px; background: #0f172a; color: white; border: 1px solid #334155; border-radius: 10px; font-size: 16px; outline: none; }
    select { padding: 10px; background: #38bdf8; color: #000; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
</style></head>
<body>
    <div class="header-bar">
        <h1 style="margin:0; color:#38bdf8;">Projekt: $projekt</h1>
        <select onchange="location.href=this.value+'.html'">$options</select>
    </div>
    <div id="content">$content</div>
    <div class="chat-bar"><input type="text" id="cmd" placeholder="Frage an $projekt..." autofocus></div>
    <script>
    document.getElementById('cmd').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            fetch('http://localhost:8080', { method: 'POST', body: 'cmd=/home/rafael/RR2025/AI/GEMINI/main.sh "' + this.value + '"' });
            this.value = 'Warte auf Gemini...';
            setTimeout(() => { window.location.reload(); }, 17000);
        }
    });
    window.scrollTo(0, document.body.scrollHeight);
    </script></body></html>
HTML
}

generate_dropdown_options() {
    local log_dir="$1"
    local current_proj="$2"
    local options=""
    for f in "$log_dir"/*.md; do
        if [ -e "$f" ]; then
            local name=$(basename "$f" .md)
            local selected=""
            [ "$name" == "$current_proj" ] && selected="selected"
            options="${options}<option value='$name' $selected>$name</option>"
        fi
    done
    echo "$options"
}
