# Vikunja MCP

Combined container with the official Vikunja 2.6.0 binary,
`democratize-technology/vikunja-mcp` 0.2.2 and Supergateway 4.1.0.

- Vikunja Web/API: port `3456`
- Streamable HTTP MCP: `http://vikunja-mcp:8000/mcp`
- MCP health: `http://vikunja-mcp:8000/healthz`
- Public WebUI in this deployment: `https://ucore.tailb13f39.ts.net:2105/`

The MCP endpoint requires `Authorization: Bearer <Vikunja API token>`. Each
MCP session gets its own stdio child and token; no global API token is stored in
the container environment. The same bearer is required for every request in the
session.

Container builds and pushes run only in GitHub Actions. For deployment, first
run `sudo podman-smart1.sh --update`, then run `./setup.sh` as the target user.
The setup script only renders and starts the pinned image already present in the
user's Podman store.

## Verified updates

The reviewed MCP source remains `a42e1c2a3bd2b694e79a944fba5153970157b19d`
(version 0.2.2). GitHub's latest release is the older 0.2.0; the update policy
preserves this newer source until a later stable release advances it. Existing
source checksum guards and the task/team compatibility patches remain enabled.

GitHub Actions tests the built image against a disposable SQLite database:
MCP authentication, team field preservation, username-based membership changes,
idempotent admin updates, bulk task dates/repeats, and listing all tasks.
Only a successful candidate may become `latest`. The tests never use production
credentials, databases or volumes.
