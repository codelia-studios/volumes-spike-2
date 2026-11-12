"""How an item's phases show on GitHub (docs/process.md §4.5, "How an item shows on GitHub").

The one place the state Action reads the conventions from; docs/process.md states them in
words, and the tests hold every known-bad example. In short:

- **Branches.** A phase thread pushes `item/<ID>-<phase>`; a contract thread pushes
  `contract/<ID>-<name>`. In an item branch the phase is the last hyphen-separated part and
  the ID is the rest. IDs are upper case (`LIB-12`); an item branch's ID is read upper-cased,
  but a contract's name must start with a lower-case letter, since that's where its ID ends.
- **Labels** are for kinds of issue only: `owner`, `drift`, `nightly`, `state`, `digest`.
  An item's phase is never a label: the branch already says it (one source of truth).
- **The report block.** Every thread ends by posting its report as a comment on its own
  pull request (or, with no branch of its own, on the pull request or issue it worked
  from), with exactly one fenced block whose info string is `volumes-report`:

      ```volumes-report
      item: LIB-12
      phase: oracle
      outcome: done
      next: build
      ```

  `outcome` is done, stuck or question. `next` is a comma-separated list: a phase of the
  same item (`build`), a phase of another item (`LIB-13 spec`), or `none`. The thread's
  COORDINATOR line names the same next steps in its chat report.
- **When a hand-off is due.** At the report, except after `spec` and `contract`, whose
  next phase may start only once their pull request has merged: then it is due at the
  merge, and a pull request closed unmerged cancels it.
- **Picked up** means the first sign of the next phase at or after the time it was due:
  a commit on its branch (`item/<ID>-<next>`, or for a contract any `contract/<ID>-*`),
  its own report block, or for `review` (which pushes no branch) a review or a `review`
  status on the item's build pull request.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

PHASES = ("spec", "oracle", "build", "review", "contract", "intake")
# Phases whose next step waits for their pull request to merge.
DUE_AT_MERGE = ("spec", "contract")
# Phases with no branch of their own: picked up by their review or report instead.
NO_BRANCH = ("review",)
OUTCOMES = ("done", "stuck", "question")
LABELS = ("owner", "drift", "nightly", "state", "digest")

ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*$")
_PHASE_ALT = "|".join(PHASES)
ITEM_BRANCH_RE = re.compile(r"^item/(?P<id>.+)-(?P<phase>" + _PHASE_ALT + r")$", re.I)
# Case matters here, as it doesn't for item branches: the ID is upper case and the name starts
# with a lower-case letter, which is how `contract/LIB-12-shelf-api` splits into LIB-12 and shelf-api.
CONTRACT_BRANCH_RE = re.compile(r"^contract/(?P<id>[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*)-(?P<name>[a-z][a-z0-9._-]*)$")

# A fenced block opened by three or more backticks or tildes with the info string
# `volumes-report`, closed by the same fence character, at least as long.
_FENCE_OPEN = re.compile(r"^(?P<fence>`{3,}|~{3,})[ \t]*volumes-report[ \t]*$")
MAX_VALUE = 200


@dataclass(frozen=True)
class Branch:
    item: str
    phase: str  # one of PHASES; contract branches have phase "contract"
    name: str = ""  # the contract's name


def parse_branch(ref: str) -> Optional[Branch]:
    """The item and phase a branch name stands for, or None when it isn't a phase branch."""
    if ref.startswith("refs/heads/"):
        ref = ref[len("refs/heads/"):]
    m = ITEM_BRANCH_RE.match(ref)
    if m:
        item = m.group("id").upper()
        phase = m.group("phase").lower()
        if phase == "contract" or not ID_RE.match(item):
            return None  # a contract is `contract/<ID>-<name>`, never an item branch
        return Branch(item, phase)
    m = CONTRACT_BRANCH_RE.match(ref)
    if m:
        return Branch(m.group("id"), "contract", m.group("name"))
    return None


def branch_for(item: str, phase: str) -> Optional[str]:
    """The branch a phase pushes, or None for a phase with no branch of its own (and contracts,
    whose names vary: see contract_prefix)."""
    if phase in NO_BRANCH or phase == "contract":
        return None
    return f"item/{item}-{phase}"


def contract_prefix(item: str) -> str:
    return f"contract/{item}-"


@dataclass(frozen=True)
class Report:
    item: str
    phase: str
    outcome: str
    next: Tuple[Tuple[str, str], ...]  # (item, phase) pairs; empty for none


class ReportError(ValueError):
    pass


def _blocks(body: str) -> List[str]:
    lines = body.replace("\r\n", "\n").split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        m = _FENCE_OPEN.match(lines[i].strip())
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        content = []
        i += 1
        closed = False
        while i < len(lines):
            s = lines[i].strip()
            if s and set(s) == {fence[0]} and len(s) >= len(fence):
                closed = True
                break
            content.append(lines[i])
            i += 1
        if closed:
            blocks.append("\n".join(content))
        i += 1
    return blocks


def parse_reports(body: str) -> List[Report]:
    """Every well-formed report block in a comment. Raises ReportError when the comment has a
    report block that doesn't parse, so a broken report is surfaced instead of ignored."""
    reports = []
    for block in _blocks(body or ""):
        reports.append(_parse_block(block))
    if len(reports) > 1:
        raise ReportError("more than one report block in one comment")
    return reports


def _parse_block(block: str) -> Report:
    fields = {}
    for raw in block.split("\n"):
        line = raw.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        key = key.strip().lower()
        if not sep or not key:
            raise ReportError(f"not a `key: value` line: {line[:60]!r}")
        if key in fields:
            raise ReportError(f"`{key}` given twice")
        fields[key] = value.strip()[:MAX_VALUE]
    for key in ("item", "phase", "outcome", "next"):
        if key not in fields:
            raise ReportError(f"missing `{key}`")
    item = fields["item"].upper()
    if not ID_RE.match(item):
        raise ReportError(f"`item` isn't an ID: {fields['item']!r}")
    phase = fields["phase"].lower()
    if phase not in PHASES:
        raise ReportError(f"unknown phase {fields['phase']!r}")
    outcome = fields["outcome"].lower()
    if outcome not in OUTCOMES:
        raise ReportError(f"unknown outcome {fields['outcome']!r}")
    return Report(item, phase, outcome, _parse_next(fields["next"], item))


def _parse_next(value: str, item: str) -> Tuple[Tuple[str, str], ...]:
    if value.strip().lower() in ("none", "-", ""):
        return ()
    steps = []
    for part in value.split(","):
        words = part.split()
        if len(words) == 1:
            target, phase = item, words[0].lower()
        elif len(words) == 2:
            target, phase = words[0].upper(), words[1].lower()
        else:
            raise ReportError(f"`next` step isn't `<phase>` or `<ID> <phase>`: {part.strip()!r}")
        if phase not in PHASES:
            raise ReportError(f"`next` names an unknown phase {phase!r}")
        if not ID_RE.match(target):
            raise ReportError(f"`next` names a bad ID {target!r}")
        if (target, phase) not in steps:
            steps.append((target, phase))
    return tuple(steps)
