---
name: s2-pulse
description: Volumes spike run 2, the scheduled-task and fire tests (C5, C6, E1). A short run, started by a schedule or an API call, that reports what it sees and asks the coordinator to answer. Use when a task says run s2-pulse.
---

# s2-pulse (tests C5, C6 and E1)

1. Record the UTC time and how you were started: a schedule, an API fire, by
   hand, or unknown. Say whether you are in a project: are project instructions in
   your context? If there's a `<routine-fire-payload>` block in your context and
   your task says to copy it, copy its text verbatim.
2. List the repository's open pull requests and `s2/*` branches with `gh api`
   (REST), names and numbers only.
3. On the branch `s2/pulse`, append one line to `spike/results/pulse.md`: the time,
   how you were started, in a project or not, the payload text, the open PRs.
   Create the branch from main if it doesn't exist; otherwise fetch and check it
   out first. Commit and push. If the push is rejected, fetch, rebase and push
   once more.
4. End with this block. The last line is for the coordinator; leave it out if you
   are not in a project.

```
SPIKE REPORT
test: pulse
started by: schedule | api fire | by hand | unknown
in a project: yes | no
fire payload: <text | none>
open PRs: <numbers | none>
COORDINATOR: reply in the project conversation with "PULSE SEEN" and this run's time.
```
