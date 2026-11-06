"""HireTrack matching engine: pure scoring functions.

This module has NO database or web code, so every rule can be unit tested on
its own. The service layer turns ORM rows into the plain dataclasses below,
calls `score_candidates`, and saves the result.

How a candidate is scored against a job (each component is 0-100):

  Skills      (required matched / required) x 80 + (preferred matched / preferred) x 20
              If the job has no preferred skills, required skills count for the full 100.
  Experience  100 if years >= minimum (or minimum is 0), else years / minimum x 100
  Education   100 if candidate level >= minimum level, else level / minimum x 100
  Semantic    cosine similarity of CV summary vs job description embeddings,
              negatives clipped to 0, x 100
  Overall     (skills x w_skills + experience x w_experience
               + education x w_education + semantic x w_semantic) / 100

Every component is rounded to 1 decimal place (half up) *before* the overall
score is calculated, so the calculation shown on screen reproduces exactly.

Ranking: overall descending, then skills descending, then name A-Z.

FAIRNESS: scoring only ever reads skills, years of experience, education level
and the CV summary text. Name, email, age, gender and race are never inputs to
any score. The name is used only as the final alphabetical tie-break so that
the order is stable and predictable.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
REQUIRED_SHARE = 80  # points available for required skills when preferred exist
PREFERRED_SHARE = 20  # points available for preferred skills
DEFAULT_WEIGHTS = {"skills": 40, "experience": 25, "education": 15, "semantic": 20}

EDUCATION_NAMES = {
    1: "Matric",
    2: "Higher Certificate",
    3: "Diploma",
    4: "Bachelor's Degree",
    5: "Honours",
    6: "Master's",
    7: "Doctorate",
}

# Thresholds for the plain-English explanation and the keyword-miss callout.
# all-MiniLM-L6-v2 cosine similarities for genuinely related CV/job pairs sit
# roughly between 0.45 and 0.75, so the bands are set on that scale.
SEMANTIC_CLOSE = 55.0
SEMANTIC_RELATED = 40.0
KEYWORD_MISS_SEMANTIC_MIN = 60.0  # "high" semantic score
KEYWORD_MISS_SKILLS_MAX = 60.0  # "low" skills score


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def round1(value: float) -> float:
    """Round to 1 decimal place, half up (2.25 -> 2.3), unlike Python's banker's round."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def fmt_num(value: float) -> str:
    """90.0 -> '90', 62.3 -> '62.3' (for readable formulas)."""
    return f"{value:.1f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------
# Inputs / outputs
# --------------------------------------------------------------------------
class WeightError(ValueError):
    """Raised when scoring weights are out of range or do not total 100."""


@dataclass(frozen=True)
class Weights:
    skills: int = DEFAULT_WEIGHTS["skills"]
    experience: int = DEFAULT_WEIGHTS["experience"]
    education: int = DEFAULT_WEIGHTS["education"]
    semantic: int = DEFAULT_WEIGHTS["semantic"]

    @property
    def total(self) -> int:
        return self.skills + self.experience + self.education + self.semantic

    def validate(self) -> "Weights":
        for name in ("skills", "experience", "education", "semantic"):
            v = getattr(self, name)
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100:
                raise WeightError(f"Each weight must be a whole number from 0 to 100 ({name} is {v})")
        if self.total != 100:
            raise WeightError(f"Weights must add up to 100% (now {self.total}%)")
        return self


@dataclass
class JobCriteria:
    required: list[str]  # canonical skill names
    preferred: list[str]
    min_experience: float
    min_level: int
    description: str
    weights: Weights = field(default_factory=Weights)


@dataclass
class CandidateProfile:
    candidate_id: int
    skills: list[str]  # canonical skill names
    years_experience: float
    level: int
    resume_summary: str
    # Only used for the final alphabetical tie-break, never for scoring.
    full_name: str = ""
    # canonical -> what was originally typed, e.g. {"javascript": "JS"}
    skills_as_entered: dict[str, str] = field(default_factory=dict)


@dataclass
class SkillMatch:
    score: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str]


@dataclass
class CandidateScore:
    candidate_id: int
    full_name: str
    skills: float
    experience: float
    education: float
    semantic: float
    overall: float
    skill_match: SkillMatch
    alias_hits: dict[str, str]  # canonical -> as entered, for matched skills only
    explanation: str = ""
    keyword_insights: list[str] = field(default_factory=list)
    rank: int = 0


