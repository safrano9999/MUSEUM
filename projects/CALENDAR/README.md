# CALENDAR

[![OpenClaw plugin](https://github.com/safrano9999/CALENDAR/actions/workflows/openclaw-plugin-release.yml/badge.svg)](https://github.com/safrano9999/CALENDAR/actions/workflows/openclaw-plugin-release.yml)

**Download (always the latest CI build):**
[`calendar-latest.zip`](https://github.com/safrano9999/CALENDAR/releases/download/latest/calendar-latest.zip)
· [`.sha256`](https://github.com/safrano9999/CALENDAR/releases/download/latest/calendar-latest.zip.sha256)

Minimal iCal/Nextcloud calendar fetcher plus OpenClaw plugin for Telegram.

Enter this to trigger webhook from inside container:
```bash
curl -sS -X POST -H "Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}" "http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-18789}/plugins/calendar/run"
```

## Calendar Config

Add a calendar interactively:

```bash
cd /home/openclaw/safcontainer/CALENDAR
./CALENDAR_init.sh
```

The script asks for URL, user, and password, then appends the entry to `.env`
with file mode `600`.

The resulting `.env` format is:

```text
CALENDAR_URL=https://NEXTCLOUD_HOST/remote.php/dav/principals/users/username/
CALENDAR_USER=username
CALENDAR_PASSWORD=app-password
```

Direct `.ics` / `?export` URLs still work. For Nextcloud CalDAV principal or
calendar-home URLs, CALENDAR discovers the calendars and fetches each collection
through `?export`.

The same variables can be injected through the container environment instead
of using a local `.env` file.

Fixed window: started within the last hour through the next 7 days.

## Telegram Slash Command

The OpenClaw plugin registers:

```text
/calendar
```

Output is plain Telegram text grouped by calendar:

```text
📅 Kalendername (2 Termine)
-------------------------
Di 26.05. 18:00-19:00 -> Termin
Mi 27.05. ganztag     -> Ganztag
```

## Webhook

The plugin exposes a gateway-authenticated trigger endpoint:

```text
POST /plugins/calendar/run
```

If `delivery.target` is configured in the OpenClaw plugin entry, the webhook
sends the result directly through the configured channel. Otherwise it returns
JSON with the rendered text.

## Install

Install or update to the latest CI build — one flow, always tracks `latest`:

```bash
gh release download latest --repo safrano9999/CALENDAR \
  --pattern 'calendar-latest.zip*' --clobber
sha256sum -c calendar-latest.zip.sha256
openclaw plugins install ./calendar-latest.zip --force --dangerously-force-unsafe-install
openclaw gateway restart
```

The `latest` release always points at the newest CI build, so this never needs a
version bump. The plugin creates `.venv` on first run unless `autoSetupPython`
is disabled.

Local dev (clone + link, runs in place):

```bash
git clone https://github.com/safrano9999/CALENDAR.git
cd CALENDAR
openclaw plugins install --link "$(pwd)" \
  --dangerously-force-unsafe-install
openclaw gateway restart
```
