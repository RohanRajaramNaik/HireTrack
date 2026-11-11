"""Applicant pipeline rules (pure Python, no database code).

Stages run in a fixed order:

    applied -> screened -> interview -> offer -> hired

An application can move forward ONE stage at a time, or be rejected from any
stage that is still open. "hired" and "rejected" are final. A rejected
application can be reopened, which puts it back at the stage it was rejected
from, so a mistake can be undone without losing the audit history.
"""
from __future__ import annotations

FLOW: tuple[str, ...] = ("applied", "screened", "interview", "offer", "hired")
REJECTED = "rejected"
ALL_STAGES: tuple[str, ...] = (*FLOW, REJECTED)
FINAL: frozenset[str] = frozenset({"hired", REJECTED})

LABELS = {
    "applied": "Applied",
    "screened": "Screened",
    "interview": "Interview",
    "offer": "Offer",
    "hired": "Hired",
    "rejected": "Rejected",
}


class StageError(ValueError):
    """Raised when a stage change is not allowed."""


def next_stage(stage: str) -> str | None:
    """The stage after this one in the normal flow, or None at the end."""
    if stage not in FLOW:
        return None
    i = FLOW.index(stage)
    return FLOW[i + 1] if i + 1 < len(FLOW) else None


def allowed_moves(stage: str, reopen_to: str | None = None) -> list[str]:
    """Stages an application at `stage` may move to.

    reopen_to is the stage a rejected application was rejected from.
    """
    if stage not in ALL_STAGES:
        raise StageError(f"Unknown stage '{stage}'")
    if stage == REJECTED:
        return [reopen_to] if reopen_to in FLOW and reopen_to != "hired" else []
    if stage == "hired":
        return []
    moves = [next_stage(stage)]
    moves.append(REJECTED)
    return [m for m in moves if m]


def check_move(current: str, target: str, reopen_to: str | None = None) -> None:
    """Raise StageError with a plain-English reason if current -> target is not allowed."""
    if target not in ALL_STAGES:
        raise StageError(f"Unknown stage '{target}'")
    if current == target:
        raise StageError(f"The application is already at {LABELS[current]}")
    if current in FINAL and not (current == REJECTED and target == reopen_to):
        raise StageError(f"{LABELS[current]} is a final stage and cannot be changed")
    if target not in allowed_moves(current, reopen_to):
        nxt = next_stage(current)
        hint = f" The next stage is {LABELS[nxt]}." if nxt else ""
        raise StageError(f"Cannot move from {LABELS[current]} to {LABELS[target]}.{hint}")


def furthest_stage(stage: str, rejected_from: str | None) -> str:
    """The furthest stage in the normal flow an application got to.

    A rejected application counts as having reached the stage it was rejected at.
    """
    if stage == REJECTED:
        return rejected_from if rejected_from in FLOW else "applied"
    return stage


def funnel(furthest: dict[str, int], current: dict[str, int]) -> list[dict]:
    """Build the funnel rows shown on the dashboard.

    furthest: {stage: number of applications whose furthest stage is this one}
    current:  {stage: number of applications sitting at this stage right now}
    "reached" = applications that got to this stage or any later one.
    "conversion" = reached / reached at the previous stage, as a percentage.
    """
    out = []
    prev = None
    for i, stage in enumerate(FLOW):
        reached = sum(furthest.get(s, 0) for s in FLOW[i:])
        conv = round(reached / prev * 100, 1) if prev else None
        out.append(
            {
                "stage": stage,
                "label": LABELS[stage],
                "current": current.get(stage, 0),
                "reached": reached,
                "conversion": conv,
            }
        )
        prev = reached
    out.append(
        {
            "stage": REJECTED,
            "label": LABELS[REJECTED],
            "current": current.get(REJECTED, 0),
            "reached": None,
            "conversion": None,
        }
    )
    return out
