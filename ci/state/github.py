"""A small GitHub client for the state Action: REST and GraphQL over urllib, standard library only
(the light runner has nothing else), and the snapshot `signals.compute` reads."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from conventions import parse_branch
from signals import parse_time

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token: str, repo: str, api: str = API):
        self.token, self.repo, self.api = token, repo, api
        self.calls = 0

    def _request(self, method: str, url: str, body: Any = None):
        if not url.startswith("http"):
            url = self.api + url
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "volumes-state-action",
        })
        for attempt in range(3):
            self.calls += 1
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    text = resp.read().decode()
                    return (json.loads(text) if text else None), resp.headers
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code in (502, 503, 504) and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                if e.code == 404 or e.code == 409:  # 409: an empty repository's or branch's commits
                    return None, e.headers
                raise GitHubError(f"{method} {url}: {e.code} {detail}") from None
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise GitHubError(f"{method} {url}: {e}") from None
        raise GitHubError(f"{method} {url}: gave up")

    def get(self, path: str):
        return self._request("GET", f"/repos/{self.repo}{path}")[0]

    def pages(self, path: str, stop=None) -> List[dict]:
        """Every page of a list. `stop(item)` true ends the walk early (lists sorted by time)."""
        out: List[dict] = []
        sep = "&" if "?" in path else "?"
        url: Optional[str] = f"{self.api}/repos/{self.repo}{path}{sep}per_page=100"
        while url:
            data, headers = self._request("GET", url)
            for item in data or []:
                if stop and stop(item):
                    return out
                out.append(item)
            m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", "") or "")
            url = m.group(1) if m else None
        return out

    def post(self, path: str, body: dict):
        return self._request("POST", f"/repos/{self.repo}{path}", body)[0]

    def patch(self, path: str, body: dict):
        return self._request("PATCH", f"/repos/{self.repo}{path}", body)[0]

    def graphql(self, query: str, **variables):
        data, _ = self._request("POST", f"{self.api}/graphql", {"query": query, "variables": variables})
        if not data or data.get("errors"):
            raise GitHubError(f"graphql: {(data or {}).get('errors')}")
        return data["data"]


# ---------------------------------------------------------------- the snapshot

PRS_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 50, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number url title headRefName isDraft createdAt mergeable
        reviews(last: 30) { nodes { submittedAt author { __typename } } }
        commits(last: 10) { nodes { commit {
          committedDate
          parents(first: 2) { totalCount nodes { status { contexts { context state createdAt description } } } }
          status { contexts { context state createdAt description } }
          checkSuites(first: 30) { nodes { checkRuns(first: 50) { nodes { name status conclusion completedAt } } } }
        } } }
      }
    }
  }
}
"""


def _contexts(status) -> Dict[str, tuple]:
    out: Dict[str, tuple] = {}
    for c in (status or {}).get("contexts") or []:
        at = parse_time(c["createdAt"])
        if c["context"] not in out or at > out[c["context"]][1]:
            out[c["context"]] = (c["state"].lower(), at, c.get("description") or "")
    return out


def _checks(commit) -> Dict[str, tuple]:
    out: Dict[str, tuple] = {}
    for suite in (commit.get("checkSuites") or {}).get("nodes") or []:
        for run in (suite.get("checkRuns") or {}).get("nodes") or []:
            prev = out.get(run["name"])
            if run["status"] != "COMPLETED":  # a run still going (a re-run) outranks any earlier result
                out[run["name"]] = ("pending", None)
                continue
            at = parse_time(run["completedAt"])
            if not prev or (prev[1] is not None and at > prev[1]):
                out[run["name"]] = ((run["conclusion"] or "").lower(), at)
    return {k: v for k, v in out.items() if v[1] is not None}


def open_prs(gh: GitHub) -> List[dict]:
    owner, name = gh.repo.split("/")
    out, after = [], None
    while True:
        data = gh.graphql(PRS_QUERY, owner=owner, name=name, after=after)["repository"]["pullRequests"]
        for n in data["nodes"]:
            history = [c["commit"] for c in n["commits"]["nodes"] or []]
            commit = history[-1] if history else {}
            parents = commit.get("parents") or {"totalCount": 1, "nodes": []}
            # A thread's last work: the newest commit that isn't a merge (the train's update of the
            # branch is a merge, and isn't the thread's activity).
            own = [c for c in history if (c.get("parents") or {}).get("totalCount", 1) < 2]
            first_parent = (parents["nodes"] or [{}])[0]
            out.append({
                "number": n["number"], "url": n["url"], "title": n["title"], "branch": n["headRefName"],
                "draft": n["isDraft"], "state": "open", "created": parse_time(n["createdAt"]),
                "merged_at": None, "closed_at": None, "mergeable": n["mergeable"],
                "head_date": parse_time(own[-1]["committedDate"]) if own else None,
                "head_parents": parents["totalCount"],
                "checks": _checks(commit), "statuses": _contexts(commit.get("status")),
                "parent_statuses": _contexts(first_parent.get("status")),
                "reviews": [((r.get("author") or {}).get("__typename") == "Bot", parse_time(r["submittedAt"]))
                            for r in n["reviews"]["nodes"] if r.get("submittedAt")],
            })
        if not data["pageInfo"]["hasNextPage"]:
            return out
        after = data["pageInfo"]["endCursor"]


