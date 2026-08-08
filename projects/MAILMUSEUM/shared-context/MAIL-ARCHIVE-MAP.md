# MAIL-ARCHIVE-MAP.md — Archive Structure Map

Fill this in during the first Archivist session.

---

## Sync Source

| Field | Value |
|-------|-------|
| IMAP Host | FILL_ME (e.g. imap.gmail.com) |
| Account Name | FILL_ME |
| offlineimap config | FILL_ME (path to .offlineimaprc) |

---

## Maildir Root

| Field | Value |
|-------|-------|
| Local path | FILL_ME (e.g. ~/maildir/mailmuseum/) |
| Disk usage estimate | FILL_ME |
| Created | FILL_ME (date of first sync) |

---

## Folder / Mailbox Structure

List all discovered mailboxes after first sync. Fill in during Archivist Phase 1.

| Folder | Message count | Notes |
|--------|---------------|-------|
| FILL_ME | FILL_ME | FILL_ME |

---

## Import Strategy

| Field | Value |
|-------|-------|
| Import method | FILL_ME (e.g. Python mailbox lib, custom parser) |
| Batch size | FILL_ME |
| Dedup key | osm_id / message_id |
| Estimated total emails | FILL_ME |
| Date range | FILL_ME (e.g. 2005–2025) |

---

## Known Caveats

Document any issues discovered during setup:

- FILL_ME

---

## Sync Status

| Field | Value |
|-------|-------|
| First sync completed | FILL_ME |
| Last sync | FILL_ME |
| Sync interval | FILL_ME (or manual) |
