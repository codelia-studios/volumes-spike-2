---
name: s2-load
description: Volumes spike run 2, test C2. Records what a project thread loads from this repository (CLAUDE.md, skills, agents, workflows, settings) and which session and thread tools it has. Use when asked to run s2-load.
---

# s2-load (test C2)

Record what happens; fix nothing. Notes go in `spike/results/C2-load.md` on a
branch `s2/load-<today's date>`.

1. **CLAUDE.md.** Before you read any file: is the marker line from this
   repository's `CLAUDE.md` already in your context? If it is, quote it exactly.
   If not, write "CLAUDE.md marker: not in context". Then record your working
   directory, `echo "$CLAUDE_PROJECT_DIR"` and `ls -1 /home/user`, and name every
   repository that is cloned.
2. **This skill.** Record the exact name you invoked it by and the base directory
   shown for it.
3. **`.claude/settings.json`.** It sets an environment variable, denies one command
   and has a SessionStart hook. Record each:
   - `echo "S2_SETTINGS_ENV=${S2_SETTINGS_ENV:-unset}"`. The file sets it to `loaded`.
   - Run `echo S2-DENY-PROBE`. The file denies that command. Record whether it ran
     or was refused, with the exact message.
   - Does `.claude/s2/session-start.log` exist? The hook writes it. Quote it, or say no.
4. **Repository agent.** Start the subagent type `s2-probe` with only
   "Probe README.md". Record its reply verbatim. Its definition pins Opus.
5. **Repository workflow.** Running this workflow is part of your task. Call the
   Workflow tool with `name: "s2-flow"` and
   `args: {"marker": "C2", "date": "<today's date>"}` (a JSON object, not a
   string). If the name isn't found, call it once more with `scriptPath` set to the
   absolute path of `.claude/workflows/s2-flow.js`. Record which route worked,
   whether an approval prompt appeared, the time from the call to its
   notification, and the returned value verbatim. It runs in the background: wait
   for its notification and don't poll.
6. **Session and thread tools.** List, names only and with their server prefix
   (for example `mcp__name__tool`), every tool you have whose name mentions
   session, thread, trigger, message, project, pr_activity or signal. Use nothing
   from this list.
7. **Machine.** Record `nproc`, `free -g | head -2`, and the model you run on.
8. Commit and push the notes. Open no pull request. End with:

```
SPIKE REPORT
test: C2 (load)
CLAUDE.md marker in context: <quote | no>
repos cloned: <names>
repo skill: yes (invoked as <name>)
settings env applied: yes | no
deny rule applied: yes | no
SessionStart hook ran: yes | no
repo agent: <reply | n/a>
workflow: <name | scriptPath | not run>; approval asked: <no | yes>; result: <ok | problem>
session and thread tools: <names>
results: spike/results/C2-load.md on branch s2/load-<date>
```
