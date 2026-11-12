#!/usr/bin/env python3
"""The state Action (docs/process.md §4.1, "State Action"): writes the state of the work as JSON
to one pinned issue, for the pulse, and logs every hand-off's pickup delay (§9).

Usage: ci/state/state.py --repo OWNER/NAME [--owner LOGIN] [--dry-run] [--github]
Needs GITHUB_TOKEN with issues: write, and read access to pull requests, checks and statuses.
STATE_MEASURE_SINCE (optional, ISO time) starts the miss-rate's first 14 days; otherwise the
log's own start (the Action's first run).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import github as gh_mod  # noqa: E402
import issue as issue_mod  # noqa: E402
import signals  # noqa: E402

ISSUE_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { issue(number: $number) { id body editor { login } isPinned } }
}
"""
PIN = "mutation($id: ID!) { pinIssue(input: {issueId: $id}) { issue { number } } }"


def owner_login(root: Path, given: str) -> str:
    if given:
        return given
    path = root / "ci" / "owner.txt"
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    raise SystemExit(f"{path}: no owner login")


def snapshot(gh: gh_mod.GitHub, owner: str, previous: dict, now: datetime) -> dict:
    since = gh_mod.window_start(now)
    repo = gh.get("")
    prs = gh_mod.open_prs(gh) + gh_mod.closed_prs(gh, since)
    measure = os.environ.get("STATE_MEASURE_SINCE", "").strip()
    return {
        "now": now,
        "owner": owner,
        "prs": prs,
        "comments": gh_mod.comments(gh, since),
        "owner_issues": {i["number"]: i["title"] for i in gh_mod.labelled_issues(gh, "owner", "all", since)},
        "drift_issues": _brief(gh_mod.labelled_issues(gh, "drift")),
        "nightly_issues": _brief(gh_mod.labelled_issues(gh, "nightly")),
        "first_commit": gh_mod.first_commit_finder(gh, repo["default_branch"]),
        "previous": previous,
        "measure_since": signals.parse_time(measure) if measure else None,
    }


def _brief(issues: List[dict]) -> List[dict]:
    return [{k: i[k] for k in ("number", "title", "url", "created")} for i in issues]


def same(a: dict, b: dict) -> bool:
    strip = lambda s: {k: v for k, v in s.items() if k != "generated_at"}  # noqa: E731
    return strip(a) == strip(b)


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", required=True)
    p.add_argument("--owner", default="")
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--dry-run", action="store_true", help="print the body, write nothing")
    p.add_argument("--github", action="store_true", help="write a job summary and annotations")
    a = p.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    gh = gh_mod.GitHub(token, a.repo)
    owner = owner_login(Path(a.root), a.owner)
    name_owner, name = a.repo.split("/")
    now = datetime.now(timezone.utc).replace(microsecond=0)

    current = issue_mod.choose(gh_mod.labelled_issues(gh, issue_mod.LABEL))
    previous, node, pinned = {}, None, False
    try:
        if current:
            info = gh.graphql(ISSUE_QUERY, owner=name_owner, name=name, number=current["number"])["repository"]["issue"]
            node, pinned = info["id"], info["isPinned"]
            previous = issue_mod.trusted_previous(current, info["body"], (info.get("editor") or {}).get("login"), owner)
    except issue_mod.StateIssueError as e:
        print(f"::error title=State issue::{e}" if a.github else f"error: {e}", file=sys.stderr)
        return 1

    state = signals.compute(snapshot(gh, owner, previous, now))
    state = signals.trim_log(state, issue_mod.fits)
    body = issue_mod.render(state)

    if a.dry_run:
        print(body)
    elif current is None:
        created = gh.post("/issues", {"title": issue_mod.TITLE, "body": body, "labels": [issue_mod.LABEL]})
        print(f"opened the state issue #{created['number']}")
        node = created["node_id"]
    elif not same(state, previous) or _older_than(previous, now, minutes=60):
        gh.patch(f"/issues/{current['number']}", {"body": body})
        print(f"updated the state issue #{current['number']}")
    else:
        print(f"the state issue #{current['number']} is unchanged")

    if not a.dry_run and node and not pinned:
        try:
            gh.graphql(PIN, id=node)
        except gh_mod.GitHubError as e:  # pinning is a convenience: the label finds the issue too
            print(f"::warning title=State issue::couldn't pin it: {e}" if a.github else f"warning: {e}")

    if a.github and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(body.split("```", 1)[0] + f"\n{gh.calls} GitHub API calls.\n")
    print(f"{gh.calls} GitHub API calls; waiting: {state['waiting']}")
    return 0


def _older_than(previous: dict, now: datetime, minutes: int) -> bool:
    """The issue is rewritten at least hourly, so its time shows the Action is alive."""
    at = signals.parse_time(previous.get("generated_at"))
    return at is None or (now - at).total_seconds() >= minutes * 60


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
