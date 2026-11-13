"""The state of the work, computed from a snapshot of GitHub (docs/process.md §4.1, "State Action").

Pure functions: `github.py` fetches and normalises, `state.py` writes the issue, and this file
decides. Every signal here has its known-bad examples in tests/test_signals.py.

A snapshot is a dict:
  now             datetime (UTC)
  owner           the owner's login
  prs             [{number, url, title, branch, draft, state (open|merged|closed), created,
                    merged_at, head_date, head_parents (count), checks {name: (conclusion, at)},
                    statuses {context: (state, at)}, parent_statuses {context: (state, at)},
                    reviews [(is_bot, at)], mergeable}]
  comments        [{id, url, issue, user, is_bot, app, created, body}] on issues and pull
                    requests, oldest first, over the window
  owner_issues    {number: title} of issues labelled `owner`
  drift_issues, nightly_issues   [{number, title, url, created}] open issues with that label
  nightly_runs    [{url, event, completed, ran}] completed runs of the nightly matrix on main
                    (`ran`: its "Build the APKs" job ran, not skipped), or None when its
                    workflow file doesn't exist
  first_commit    callable (branch, since) -> earliest commit datetime at or after `since`
                    on that branch, or None; for a contract, the branch is a prefix ending in `-`
  previous        the previous state (dict) or {}
  measure_since   datetime the miss-rate measure starts (None: the log's own start, or now)
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import conventions as cv

HANDOFF_LIMIT = timedelta(minutes=20)  # §4.3: a hand-off not picked up after 20 minutes is flagged
HANDOFF_EXPIRY = timedelta(days=7)  # never picked up: logged as missed and no longer listed
STALE_AFTER = timedelta(hours=2)  # a phase PR with no activity for over 2 hours
GREEN_WAIT = timedelta(minutes=60)  # green for longer than two train cycles (every 30 min)
MEASURE_DAYS = 14  # ADR-686's fallback measure: the first two weeks
APP_THREAD = "claude"  # performed_via_github_app.slug of what a thread posts
VERIFY_CHECK = "verify"
REVIEW_STATUS = "review"
TRAIN_STATUS = "train"
NIGHTLY_WORKFLOW = "nightly.yml"
NIGHTLY_EVENTS = ("schedule", "workflow_dispatch")  # the server's clock dispatches; the cron is a second chance
NIGHTLY_LIMIT = timedelta(hours=26)  # a daily run, with two hours' slack: past this, the clock is dead


def iso(t: Optional[datetime]) -> Optional[str]:
    return None if t is None else t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def minutes(d: timedelta) -> int:
    return int(d.total_seconds() // 60)


# ---------------------------------------------------------------- hand-offs


def _reports(snap) -> Tuple[List[Tuple[dict, cv.Report]], List[dict]]:
    found, errors = [], []
    for c in snap["comments"]:
        try:
            for r in cv.parse_reports(c["body"]):
                found.append((c, r))
        except cv.ReportError as e:
            errors.append({"comment": c["url"], "error": str(e)})
    return found, errors


def _due(snap, comment: dict, report: cv.Report) -> Tuple[str, Optional[datetime]]:
    """('due', time) / ('waiting-merge', None) / ('cancelled', time) / ('error', None)."""
    if report.phase not in cv.DUE_AT_MERGE:
        return "due", comment["created"]
    pr = next((p for p in snap["prs"] if p["number"] == comment["issue"]), None)
    branch = cv.parse_branch(pr["branch"]) if pr else None
    if not pr or not branch or branch.item != report.item or branch.phase != report.phase:
        return "error", None
    if pr["state"] == "merged":  # due when both the merge and the report have happened
        return "due", max(pr["merged_at"], comment["created"])
    if pr["state"] == "closed":
        return "cancelled", pr.get("closed_at") or comment["created"]
    return "waiting-merge", None


def _build_pr(snap, item: str) -> Optional[dict]:
    want = f"item/{item}-build".lower()
    prs = [p for p in snap["prs"] if p["branch"].lower() == want]
    return max(prs, key=lambda p: p["created"]) if prs else None


def _pickup(snap, reports, item: str, phase: str, due: datetime) -> Optional[datetime]:
    seen: List[datetime] = []
    branch = cv.branch_for(item, phase)
    if branch:
        t = snap["first_commit"](branch, due)
        if t:
            seen.append(t)
    if phase == "contract":
        t = snap["first_commit"](cv.contract_prefix(item), due)
        if t:
            seen.append(t)
    for c, r in reports:
        if r.item == item and r.phase == phase and c["created"] >= due:
            seen.append(c["created"])
    if phase == "review":
        pr = _build_pr(snap, item)
        if pr:
            pr = snap.get("pr_detail", lambda p: p)(pr)
            seen += [at for is_bot, at in pr["reviews"] if not is_bot and at >= due]
            st = pr["statuses"].get(REVIEW_STATUS)
            if st and st[1] >= due:
                seen.append(st[1])
    return min(seen) if seen else None


def _key(row) -> Tuple:
    return tuple(row[:5])


def handoffs(snap, reports) -> Tuple[List[dict], List[list], List[dict]]:
    """(waiting, new log rows, errors). A log row is
    [item, from_phase, next_item, next_phase, due, picked_up, delay_seconds, result],
    result one of picked, late, expired, cancelled. late and expired are misses."""
    now = snap["now"]
    logged = {_key(r) for r in snap["previous"].get("handoff_log", {}).get("rows", [])}
    waiting, rows, errors = [], [], []
    pending: Dict[Tuple[str, str], bool] = {}
    steps = []
    for c, r in reports:
        if not r.next:
            continue
        status, due = _due(snap, c, r)
        if status == "error":
            errors.append({"comment": c["url"], "error": f"a {r.phase} report must be on its own pull request "
                                                          f"(item/{r.item}-{r.phase} or contract/{r.item}-*)"})
            continue
        if status == "waiting-merge":
            continue
        for target, phase in r.next:
            steps.append((due, status, c, r, target, phase))
    steps.sort(key=lambda x: x[0])
    for due, status, c, r, target, phase in steps:
        row = [r.item, r.phase, target, phase, iso(due)]
        if tuple(row) in logged:
            continue
        if status == "cancelled":
            rows.append(row + [None, None, "cancelled"])
            logged.add(tuple(row))
            continue
        if pending.get((target, phase)):
            continue  # the same next step reported again while it still waits: one hand-off
        picked = _pickup(snap, reports, target, phase, due)
        if picked:
            delay = int((picked - due).total_seconds())
            rows.append(row + [iso(picked), delay, "late" if picked - due > HANDOFF_LIMIT else "picked"])
            logged.add(tuple(row))
        elif now - due > HANDOFF_EXPIRY:
            rows.append(row + [None, None, "expired"])
            logged.add(tuple(row))
        else:
            pending[(target, phase)] = True
            if now - due > HANDOFF_LIMIT:
                waiting.append({
                    "item": target, "phase": phase, "after": f"{r.item} {r.phase}",
                    "due": iso(due), "waited_min": minutes(now - due),
                    "expected": cv.branch_for(target, phase) or (cv.contract_prefix(target) + "*" if phase == "contract"
                                                                 else f"a review of item/{target}-build"),
                    "report": c["url"],
                })
    return waiting, rows, errors


# ---------------------------------------------------------------- pull requests


def _green(pr) -> Optional[datetime]:
    """When the PR's head became green (verify succeeded and review passed), or None."""
    check = pr["checks"].get(VERIFY_CHECK)
    if not check or check[0] != "success":
        return None
    review = pr["statuses"].get(REVIEW_STATUS)
    if (not review or review[0] != "success") and pr.get("head_parents", 1) == 2:
        # A merge the train made to bring the branch up to date: the review of the commit it
        # updated covers it (the train's own rule).
        review = pr.get("parent_statuses", {}).get(REVIEW_STATUS)
    if not review or review[0] != "success":
        return None
    return max(check[1], review[1])


