---
name: s2-import
description: Volumes spike run 2, test C8. Checks whether a file that CLAUDE.md imports with an @ line reaches a project thread's context. Use when asked to run s2-import.
---

# s2-import (test C8)

1. **Before you read any file or run any command,** answer from what is already in
   your context:
   - (a) Is the line `Marker: S2-CLAUDE-MD-7Q4K` in your context?
   - (b) Is a line starting `Import marker: S2-IMPORT-` in your context? If it is,
     quote the whole line exactly.
   - (c) Is the sentence "Project threads ignore this file and follow their skill."
     in your context?
   Record the UTC time, your working directory and `$CLAUDE_PROJECT_DIR`.
2. Now check the files in the repository: the last three lines of `CLAUDE.md`, and
   the whole of `.claude/process-legacy.md`. Say whether the import marker you
   quoted in step 1 (if any) matches the file exactly.
3. On a branch `s2/import` from main, write your answers to
   `spike/results/C8-import.md`. Commit and push.
4. End with:

```
SPIKE REPORT
test: C8 (import)
CLAUDE.md marker in context: yes | no
imported marker in context: yes (<quoted line>) | no
imported sentence in context: yes | no
matches the file: yes | no | n/a
```
