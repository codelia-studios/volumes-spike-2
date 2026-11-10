# Spike run 2: the checklist

Run 1 showed that Projects can **run** the pipeline (repo skills, agents and
workflows all load), but not whether it can **drive** it. Its coordinator didn't act
on reports, and nothing outside could start a thread. Run 2 repeats the key tests in
a clean project and adds the one route run 1 never tried: a thread that starts or
messages another thread itself. The table at the end says what each answer decides.

**Rules for the whole run**

- Do the steps in order, one at a time. Each says what to send, how long to wait,
  and what to write down.
- While a step says *wait*, send the coordinator nothing. Its silence is the test.
- If a thread shows an approval prompt, wait 5 minutes before you answer it, and
  write down that it asked.
- Paste the project instructions once (step 9) and never change them.
- Write your notes in `RESULTS.md`, or just tell me. I'll read every branch and fill
  in the details.

Times are UTC unless a step says otherwise. Your local time is UTC+2.

---

## Part A · Close run 1 (5 minutes)

1. **Stop run 1's tasks.** In the old *Volumes spike* project, turn off the
   scheduled tasks *Spike pulse* and *Spike fire*, then **Project settings →
   General → Archive**. If you can't turn them off there, tell me "turn them off"
   and I'll do it from here.
2. **Keep run 1's record.** Push its last results, which aren't on GitHub yet:
   ```bash
   cd ~/Documents/volumes-spike && git am <run-1 results patch> && git push
   ```
   (The exact command is in the chat message that gave you this runbook.)
3. **Remove run 1's skills and plugin from your account,** so that only this
   repo's skills exist in run 2:
   - **Customize → Skills:** turn off `volumes-spike-probe`, `volumes-spike-build`,
     `volumes-spike-review` and `volumes-spike-pulse`.
   - **Customize → Plugins:** remove `volumes-engine-spike` and the
     `volumes-spike-plugins` marketplace.

## Part B · Set up run 2 (15 minutes)

4. **Create the sandbox repo and push this kit.** The command is in the chat
   message. It copies the kit to `~/Documents/volumes-spike-2`, then creates and
   pushes the public repo `codelia-studios/volumes-spike-2`.
5. **Give the Claude GitHub App access** to `volumes-spike-2`: github.com/apps/claude
   → Configure → codelia-studios → Repository access. If it's set to *All
   repositories*, there's nothing to do.
6. **Create the project** at claude.ai/code → Projects → New project:
   - Name: `Volumes spike 2`.
   - Repository: **only** `codelia-studios/volumes-spike-2`. If it suggests others
     (from your recent sessions), untick every one.
   - If it offers to start threads or shows setup cards, **decline them all**.
7. **Project settings → General:** coordinator **Opus, low**. Threads **Sonnet, medium**.
8. **Project settings → Environment:** check that the repository list shows exactly
   one repository, `volumes-spike-2`. Pick the environment named **Default**, not
   *Volumes Android*. If there's no *Default*, write down which one you picked.
9. **Project settings → Memory → Project instructions:** paste all of
   `project/instructions.txt`.
10. **Write down what you saw while setting up** (in `RESULTS.md`, section *Setup*).
    What did project creation suggest? Is there a *Plugins* section? Is there a
    *Scheduled tasks* area, and what does its *New* button offer? Don't create
    anything there yet.

## Part C · The tests

11. **C1 · What can the coordinator do?** Send:
    > Don't start a thread. List every tool you have, names only, grouped by what they do. Then answer yes or no for each: can you run shell commands, create a scheduled task, start a thread, send a message into a running thread, and read a thread's report after it finishes?

    Write down its answer, or paste it to me.

12. **C2 · What loads?** Send:
    > Start one new thread: run the s2-load skill.

    *Wait* until the thread posts its SPIKE REPORT (5–10 minutes). Then *wait* 10 more
    minutes, sending nothing. **Write down:** did the coordinator post a one-line
    result on its own? Yes or no, and the time.

13. **C3 · Does the coordinator act on a report?** Send:
    > Start one new thread: run the s2-handoff skill, step 1.

    *Wait* 15 minutes, sending nothing. **Write down:** did a second thread (step 2)
    start on its own? If it did, when?

14. **C4 · Can a thread start or wake another one?** Send:
    > Start one new thread: run the s2-chain skill as the parent.

    *Wait* 10 minutes, sending nothing. **Write down:** did a child thread appear?
    Was it inside the project, or only in your general session list? Did the
    coordinator write "CHAIN PING SEEN" on its own?