def _last_activity(snap, pr) -> datetime:
    times = [pr["created"]]
    if pr.get("head_date"):
        times.append(pr["head_date"])
    times += [c["created"] for c in snap["comments"] if c["issue"] == pr["number"] and not c["is_bot"]]
    times += [at for is_bot, at in pr["reviews"] if not is_bot]
    return max(times)


def stale_prs(snap) -> List[dict]:
    now, out = snap["now"], []
    for pr in snap["prs"]:
        if pr["state"] != "open":
            continue
        b = cv.parse_branch(pr["branch"])
        if not b or _green(pr):
            continue  # only the threads' PRs; a green one waits on the train, not on a thread
        last = _last_activity(snap, pr)
        if now - last > STALE_AFTER:
            out.append({"number": pr["number"], "url": pr["url"], "branch": pr["branch"], "item": b.item,
                        "phase": b.phase, "draft": pr["draft"], "last_activity": iso(last),
                        "idle_min": minutes(now - last)})
    return sorted(out, key=lambda x: -x["idle_min"])


def green_not_merging(snap) -> List[dict]:
    now, out = snap["now"], []
    for pr in snap["prs"]:
        if pr["state"] != "open" or pr["draft"]:
            continue
        since = _green(pr)
        if since is None or now - since <= GREEN_WAIT:
            continue
        why = []
        if pr.get("mergeable") == "CONFLICTING":
            why.append("conflicts with its base")
        train = pr["statuses"].get(TRAIN_STATUS)
        if train:
            why.append(f"train: {train[0]}" + (f" ({train[2]})" if len(train) > 2 and train[2] else ""))
        out.append({"number": pr["number"], "url": pr["url"], "branch": pr["branch"], "green_since": iso(since),
                    "waited_min": minutes(now - since), "why": "; ".join(why) or "unknown"})
    return sorted(out, key=lambda x: -x["waited_min"])


