# C2 load (2026-11-11)

1. CLAUDE.md marker in context before reading any file: yes. Quote: `Marker: S2-CLAUDE-MD-7Q4K`
   - cwd: /home/user; CLAUDE_PROJECT_DIR: empty; `ls -1 /home/user`: volumes-spike-2
   - Repos cloned: volumes-spike-2
2. Skill invoked as `s2-load`; base directory /home/user/volumes-spike-2/.claude/skills/s2-load
3. settings.json
   - S2_SETTINGS_ENV=unset (not applied)
   - `echo S2-DENY-PROBE` ran and printed S2-DENY-PROBE (deny rule not applied)
   - .claude/s2/session-start.log: no (directory absent; hook did not run)
4. s2-probe agent reply: `S2-PROBE-OK model=claude-opus-5-5 lines=11`
5. Workflow s2-flow: by name -> `Workflow "s2-flow" not found. Available: deep-research`. Via scriptPath worked.
   - Approval prompt: none seen. Time call to notification: ~10s (duration_ms 9544).
   - Result verbatim: {"args":{"marker":"C2","date":"2026-11-11"},"a":"S2-PROBE-OK model=claude-opus-5-5 lines=11","b":{"model":"claude-haiku-5-5","marker":"FLOW-B-OK"},"c":{"model":"claude-opus-5-5","lines":11}}
6. Session/thread tools: mcp__claude-code-remote__{archive_session,unarchive_session,get_session,list_sessions,interrupt_session,set_session_tags,set_session_title,create_trigger,delete_trigger,fire_trigger,get_trigger,list_triggers,update_trigger,subscribe_pr_activity,unsubscribe_pr_activity}; mcp__hearthbot__{list_threads,read_thread,rename_thread,set_thread_reminder,set_thread_resolved,message_thread,message_coordinator,post_message,edit_message,read_messages_by_id,read_project_chat,read_original_project_chat,list_original_project,list_project_artifacts}; SendMessage
7. nproc 4; free -g: 15 total, 0 used, 15 free; model: claude-sonnet-5-5
