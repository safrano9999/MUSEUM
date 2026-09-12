# hermes-ephemeral

`hermes-ephemeral` rebuilds Hermes' complete runtime configuration from the
current process environment. It never imports `openclaw-ephemeral`, never reads
or merges an old Hermes config, and never writes resolved credentials.

The repository is a rootfs contribution: everything below `image/runtime/`
can be overlaid directly on an image. The installed launcher is
`/usr/local/bin/hermes-ephemeral`; all Python implementation lives beside it in
`/usr/local/lib/hermes-ephemeral/hermes_ephemeral`.

## Runtime contract

The first OpenAI-v1 group is suffixless. Additional groups use `_2`, `_3`, and
so on; padded input such as `_02` is accepted as well:

```text
OPENAI_V1_PROVIDER=litellm
OPENAI_V1_URL=http://host.containers.internal
OPENAI_V1_PORT=4000
OPENAI_V1_KEY=...
OPENAI_V1_API_KEY_ALIAS=LITELLM_API_KEY
OPENAI_V1_STREAM=true
HERMES_MODEL=luna
```

Every active group is queried through its `/v1/models` endpoint. An optional
`OPENAI_V1_MODELS` value can provide a comma-separated or JSON fallback. The
generated provider config contains only the environment-variable name in
`key_env`, not the key value.

HTTP MCP servers use a suffixless first group and `_02`, `_03`, and later
groups:

```text
MCP_SERVER_NAME=calendar
MCP_SERVER_URL=http://nextcloud:48005/mcp
MCP_SERVER_BEARER=

MCP_SERVER_NAME_02=kachelmann
MCP_SERVER_URL_02=http://kachelmann:48006/mcp
MCP_SERVER_BEARER_02=...
```

Only a URL activates a group. The bearer is emitted as an environment
placeholder such as `Bearer ${MCP_SERVER_BEARER_02}`. Names are optional and
otherwise come from the URL hostname.

Paths follow Hermes' own runtime contract:

- state is always below `$HOME/.hermes`
- configuration is always `$HOME/.hermes/config.yaml`
- `HERMES_CONFIG_TEMPLATE`, optional
- `HERMES_BIN`, defaulting to the `hermes` found on `PATH`; its install prefix
  is used to discover `lib/hermes-agent/cli-config.yaml.example`

No Fedora path is embedded in the Python configuration logic.

## systemd order

`hermes-ephemeral.service` is a `Type=oneshot` unit with this order:

```text
persistainer.service
        │
        ├── optional active tailscale-up.service
        │
        ▼
hermes-ephemeral.service
        │
        ▼
hermes.service
```

The optional `Wants+After` edges pull initialization hooks and Tailscale into
the transaction when their units exist; condition-skipped units remain a clean
no-op. `hermes.service` must require the configurator, so an invalid or
unavailable provider configuration prevents the gateway from using an
incomplete file.

## Fedora CONTAINER integration points

The Core build integration has four explicit points:

1. Fetch `safrano9999/hermes-ephemeral` into Core's prepared vendor stage.
2. Overlay the checkout's `image/runtime/` onto the Core rootfs.
3. Remove Core's old `/usr/local/bin/hermes-ephemeral.py` and its
   `ExecStartPre`; make `hermes.service` use
   `Requires=hermes-ephemeral.service` and
   `After=hermes-ephemeral.service`.
4. Enable `hermes-ephemeral.service` together with `hermes.service` and merge
   this repository's `env.example`, `config.conf_example`, and
   `container.example` through the normal Example Chain. The matching
   `OPENAI_V1` and `MCP_SERVER` repeat groups are intentionally deduplicable.

The remote repository must be private before Core CI is pointed at it; the
build checkout therefore needs the same authenticated private-repository path
used by other private inputs.

## Tests

PyYAML is the only non-standard-library Python dependency.

```bash
PYTHONPATH=image/runtime/usr/local/lib/hermes-ephemeral \
  python3 -m unittest discover -s tests -v
```