# --------------------------------------------------------------------------
# Validation rules shared with the API layer
# --------------------------------------------------------------------------
def validate_skill_lists(required: Sequence[str], preferred: Sequence[str]) -> None:
    """A job needs >= 1 required skill and preferred must not repeat a required one."""
    if not required:
        raise ValueError("Add at least one required skill")
    overlap = sorted(set(required) & set(preferred))
    if overlap:
        raise ValueError(f"Preferred skills repeat required skills: {', '.join(overlap)}")


# --------------------------------------------------------------------------
# Component scores
# --------------------------------------------------------------------------
def skills_score(candidate_skills: Sequence[str], required: Sequence[str], preferred: Sequence[str]) -> SkillMatch:
    """Required skills are worth 80 points, preferred 20.

    With no preferred skills, required skills are worth the full 100.
    Inputs must already be canonical (see SkillNormaliser).
    """
    have = set(candidate_skills)
    matched_req = [s for s in required if s in have]
    missing_req = [s for s in required if s not in have]
    matched_pref = [s for s in preferred if s in have]
    missing_pref = [s for s in preferred if s not in have]

    if not required:
        req_part = 0.0
    elif preferred:
        req_part = len(matched_req) / len(required) * REQUIRED_SHARE
    else:
        req_part = len(matched_req) / len(required) * 100
    pref_part = len(matched_pref) / len(preferred) * PREFERRED_SHARE if preferred else 0.0

    return SkillMatch(
        score=round1(clamp(req_part + pref_part)),
        matched_required=matched_req,
        missing_required=missing_req,
        matched_preferred=matched_pref,
        missing_preferred=missing_pref,
    )


def experience_score(years: float, minimum: float) -> float:
    """100 if the candidate meets the minimum (or there is none), else pro rata."""
    if minimum <= 0 or years >= minimum:
        return 100.0
    return round1(clamp(max(years, 0) / minimum * 100))


def education_score(level: int, min_level: int) -> float:
    """100 if the candidate's level is at or above the minimum, else level / minimum x 100."""
    if level >= min_level:
        return 100.0
    return round1(clamp(level / min_level * 100))