# ---------------------------------------------------------------- owner comments


def owner_comments(snap) -> List[dict]:
    """The owner's comments on `owner` issues, posted on GitHub itself (not through an app), that
    no later comment through the Claude app has recorded by linking them."""
    owner = snap["owner"].lower()
    out = []
    comments = snap["comments"]
    for i, c in enumerate(comments):
        if c["issue"] not in snap["owner_issues"]:
            continue
        if c["user"].lower() != owner or c["app"] is not None:
            continue
        anchor = re.compile(rf"issuecomment-{c['id']}(?!\d)")
        recorded = any(
            later["issue"] == c["issue"] and later["app"] == APP_THREAD and later["created"] >= c["created"]
            and anchor.search(later["body"] or "")
            for later in comments[i + 1:]
        )
        if not recorded:
            out.append({"issue": c["issue"], "title": snap["owner_issues"][c["issue"]], "comment": c["url"],
                        "created": iso(c["created"])})
    return out


# ---------------------------------------------------------------- the whole state


def _rate(rows: List[list], start: datetime, end: Optional[datetime], waiting: List[dict]) -> Dict[str, int]:
    def inside(t):
        return t >= start and (end is None or t < end)
    n = m = 0
    for r in rows:
        due = parse_time(r[4])
        if r[7] == "cancelled" or not inside(due):
            continue
        n += 1
        m += r[7] in ("late", "expired")
    for w in waiting:  # waiting past the limit is already a miss, whatever happens next
        if inside(parse_time(w["due"])):
            n += 1
            m += 1
    return {"handoffs": n, "missed": m}


def nightly_overdue(snap) -> List[dict]:
    """The guard that shows a dead clock: no completed nightly run on main, from the clock or the
    cron, within 26 hours. A red run counts as having run (red is the `nightly` issues' job); a
    run from a pull request's self-test doesn't, nor a night's second trigger, which the
    once-a-night guard ends before "Build the APKs" (a late cron after the clock's run would
    otherwise put the alarm off by up to a day). A missing workflow file is listed too."""
    runs = snap["nightly_runs"]
    if runs is None:
        return [{"workflow": NIGHTLY_WORKFLOW, "last_completed": None, "url": None, "reason": "no workflow file"}]
    done = [r for r in runs if r["event"] in NIGHTLY_EVENTS and r.get("completed") and r.get("ran")]
    last = max(done, key=lambda r: parse_time(r["completed"]), default=None)
    if last and snap["now"] - parse_time(last["completed"]) <= NIGHTLY_LIMIT:
        return []
    return [{"workflow": NIGHTLY_WORKFLOW, "last_completed": last["completed"] if last else None,
             "url": last["url"] if last else None,
             "reason": "no completed run within 26 hours" if last else "never completed"}]


