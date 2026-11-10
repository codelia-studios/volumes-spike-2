---
name: s2-chain
description: Volumes spike run 2, test C4. Checks whether a thread can start another thread itself, and whether a message from a thread makes the coordinator act. Use when asked to run s2-chain.
---

# s2-chain (test C4)

Your task says **parent** or **child**. The parent starts at most one thread and
sends at most one message. The child starts nothing and sends nothing.

## Parent

1. Record the UTC time. List, names only and with their server prefix, the tools
   you have that can (a) start a new session or thread, (b) send a message to
   another session, (c) find this project's coordinator session.
2. **Start a thread.** If you have a tool from (a), call it once to start one
   thread whose task is exactly: "Run the s2-chain skill as the child." Prefer a
   tool that starts it inside this project. Record the tool, its arguments and its
   result (an id or a link). If it's refused or asks for approval, record that
   exactly. Try a second tool from (a) at most once.
3. **Message the coordinator.** If you can find the coordinator's session (c) and
   send it a message (b), send exactly: "CHAIN PING from the s2-chain thread.
   Reply in the project conversation with: CHAIN PING SEEN." Record the tools you
   used and their results.
4. On a branch `s2/chain` from main, write the notes to
   `spike/results/C4-chain.md`. Commit and push. End with:

```
SPIKE REPORT
test: C4 (chain), parent
start-a-thread tool: <name | none>; result: <started <id or link> | refused: <message> | not tried>
message-the-coordinator tool: <name | none>; result: <sent | refused: <message> | not tried>
```

## Child

1. Record the UTC time and the exact text of the task that started you. Say
   whether you can see project context (project instructions) in your context.
2. On a branch `s2/chain-child` from main, write
   `spike/results/C4-chain-child.md` with those three things. Commit and push.
3. End with:

```
SPIKE REPORT
test: C4 (chain), child
started at: <UTC time>
started by: <task text>
project context: yes | no
```