def semantic_scores(job_vector: np.ndarray, candidate_matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of each CV embedding to the job embedding, as 0-100.

    Negative similarities (opposite meaning) are treated as 0.
    """
    if candidate_matrix.shape[0] == 0:
        return np.zeros(0)
    sims = cosine_similarity(job_vector.reshape(1, -1), candidate_matrix)[0]
    return np.clip(sims, 0.0, None) * 100.0


def overall_score(skills: float, experience: float, education: float, semantic: float, weights: Weights) -> float:
    """Weighted average of the four components, rounded to 1 decimal.

    Computed in integer tenths so the browser's "what if" re-ranking (which
    uses the same integer method) always agrees with the server exactly.
    """
    tenths = [int(round(c * 10)) for c in (skills, experience, education, semantic)]
    ws = (weights.skills, weights.experience, weights.education, weights.semantic)
    total = sum(t * w for t, w in zip(tenths, ws))  # in (tenths x percent)
    return ((total + 50) // 100) / 10  # round half up back to tenths


def calculation_string(score: CandidateScore, weights: Weights) -> str:
    """Human-readable formula, e.g. 'Overall = (90×40 + 100×25 + 80×15 + 62.3×20) / 100 = 86.5'."""
    parts = [
        f"{fmt_num(score.skills)}×{weights.skills}",
        f"{fmt_num(score.experience)}×{weights.experience}",
        f"{fmt_num(score.education)}×{weights.education}",
        f"{fmt_num(score.semantic)}×{weights.semantic}",
    ]
    return f"Overall = ({' + '.join(parts)}) / 100 = {score.overall:.1f}"


# --------------------------------------------------------------------------
# Plain-English explanation
# --------------------------------------------------------------------------
def _years(n: float) -> str:
    n_txt = fmt_num(n)
    return f"{n_txt} year" if n_txt == "1" else f"{n_txt} years"


def explain(
    skill_match: SkillMatch,
    years: float,
    min_experience: float,
    level: int,
    min_level: int,
    semantic: float,
) -> str:
    """One jargon-free sentence describing why a candidate scored as they did."""
    n_req = len(skill_match.matched_required) + len(skill_match.missing_required)
    got = len(skill_match.matched_required)
    n_pref = len(skill_match.matched_preferred) + len(skill_match.missing_preferred)

    if n_req and got == n_req:
        skills = f"strong on skills ({got} of {n_req} required"
    elif n_req and got / n_req >= 0.5:
        skills = f"partial skills match ({got} of {n_req} required"
    else:
        skills = f"weak skills match ({got} of {n_req} required"
    if n_pref:
        skills += f", {len(skill_match.matched_preferred)} of {n_pref} preferred"
    skills += ")"

    if min_experience <= 0:
        exp = "no experience minimum applies"
    elif years >= min_experience:
        exp = "meets the experience minimum"
    elif years <= 0:
        exp = f"no experience yet against the {fmt_num(min_experience)}-year minimum"
    else:
        exp = f"{_years(min_experience - years)} short of the {fmt_num(min_experience)}-year minimum"

    gap = min_level - level
    if gap <= 0:
        edu = "meets the education requirement"
    elif gap == 1:
        edu = "one level below the education requirement"
    else:
        edu = f"{gap} levels below the education requirement"

    if semantic >= SEMANTIC_CLOSE:
        sem = "CV closely matches the role description"
    elif semantic >= SEMANTIC_RELATED:
        sem = "CV is broadly related to the role"
    else:
        sem = "CV describes different work"

    sentence = f"{skills}, {exp}, {edu}; {sem}."
    return sentence[0].upper() + sentence[1:]


def keyword_insights(skill_match: SkillMatch, semantic: float, skills: float, alias_hits: dict[str, str]) -> list[str]:
    """Reasons a plain keyword search would have missed or under-rated this candidate."""
    notes: list[str] = []
    for canonical, entered in alias_hits.items():
        notes.append(f'Listed "{entered}", which a keyword search for "{canonical}" would not find.')
    if semantic >= KEYWORD_MISS_SEMANTIC_MIN and skills < KEYWORD_MISS_SKILLS_MAX:
        n_req = len(skill_match.matched_required) + len(skill_match.missing_required)
        notes.append(
            f"Their CV describes this kind of work in different words: meaning match is "
            f"{fmt_num(semantic)} while only {len(skill_match.matched_required)} of {n_req} "
            f"required skills match by name."
        )
    return notes


# --------------------------------------------------------------------------
# Whole run
# --------------------------------------------------------------------------
def score_candidate(job: JobCriteria, cand: CandidateProfile, semantic_raw: float) -> CandidateScore:
    """Score one candidate given its pre-computed semantic similarity (0-100)."""
    sm = skills_score(cand.skills, job.required, job.preferred)
    exp = experience_score(cand.years_experience, job.min_experience)
    edu = education_score(cand.level, job.min_level)
    sem = round1(clamp(semantic_raw))
    overall = overall_score(sm.score, exp, edu, sem, job.weights)

    matched = set(sm.matched_required) | set(sm.matched_preferred)
    alias_hits = {
        c: entered
        for c, entered in cand.skills_as_entered.items()
        if c in matched and entered and entered.strip().lower() != c
    }
    return CandidateScore(
        candidate_id=cand.candidate_id,
        full_name=cand.full_name,
        skills=sm.score,
        experience=exp,
        education=edu,
        semantic=sem,
        overall=overall,
        skill_match=sm,
        alias_hits=alias_hits,
        explanation=explain(sm, cand.years_experience, job.min_experience, cand.level, job.min_level, sem),
        keyword_insights=keyword_insights(sm, sem, sm.score, alias_hits),
    )


def rank_scores(scores: list[CandidateScore]) -> list[CandidateScore]:
    """Sort by overall desc, skills desc, name A-Z (then id, for full determinism) and set rank."""
    ordered = sorted(scores, key=lambda s: (-s.overall, -s.skills, s.full_name.casefold(), s.candidate_id))
    for i, s in enumerate(ordered, start=1):
        s.rank = i
    return ordered


def score_candidates(
    job: JobCriteria,
    candidates: Sequence[CandidateProfile],
    embed: Callable[[Sequence[str]], np.ndarray],
) -> list[CandidateScore]:
    """Score and rank every candidate for one job.

    `embed` maps a list of texts to an (n, dim) matrix. The job description is
    encoded once; candidate summaries are encoded in one batch (and cached by
    the embedder between runs).
    """
    job.weights.validate()
    validate_skill_lists(job.required, job.preferred)
    if not candidates:
        return []
    job_vec = embed([job.description])[0]
    cand_mat = embed([c.resume_summary for c in candidates])
    sems = semantic_scores(job_vec, cand_mat)
    return rank_scores([score_candidate(job, c, float(s)) for c, s in zip(candidates, sems)])
