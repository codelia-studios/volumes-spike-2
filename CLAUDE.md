# Volumes spike sandbox, run 2

A throwaway sandbox for testing how Claude Code Projects behave before the Volumes
Android port moves onto one. Nothing here ships.

Marker: S2-CLAUDE-MD-7Q4K

(The s2-load skill asks whether that marker line was in your context before you read
any file. That tests whether this file loads in a project thread.)

- Use `gh api` (REST) for GitHub. `gh pr` and `gh issue` use GraphQL, which the
  cloud GitHub proxy refuses.
- Never merge a pull request, never push to `main`, never force-push.
- Never touch any other repository.
- Results go under `spike/results/` on your own `s2/*` branch.
- The skills for this run are in `.claude/skills` and start with `s2-`. Follow the
  one your task names exactly, including deliberate mistakes. These are measurements.

@.claude/process-legacy.md
