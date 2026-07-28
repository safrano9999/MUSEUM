# Every Project We Develop

## Development Goal

This is an open-source project for GitHub. All code must be deployable by any user — not just tailored to our local setup. Think portable, documented, and self-contained.

## Python

- Use `venv` for Python dependencies
- Include `requirements.txt`
- Never hardcode paths, tokens, or user-specific config

## Deployability

The full workflow — `git clone` → setup → run — must work cleanly for any user on a fresh system. No leftover state, no personal data, no hardcoded names or usernames in plaintext. Every commit should be deployable. Test the flow mentally: would a stranger be able to `git clone` and get this running without editing code?

## Working Style

Don't build until you're confident the user has communicated 100% of what they want. The user has clear visions of how things should work — don't invent too much on your own. Ask, listen, confirm. Building the wrong thing costs time and tokens. When in doubt: keep asking, don't start coding.