def closed_prs(gh: GitHub, since: datetime) -> List[dict]:
    """Phase pull requests closed or merged inside the window: when a spec or contract merged."""
    rows = gh.pages("/pulls?state=closed&sort=updated&direction=desc",
                    stop=lambda p: parse_time(p["updated_at"]) < since)
    return [{
        "number": p["number"], "url": p["html_url"], "title": p["title"], "branch": p["head"]["ref"],
        "draft": p["draft"], "state": "merged" if p["merged_at"] else "closed",
        "created": parse_time(p["created_at"]), "merged_at": parse_time(p["merged_at"]),
        "closed_at": parse_time(p["closed_at"]), "mergeable": None, "head_date": None, "head_parents": 1,
        "checks": {}, "statuses": {}, "parent_statuses": {}, "reviews": [], "head_sha": p["head"]["sha"],
        "detail": False,  # reviews and statuses are fetched only when a hand-off needs them
    } for p in rows]


def pr_detail(gh: GitHub):
    """Fills in a closed pull request's reviews and its head's statuses, when a review hand-off
    needs them (a build PR the train merged before any run saw its review)."""
    def fill(pr: dict) -> dict:
        if pr.get("detail", True):
            return pr
        reviews = gh.pages(f"/pulls/{pr['number']}/reviews")
        pr["reviews"] = [(r["user"]["type"] == "Bot", parse_time(r["submitted_at"]))
                         for r in reviews if r.get("submitted_at") and r.get("user")]
        status = gh.get(f"/commits/{pr['head_sha']}/status") or {}
        pr["statuses"] = {s["context"]: (s["state"], parse_time(s["created_at"]), s.get("description") or "")
                          for s in status.get("statuses") or []}
        pr["detail"] = True
        return pr
    return fill


def comments(gh: GitHub, since: datetime) -> List[dict]:
    rows = gh.pages(f"/issues/comments?sort=created&direction=asc&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    out = []
    for c in rows:
        created = parse_time(c["created_at"])
        if created < since:
            continue  # `since` filters on update time; an old comment edited lately isn't new
        out.append({
            "id": c["id"], "url": c["html_url"], "issue": int(c["issue_url"].rsplit("/", 1)[1]),
            "user": c["user"]["login"], "is_bot": c["user"]["type"] == "Bot",
            "app": (c.get("performed_via_github_app") or {}).get("slug"),
            "created": created, "body": c.get("body") or "",
        })
    out.sort(key=lambda c: (c["created"], c["id"]))
    return out


def labelled_issues(gh: GitHub, label: str, state: str = "open", since: Optional[datetime] = None) -> List[dict]:
    q = f"/issues?labels={urllib.parse.quote(label)}&state={state}"
    if since:
        q += f"&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    return [{"number": i["number"], "title": i["title"], "url": i["html_url"], "created": i["created_at"],
             "user": i["user"]["login"]}
            for i in gh.pages(q) if "pull_request" not in i]


def first_commit_finder(gh: GitHub, base: str):
    """(branch or contract prefix, since) -> the earliest commit at or after `since` that the
    branch has and `base` doesn't, merges left out. Only the branch's own commits count: a
    branch cut from a `base` that moved after the hand-off was due would otherwise look picked
    up at once, and the train's merge of `base` into a branch isn't a thread's work. Both lists
    are bounded by date, so a long branch is read in full. Branch names are matched ignoring
    case (IDs are upper case, but a thread may slip)."""
    cache: Dict[tuple, Optional[datetime]] = {}
    index: Dict[str, List[str]] = {}
    on_base: Dict[datetime, set] = {}

    def branches(ref: str) -> List[str]:
        top = ref.split("/", 1)[0] + "/"
        if top not in index:
            refs = gh.pages(f"/git/matching-refs/heads/{top}")
            index[top] = [r["ref"][len("refs/heads/"):] for r in refs]
        if ref.endswith("-"):  # every contract branch of one item
            item = ref[len("contract/"):-1]
            return [b for b, p in ((b, parse_branch(b)) for b in index[top]) if p and p.phase == "contract" and p.item == item]
        return [b for b in index[top] if b.lower() == ref.lower()]

    def commits(ref: str, since: datetime) -> List[dict]:
        stamp = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        return gh.pages(f"/commits?sha={urllib.parse.quote(ref, safe='/')}&since={stamp}")

    def find(ref: str, since: datetime) -> Optional[datetime]:
        key = (ref.lower(), since)
        if key in cache:
            return cache[key]
        best = None
        for b in branches(ref):
            if since not in on_base:
                on_base[since] = {c["sha"] for c in commits(base, since)}
            for c in commits(b, since):
                if c["sha"] in on_base[since] or len(c.get("parents") or []) > 1:
                    continue
                t = parse_time(c["commit"]["committer"]["date"])
                if t >= since and (best is None or t < best):
                    best = t
        cache[key] = best
        return best

    return find


def window_start(now: datetime, days: int = 14) -> datetime:
    return now - timedelta(days=days)
