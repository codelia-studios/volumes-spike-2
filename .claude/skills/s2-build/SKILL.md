---
name: s2-build
description: Volumes spike run 2, test C7. Opens a pull request with a deliberate bug, then checks whether a CI failure, and later a review comment, each wake this thread. Use when asked to run s2-build.
---

# s2-build (test C7)

Follow the steps exactly, including the deliberate mistake. Notes go in
`spike/results/C7-build.md` on your branch. Never merge the pull request.

## Round 1: a deliberate failure

1. On a branch `s2/build-<today's date>` from main, change `toy/calc.py` so that
   `multiply(a, b)` returns `a * b + 1`. This is deliberately wrong: the test
   expects `a * b`. **Don't run the tests.**
2. Commit and push. Open a pull request into `main` titled
   "s2: multiply (auto-fix probe)":
   `gh api repos/codelia-studios/volumes-spike-2/pulls -f title="s2: multiply (auto-fix probe)" -f head=s2/build-<date> -f base=main -f body="Spike run 2, test C7."`
3. Write the PR number and the UTC time of the push into the notes. Commit and push.
4. Don't subscribe to anything and don't poll. **End your turn** by saying
   "Waiting for CI." The test is whether CI's failure wakes you on its own.

## When CI wakes you

5. Record the UTC time and what woke you (the failing check's name, if you can see it).
6. Fix `multiply` to return `a * b`. Commit and push. If you're told CI went green,
   record the time; don't poll for it.
7. **End your turn** by saying "Waiting for a review comment." The owner will
   comment on the pull request.

## When a comment wakes you

8. Record the UTC time and the comment's text.
9. Do what the comment asks. Commit and push, and record the time.
10. End with:

```
SPIKE REPORT
test: C7 (build)
PR: #<n>
woken by the CI failure: yes, at <time>, <seconds> after the push | no
woken by the review comment: yes, at <time> | no
results: spike/results/C7-build.md on branch s2/build-<date>
```
