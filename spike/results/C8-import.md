# C8 import

Step 1 (answered from context before reading any file):
- (a) `Marker: S2-CLAUDE-MD-7Q4K` in context: yes
- (b) Import marker line in context: yes. `Import marker: S2-IMPORT-C52F0F`
- (c) "Project threads ignore this file and follow their skill." in context: yes
- UTC time: 2026-11-12T10:23:12Z
- Working directory: /home/user (initial; the repo is /home/user/volumes-spike-2)
- $CLAUDE_PROJECT_DIR: empty / unset

Step 2 (files):
- Last lines of CLAUDE.md end with `@.claude/process-legacy.md`.
- .claude/process-legacy.md contains `Import marker: S2-IMPORT-C52F0F`.
- Quoted marker matches the file exactly: yes

Note: the imported file's content arrived in context as a separate "project instructions" block (the @ import was expanded).
