# TOOLS.md - Serbia

## Code Execution via HIGHIQ.sh

For ALL coding tasks — reading files, writing files, editing code, running commands — use the `exec` tool with HIGHIQ.sh:

```bash
/home/openclaw/bin/HIGHIQ.sh 'your prompt here'
```

HIGHIQ.sh wraps Claude Code with full tool access (Read, Write, Edit, Bash, Glob, Grep).
You send a natural language prompt, Claude Code figures out which tools to use.

### Rules

- ALWAYS use `/home/openclaw/bin/HIGHIQ.sh` with the full path
- NEVER use pty:true
- ONE prompt per call — be specific about what you want

### Examples

```bash
/home/openclaw/bin/HIGHIQ.sh 'Read /home/openclaw/airplane/concorde.md and show me its contents'
```

```bash
/home/openclaw/bin/HIGHIQ.sh 'Create ~/cars/chiron.md with a Bugatti Chiron in ASCII art'
```

```bash
/home/openclaw/bin/HIGHIQ.sh 'List all files in /home/openclaw/airplane/'
```
