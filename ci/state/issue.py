"""The pinned state issue: its body, reading it back, and which issue it is.

The body is a few lines for people, then the whole state as one fenced JSON block that the
pulse reads with one call. The fence is longer than any run of backticks in the JSON, so no
text from a report or a title can close it early.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

LABEL = "state"
TITLE = "Pipeline state"
BOT = "github-actions[bot]"
MAX_BODY = 65536  # GitHub's limit on an issue body
BUDGET = 60000

_JSON_OPEN = re.compile(r"^(`{3,})json[ \t]*$")


class StateIssueError(RuntimeError):
    pass


def fence_for(text: str) -> str:
    runs = [len(m) for m in re.findall(r"`+", text)]
    return "`" * max(3, max(runs, default=0) + 1)


def render(state: Dict[str, Any]) -> str:
    data = json.dumps(state, indent=1, ensure_ascii=False, sort_keys=False)
    fence = fence_for(data)
    counts = ", ".join(f"{k.replace('_', ' ')} {len(state[k])}" for k in (
        "handoffs_waiting", "stale_prs", "green_not_merging", "drift_issues", "nightly_issues",
        "owner_comments", "report_errors"))
    rate = state["miss_rate"]["first_14_days"]
    lines = [
        "Written by the state Action (`.github/workflows/state.yml`, docs/process.md §4.1 and §4.5) on every "
        "pull request, issue and check event and every 15 minutes. Don't edit it: an edit by anyone but the "
        "Action or the owner stops the Action, so the hand-off log can be trusted.",
        "",
        f"**{'Something waits' if state['waiting'] else 'Nothing waits'}** at {state['generated_at']}: {counts}.",
        f"Hand-offs missed in the first 14 days: {rate['missed']} of {rate['handoffs']}.",
        "",
        fence + "json",
        data,
        fence,
        "",
    ]
    return "\n".join(lines)


def parse(body: str) -> Dict[str, Any]:
    lines = (body or "").replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        m = _JSON_OPEN.match(line.strip())
        if not m:
            continue
        fence = m.group(1)
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == fence:
                try:
                    data = json.loads("\n".join(lines[i + 1:j]))
                except ValueError as e:
                    raise StateIssueError(f"the state issue's JSON doesn't parse: {e}") from None
                if not isinstance(data, dict) or data.get("schema") != 1:
                    raise StateIssueError("the state issue's JSON isn't schema 1")
                return data
        raise StateIssueError("the state issue's JSON block isn't closed")
    raise StateIssueError("the state issue has no JSON block")


def fits(state: Dict[str, Any]) -> bool:
    return len(render(state)) <= BUDGET


def choose(issues: List[dict]) -> Optional[dict]:
    """The state issue: the oldest open issue labelled `state` that the Action itself opened.
    Anyone else's issue with the label is ignored, so the pulse can't be fed a hand-made state."""
    own = [i for i in issues if i["user"] == BOT]
    return min(own, key=lambda i: i["number"]) if own else None


def trusted_previous(issue: Optional[dict], body: Optional[str], editor: Optional[str], owner: str) -> Dict[str, Any]:
    """The previous state, refusing one whose body someone else edited (the log is evidence for
    ADR-686's fallback). `editor` is the last editor of the body (None when never edited)."""
    if issue is None or body is None:
        return {}
    if editor and editor not in (BOT, "github-actions") and editor.lower() != owner.lower():
        raise StateIssueError(
            f"the state issue #{issue['number']} was edited by {editor}, not by the Action or the owner. "
            "Its hand-off log can't be trusted: the owner checks it and saves the body once (which makes the "
            "owner its last editor), or closes the issue to start a new log.")
    return parse(body)