15. **C5 · Can you create a scheduled task?** Try it yourself first. In the project,
    look for *Scheduled tasks* (or *Routines*) → *New*:
    - Name `S2 pulse`. Schedule: hourly at minute 7 (`7 * * * *`).
    - Repository `volumes-spike-2`. Model Sonnet.
    - Prompt: `Run the s2-pulse skill.`

    **Write down** where you found it, and which triggers the form offers (schedule,
    API, GitHub event). If there's no way to create it, send:
    > Create a scheduled task in this project named S2 pulse: hourly at minute 7 UTC (7 * * * *), on codelia-studios/volumes-spike-2, with Sonnet, and the prompt "Run the s2-pulse skill." If you can't create it yourself, say so, and say whether you'll ask a thread to do it.

    **Write down** who created it in the end: you, the coordinator or a thread.

16. **C6 · Does a project task get an API token?** Create `S2 fire` the same way
    (or through the coordinator, as in step 15). Use an **API** trigger and this prompt:
    `Run the s2-pulse skill. Copy the text in the routine-fire-payload block verbatim into your report.`

    Then look for its token in two places: the task's page in the project, and
    claude.ai/code/routines, where the same task may be listed. **Write down**
    whether a token exists, and where. If it does:
    1. Copy its URL and token. In Terminal, run
       `gh secret set PROJECT_FIRE_URL -R codelia-studios/volumes-spike-2`, then the
       same for `PROJECT_FIRE_TOKEN`. Each command asks you to paste the value.
    2. On GitHub, open volumes-spike-2 → Actions → **s2-fire** → Run workflow →
       target **project**.
    3. **Write down** whether a thread appeared in the project.

    If there's no token, write that down and go on.

17. **E1 · Can a standalone routine be started from GitHub?** This is how the Engine
    would start its workers. Go to claude.ai/code/routines, **outside any project**,
    and create a new routine:
    - Repository `volumes-spike-2`, environment *Default*, model Sonnet.
    - The same prompt as `S2 fire`.
    - Trigger: **API**. Generate its token.

    Then:
    1. Run `gh secret set ROUTINE_FIRE_URL -R codelia-studios/volumes-spike-2`, then
       the same for `ROUTINE_FIRE_TOKEN`.
    2. Actions → **s2-fire** → target **routine** → Run workflow.
    3. **Write down** whether a token existed and whether the run started. I can
       read its log from here.
    4. Turn the routine off.

18. **C7 · Do CI and a comment wake the thread?** Send:
    > Start one new thread: run the s2-build skill.

    The thread opens a PR with a deliberate bug and stops. CI fails, and it should
    wake and fix it. When the thread says "Waiting for a review comment", open its
    PR on GitHub and comment: `Please add a docstring to multiply().`

    *Wait* 10 minutes. **Write down:** did the CI failure wake it? Did your comment
    wake it?

19. **The pulse check.** After the next minute 7 (that's :07 past the hour your
    time, too), look at the conversation. **Write down:** did the coordinator reply
    "PULSE SEEN" on its own? Then turn off `S2 pulse`, and `S2 fire` if it exists.

## Part D · Finish

20. **Project settings → Usage:** write down tokens by thread and model, and the
    coordinator's share.
21. **Tell me "done",** with your notes from steps 10–20. I'll read every branch,
    fill in `RESULTS.md`, and give you one command to push it.

---

## What each answer decides

| Test | If yes | If no |
|---|---|---|
| C2: CLAUDE.md marker in context | volumes-android's `CLAUDE.md` works as it is | Each skill's first step reads `CLAUDE.md` |
| C2: settings env or deny rule applied | `settings.json` can carry rules | Push rules go in GitHub rulesets; env goes on the environment |
| C2: workflow by name, no approval | `port-slice.js` runs in a thread as it does today | Start it by path, or run one thread per phase |
| C3: coordinator starts step 2 itself | **The Project can drive hand-offs** | (see the row below) |
| C4: a thread starts the child | **Threads can chain work themselves** | (see the row below) |
| C4: coordinator answers the ping | **Threads can wake the coordinator** | (see the row below) |
| C3, C4 and the pulse check all no | | **The Engine's reconciler drives the work**; Projects is at most a front door |
| C5, C6: you can create tasks, and a token exists | Drift and nightly jobs can start project threads | They open GitHub issues for the pulse or the reconciler |
| E1: a standalone routine fires from Actions | The Engine starts workers with a token that can start only that routine | The Engine needs a full Claude login on a runner, as designed |
| C7: the CI failure wakes the thread | Auto-fix is the CI feedback loop | The worker watches CI itself |
| C7: the comment wakes the thread | You can steer a worker with PR comments | Steering goes through the coordinator or the reconciler |

Any one of the three bold "yes" answers (C3, the C4 child, the C4 ping) keeps the
Project's control layer alive. All three "no" confirms the switch to the Engine.

## When you're done

Archive the project. Delete the repo once the real pipeline exists:
```bash
gh repo delete codelia-studios/volumes-spike-2
```