def compute(snap) -> Dict[str, Any]:
    now = snap["now"]
    prev_log = snap["previous"].get("handoff_log", {})
    reports, errors = _reports(snap)
    waiting, new_rows, ho_errors = handoffs(snap, reports)
    rows = list(prev_log.get("rows", [])) + new_rows
    rows.sort(key=lambda r: (r[4], r[0], r[1], r[2], r[3]))
    # The measure starts at STATE_MEASURE_SINCE, else where the log started: on the first run,
    # the first hand-off it found (its comments reach 14 days back) or now.
    start = (snap.get("measure_since") or parse_time(prev_log.get("since"))
             or min([parse_time(r[4]) for r in new_rows] + [now]))
    dropped = copy.deepcopy(prev_log.get("dropped") or {"all": {"handoffs": 0, "missed": 0},
                                                         "first_14_days": {"handoffs": 0, "missed": 0}})
    first = _rate(rows, start, start + timedelta(days=MEASURE_DAYS), waiting)
    every = _rate(rows, start, None, waiting)
    for k, v in (("first_14_days", first), ("all", every)):
        v["handoffs"] += dropped[k]["handoffs"]
        v["missed"] += dropped[k]["missed"]
    lists = {
        "handoffs_waiting": waiting,
        "stale_prs": stale_prs(snap),
        "green_not_merging": green_not_merging(snap),
        "drift_issues": snap["drift_issues"],
        "nightly_issues": snap["nightly_issues"],
        "nightly_overdue": nightly_overdue(snap),
        "owner_comments": owner_comments(snap),
        "report_errors": errors + ho_errors,
    }
    return {
        "schema": 1,
        "generated_at": iso(now),
        "waiting": any(lists.values()),
        **lists,
        "miss_rate": {
            "first_14_days": {**first, "from": iso(start), "to": iso(start + timedelta(days=MEASURE_DAYS))},
            "all": every,
            "fallback_if": "more than 1 missed in 10 in the first 14 days (ADR-686)",
            "exceeded": first["handoffs"] > 0 and first["missed"] * 10 > first["handoffs"],
        },
        "handoff_log": {"since": iso(start), "dropped": dropped, "rows": rows},
    }


# Rows are folded only once their report has left the comment window (14 days), so a folded
# hand-off can't be found and logged a second time.
FOLD_AFTER = timedelta(days=15)


def trim_log(state: Dict[str, Any], fits: Callable[[Dict[str, Any]], bool]) -> Dict[str, Any]:
    """Fold the oldest log rows into the `dropped` counters until the state fits the issue.
    Raises when it can't fit with only rows older than FOLD_AFTER folded."""
    log = state["handoff_log"]
    start = parse_time(log["since"])
    end = start + timedelta(days=MEASURE_DAYS)
    cutoff = parse_time(state["generated_at"]) - FOLD_AFTER
    while not fits(state):
        old = [r for r in log["rows"][:max(1, len(log["rows"]) // 50)] if parse_time(r[4]) < cutoff]
        if not old:  # 2% at a time, as rendering is the cost
            raise ValueError("the state doesn't fit the issue even with every hand-off older than 15 days folded")
        for r in old:
            _drop(log, r, start, end)
        del log["rows"][:len(old)]
    return state


def _drop(log, r, start, end):
    if r[7] != "cancelled":
        missed = int(r[7] in ("late", "expired"))
        due = parse_time(r[4])
        if due >= start:
            log["dropped"]["all"]["handoffs"] += 1
            log["dropped"]["all"]["missed"] += missed
            if due < end:
                log["dropped"]["first_14_days"]["handoffs"] += 1
                log["dropped"]["first_14_days"]["missed"] += missed
