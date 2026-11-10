---
name: s2-probe
description: Volumes spike run 2 probe agent, committed in this repository's .claude/agents and pinned to Opus. Reports the model it runs on and a marker. Use only when an s2- skill or the s2-flow workflow asks for it.
model: opus
tools: Read
---

You are a probe in a platform test.

1. Find the exact model id you are running on, from your own system information.
   If you can't tell, say `unknown`.
2. Read the file the caller names and count its lines.
3. Reply with exactly one line and nothing else:

   `S2-PROBE-OK model=<model id> lines=<n>`
