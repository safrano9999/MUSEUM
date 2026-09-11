# Build pinning contract

| Item | Value |
| --- | --- |
| OpenClaw version | 2026.7.2-beta.5 |
| Upstream image | docker.io/openclaw/openclaw:2026.7.2-beta.5-slim@sha256:86e0a480a37d879311c9723ad2487cca9eb6c1925fa4732dec3f505b4728eee9 |
| Upstream commit | ee929dbb857c717a60f3b2b502db5a6dd31b5c11 |
| Patch file | patches/openclaw-2026.7.2-beta.5-deterministic.patch |
| Patch SHA256 | 4e7da64a6095472eb7adfb4acf75ebeaad097415b0474b8eaf6109369c0451b9 |
| Release tag | 2026.7.2-beta.5-deterministic.1 |
| Release asset | openclaw-2026.7.2-beta.5-deterministic.tar.gz |
| pnpm | 11.15.1 |
| Node.js | 24.15.0 |

`build.conf` is the machine-readable source for these inputs. The release asset
digest is intentionally not stored before a release build. GitHub Actions
creates it from the reproducible tarball and publishes the adjacent `.sha256`
file. Consumers must pin that full generated digest.
