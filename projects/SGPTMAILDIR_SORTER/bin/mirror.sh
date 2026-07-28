#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR=${1:-"$BASE_PROJECT/Mail/gmail"}
ACCOUNT_NAME=${2:-""}

if [ -z "$ACCOUNT_NAME" ]; then
  ACCOUNT_NAME=$(basename "$BASE_DIR")
fi

OUT_JSON=${3:-"$BASE_PROJECT/mirror_dir_${ACCOUNT_NAME}.json"}

python3 - <<'PY' "$BASE_DIR" "$OUT_JSON" "$ACCOUNT_NAME"
import json
import sys
from pathlib import Path

base = Path(sys.argv[1]).expanduser().resolve()
out = Path(sys.argv[2]).expanduser().resolve()
account = sys.argv[3]

# load existing json if present
existing = {}
existing_list = []
if out.exists():
    data = json.loads(out.read_text())
    existing_list = data.get("folders", [])
    for f in existing_list:
        key = f.get("maildir_path")
        if key:
            existing[key] = f

folders = {k: v for k, v in existing.items()}

# maildir folder = directory that contains cur/new/tmp
for cur_dir in base.rglob('cur'):
    parent = cur_dir.parent
    if not (parent / 'new').is_dir() or not (parent / 'tmp').is_dir():
        continue
    rel = parent.relative_to(base).as_posix()

    # derive imap-like path for dot folders (INBOX.xxx -> INBOX/xxx)
    imap_path = rel
    if rel.startswith('INBOX.'):
        imap_path = 'INBOX/' + rel[len('INBOX.'):].replace('.', '/')
    elif rel.startswith('[Gmail].'):
        imap_path = '[Gmail]/' + rel[len('[Gmail].'):].replace('.', '/')

    folder_name = imap_path.split('/')[-1] if '/' in imap_path else imap_path

    if rel in folders:
        # keep existing, but ensure name/imap_path set
        folders[rel].setdefault("name", folder_name)
        folders[rel].setdefault("imap_path", imap_path)
        continue

    folders[rel] = {
        "name": folder_name,
        "maildir_path": rel,
        "imap_path": imap_path,
    }

try:
    root_rel = "../" + str(base.relative_to(out.parent))
except Exception:
    root_rel = str(base)

payload = {
    "account": account,
    "root": root_rel,
    "count": len(folders),
    "folders": sorted(folders.values(), key=lambda x: x.get("imap_path", ""))
}

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
print(f"Wrote {out} ({payload['count']} folders)")
PY
