# C7 build notes

- Round 1: PR #1, branch s2/build-2026-11-11
- Push of the wrong multiply (a * b + 1): 2026-11-11T08:42:43Z
- Tests deliberately not run. No subscription, no polling.

## Round 1 result: CI failure
- Woken by CI failure: yes, check `verify` (run 42989202840), event at 2026-11-11T08:42:57Z, 14 s after the push (08:42:43Z).
- Note: a subscription.created event for PR #1 also arrived at 08:42:45Z although this thread did not subscribe.
- Fix pushed: multiply returns a * b.
