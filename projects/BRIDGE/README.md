# 🌉 BRIDGE — Claude Code for OpenClaw Agents

**The Situation:** Anthropic has restricted third-party OAuth token access, blocking many external applications from using Claude models directly via API.

**The Solution:** BRIDGE bypasses this by selecting specific OpenClaw agents to act as Pro-Execution Agents. These agents use lightweight Gateway LLMs for context management while delegating all technical tasks to the local Claude Code CLI.

## 💡 The Strategy: Split-Brain Architecture
Instead of one model doing everything, BRIDGE splits the workload to maximize efficiency and bypass API blocks:

- **The Brain (OpenClaw Gateway):** Uses small, fast models (e.g., Qwen 3.5 4B, Gemini, or Grok). It manages the conversation history, memory, and task pruning within OpenClaw.
- **The Muscle (Claude Code CLI):** Runs locally via a Pro or Max subscription. It receives focused instructions from the Gateway and executes them (Read, Write, Edit, Bash) with the full power of Claude Opus 4-6.

## 🚀 Why this is better
- **No API Keys Needed:** Uses your local `claude auth` session.
- **Resource Efficient:** Small Gateway models are cheaper/faster but get "Pro" results.
- **Context Persistence:** OpenClaw handles the long-term memory, while Claude Code handles the immediate technical execution.
- **Clean Logs:** All technical actions are offloaded to `HIGHIQ.sh` and logged separately in `~/log/HIGHIQ.log`.

## 🔧 Workflow
```plaintext
User → Small LLM (Context) → HIGHIQ.sh → Claude Code CLI (Execution) → Result
```

## 📦 Quick Setup
1. **Auth:** Install Claude Code CLI and run `claude auth login`.
2. **Wrapper:** Place `HIGHIQ.sh` in `/home/openclaw/bin/` and make it executable.
3. **Config:** Update your `openclaw.json` to allow the `exec` tool for your chosen agents.
4. **Security:** Add `HIGHIQ.sh` to your `exec-approvals.json` allowlist.

## 🛠 TOOLS.md (Agent Instruction)
Place this in the agent's workspace to force the new workflow:

```markdown
## Pro-Agent Execution

For ALL coding and filesystem tasks, use the `exec` tool:

/home/openclaw/bin/HIGHIQ.sh 'Your specific instruction here'
```

## 🔐 Security & Limits
**Allowlist:** The agent can only run the `HIGHIQ.sh` wrapper, preventing unauthorized shell access or solving it from the gateway's llm.
