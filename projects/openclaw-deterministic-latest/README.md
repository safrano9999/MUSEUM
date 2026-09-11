# openclaw-deterministic-latest

Version-specific patch source for the moving OpenClaw lane. This repository does
not build or publish a container image. The downstream image keeps its own name;
"deterministic" identifies only this source patch and its release artifact.

## Exact target

- OpenClaw version: 2026.7.2-beta.5
- Upstream commit: ee929dbb857c717a60f3b2b502db5a6dd31b5c11
- Patch: patches/openclaw-2026.7.2-beta.5-deterministic.patch

The complete machine-readable build input is recorded in `build.conf`.

The patch adds the credential-free dummy/dummy and dummy/note models. Reply
claiming is centralized at runBeforeAgentReplyForTurn: plugins run first, then
the deterministic fallback. Embedded, CLI, and steer admissions receive the
same inbound text, media, location, and structured-context event fields.

## Apply locally

Check out the exact upstream commit, then run:

    ./scripts/apply-pinned-patch.sh /path/to/openclaw

The script refuses a different commit and verifies the checked-in patch checksum
before applying it.

## Release artifact

The GitHub Actions workflow checks out the exact upstream SHA, applies the patch,
runs the focused tests and full build, then packages the resulting top-level
dist/ directory reproducibly. Each dated release and the `latest` alias contain:

- openclaw-2026.7.2-beta.5-deterministic.patch
- openclaw-2026.7.2-beta.5-deterministic.patch.sha256
- openclaw-2026.7.2-beta.5-deterministic.tar.gz
- openclaw-2026.7.2-beta.5-deterministic.tar.gz.sha256

The downstream ephemeral image consumes the version-pinned or `latest` release
tag, the asset name, and the generated SHA256. The SHA256 value is taken from
the generated release checksum; no digest is guessed or shortened.

## Forward-port rule

Every upstream update is a new exact pin and a newly generated patch. The
workflow's git apply --check, focused tests, and build are the compatibility
gate. Never retarget this patch by changing only the version label.
