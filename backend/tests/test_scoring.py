"""Unit tests for the pure matching engine (no database, no web server)."""
import numpy as np
import pytest

from app.engine.scoring import (
    CandidateProfile,
    JobCriteria,
    Weights,
    WeightError,
    calculation_string,
    education_score,
    experience_score,
    explain,
    keyword_insights,
    overall_score,
    rank_scores,
    round1,
    score_candidate,
    score_candidates,
    semantic_scores,
    skills_score,
    validate_skill_lists,
)
from app.engine.skills import SkillNormaliser


# ---------------------------------------------------------------- skills
class TestSkillsScore:
    def test_all_required_and_preferred(self):
        m = skills_score(["python", "sql", "aws"], ["python", "sql"], ["aws"])
        assert m.score == 100.0
        assert m.matched_required == ["python", "sql"] and m.missing_required == []
        assert m.matched_preferred == ["aws"] and m.missing_preferred == []

    def test_partial_required_and_preferred(self):
        # 2 of 3 required -> 53.33..., 1 of 2 preferred -> 10  => 63.3
        m = skills_score(["python", "sql", "aws"], ["python", "sql", "spark"], ["aws", "dbt"])
        assert m.score == 63.3
        assert m.missing_required == ["spark"]
        assert m.missing_preferred == ["dbt"]

    def test_no_preferred_required_counts_full_100(self):
        m = skills_score(["python"], ["python", "sql"], [])
        assert m.score == 50.0

    def test_only_preferred_matched(self):
        m = skills_score(["aws"], ["python"], ["aws"])
        assert m.score == 20.0

    def test_nothing_matched(self):
        m = skills_score([], ["python"], ["aws"])
        assert m.score == 0.0

    def test_rounds_to_one_decimal(self):
        m = skills_score(["a"], ["a", "b", "c"], [])
        assert m.score == 33.3

    def test_required_list_order_preserved(self):
        m = skills_score(["c", "a"], ["a", "b", "c"], [])
        assert m.matched_required == ["a", "c"]


# ------------------------------------------------------------ experience
class TestExperience:
    @pytest.mark.parametrize(
        "years,minimum,expected",
        [(5, 3, 100.0), (3, 3, 100.0), (0, 0, 100.0), (2, 0, 100.0), (2, 4, 50.0), (1, 3, 33.3), (0, 5, 0.0)],
    )
    def test_formula(self, years, minimum, expected):
        assert experience_score(years, minimum) == expected


# ------------------------------------------------------------- education
class TestEducation:
    @pytest.mark.parametrize(
        "level,minimum,expected",
        [(4, 4, 100.0), (7, 4, 100.0), (3, 4, 75.0), (1, 4, 25.0), (4, 6, 66.7), (1, 1, 100.0)],
    )
    def test_formula(self, level, minimum, expected):
        assert education_score(level, minimum) == expected


# -------------------------------------------------------------- semantic
class TestSemantic:
    def test_identical_vectors_score_100(self):
        v = np.array([1.0, 0.0, 0.0])
        assert semantic_scores(v, np.array([[1.0, 0.0, 0.0]]))[0] == pytest.approx(100.0)

    def test_orthogonal_scores_0(self):
        v = np.array([1.0, 0.0])
        assert semantic_scores(v, np.array([[0.0, 1.0]]))[0] == pytest.approx(0.0)

    def test_negative_similarity_clipped_to_0(self):
        v = np.array([1.0, 0.0])
        assert semantic_scores(v, np.array([[-1.0, 0.0]]))[0] == 0.0

    def test_partial_similarity(self):
        v = np.array([1.0, 0.0])
        s = semantic_scores(v, np.array([[1.0, 1.0]]))[0]
        assert s == pytest.approx(70.7107, abs=1e-3)

    def test_empty_matrix(self):
        assert semantic_scores(np.array([1.0]), np.zeros((0, 1))).shape == (0,)


# --------------------------------------------------------------- overall
class TestOverall:
    def test_default_weights(self):
        # (90*40 + 100*25 + 75*15 + 60*20) / 100 = 84.25 -> 84.3 (half up)
        assert overall_score(90, 100, 75, 60, Weights()) == 84.3

    def test_brief_example_style(self):
        w = Weights(40, 25, 15, 20)
        assert overall_score(100, 100, 100, 100, w) == 100.0
        assert overall_score(0, 0, 0, 0, w) == 0.0

    def test_with_decimals(self):
        # (63.3*40 + 50*25 + 66.7*15 + 41.2*20) / 100 = 25.32+12.5+10.005+8.24 = 56.065 -> 56.1
        assert overall_score(63.3, 50, 66.7, 41.2, Weights()) == 56.1

    def test_custom_weights(self):
        assert overall_score(80, 20, 0, 0, Weights(50, 50, 0, 0)) == 50.0

    def test_round_half_up_not_bankers(self):
        assert round1(0.25) == 0.3
        assert round1(2.35) == 2.4
        assert round(0.25, 1) == 0.2  # python's default would be wrong

    def test_calculation_string(self):
        job = JobCriteria(["python"], [], 3, 4, "x" * 30)
        c = CandidateProfile(1, ["python"], 5, 4, "y" * 30, full_name="A")
        s = score_candidate(job, c, 62.34)
        assert calculation_string(s, job.weights) == "Overall = (100×40 + 100×25 + 100×15 + 62.3×20) / 100 = 92.5"


# --------------------------------------------------------------- weights
class TestWeights:
    def test_defaults_total_100(self):
        assert Weights().validate().total == 100

    def test_95_rejected_with_message(self):
        with pytest.raises(WeightError, match=r"Weights must add up to 100% \(now 95%\)"):
            Weights(40, 25, 15, 15).validate()

    def test_over_100_rejected(self):
        with pytest.raises(WeightError, match=r"now 105%"):
            Weights(45, 25, 15, 20).validate()

    def test_negative_rejected(self):
        with pytest.raises(WeightError):
            Weights(-10, 60, 30, 20).validate()

    def test_above_100_single_rejected(self):
        with pytest.raises(WeightError):
            Weights(110, -10, 0, 0).validate()

    def test_zero_weights_allowed_if_total_100(self):
        assert Weights(100, 0, 0, 0).validate().total == 100


# ---------------------------------------------------------- normaliser
class TestNormaliser:
    n = SkillNormaliser()

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("JS", "javascript"),
            ("  ts ", "typescript"),
            ("Py", "python"),
            ("K8s", "kubernetes"),
            ("Postgres", "postgresql"),
            ("ML", "machine learning"),
            ("Node JS", "node.js"),
            ("Amazon   Web  Services", "aws"),
            ("Power BI", "power bi"),
            ("C#", "c#"),
        ],
    )
    def test_aliases_and_cleanup(self, raw, expected):
        assert self.n.normalise(raw) == expected

    def test_collapse_spaces_and_lowercase(self):
        assert self.n.normalise("  Data    Modelling ") == "data modelling"

    def test_dedupe_after_alias(self):
        assert self.n.normalise_many(["JS", "JavaScript", "javascript ", "", "  "]) == ["javascript"]

    def test_keeps_original_entry(self):
        assert self.n.normalise_with_source(["JS", "Python"]) == [("javascript", "JS"), ("python", "Python")]

    def test_is_alias(self):
        assert self.n.is_alias("js") and not self.n.is_alias("javascript")


# ------------------------------------------------------- skill lists rule
class TestSkillListRules:
    def test_requires_one_required(self):
        with pytest.raises(ValueError, match="at least one required"):
            validate_skill_lists([], ["aws"])

    def test_preferred_cannot_repeat_required(self):
        with pytest.raises(ValueError, match="repeat required skills: python"):
            validate_skill_lists(["python"], ["python", "aws"])

    def test_ok(self):
        validate_skill_lists(["python"], ["aws"])


# --------------------------------------------------------------- ranking
def _cs(cid, name, overall, skills):
    from app.engine.scoring import CandidateScore, SkillMatch

    return CandidateScore(cid, name, skills, 0, 0, 0, overall, SkillMatch(skills, [], [], [], []), {})


class TestRanking:
    def test_overall_desc(self):
        r = rank_scores([_cs(1, "A", 50, 10), _cs(2, "B", 90, 10)])
        assert [s.candidate_id for s in r] == [2, 1] and [s.rank for s in r] == [1, 2]

    def test_tie_on_overall_uses_skills(self):
        r = rank_scores([_cs(1, "A", 80, 50), _cs(2, "B", 80, 70)])
        assert [s.candidate_id for s in r] == [2, 1]

    def test_tie_on_overall_and_skills_uses_name(self):
        r = rank_scores([_cs(1, "Zanele", 80, 50), _cs(2, "andile", 80, 50), _cs(3, "Bongani", 80, 50)])
        assert [s.full_name for s in r] == ["andile", "Bongani", "Zanele"]

    def test_ranks_start_at_one_and_are_consecutive(self):
        r = rank_scores([_cs(i, f"N{i}", i, 0) for i in range(5)])
        assert [s.rank for s in r] == [1, 2, 3, 4, 5]


# ------------------------------------------------------- explanations
class TestExplain:
    def test_strong_candidate(self):
        m = skills_score(["a", "b", "c"], ["a", "b", "c"], [])
        text = explain(m, 6, 5, 3, 4, 70)
        assert text == (
            "Strong on skills (3 of 3 required), meets the experience minimum, "
            "one level below the education requirement; CV closely matches the role description."
        )

    def test_short_on_experience(self):
        m = skills_score(["a"], ["a", "b"], ["c"])
        text = explain(m, 2, 5, 4, 4, 30)
        assert "Partial skills match (1 of 2 required, 0 of 1 preferred)" in text
        assert "3 years short of the 5-year minimum" in text
        assert "CV describes different work" in text

    def test_keyword_insight_alias(self):
        job = JobCriteria(["javascript"], [], 0, 1, "x" * 30)
        c = CandidateProfile(1, ["javascript"], 1, 1, "y" * 30, "A", {"javascript": "JS"})
        s = score_candidate(job, c, 10)
        assert s.alias_hits == {"javascript": "JS"}
        assert any('"JS"' in n for n in s.keyword_insights)

    def test_keyword_insight_semantic_rescue(self):
        m = skills_score([], ["a", "b"], [])
        notes = keyword_insights(m, 65, m.score, {})
        assert len(notes) == 1 and "different words" in notes[0]

    def test_no_insight_for_plain_match(self):
        m = skills_score(["a"], ["a"], [])
        assert keyword_insights(m, 65, m.score, {}) == []


# -------------------------------------------------------------- fairness
class TestFairness:
    def test_name_does_not_change_scores(self):
        job = JobCriteria(["python"], ["aws"], 3, 4, "Build data pipelines on AWS with Python")
        a = CandidateProfile(1, ["python"], 4, 4, "Builds pipelines in Python daily", full_name="Thabo Mokoena")
        b = CandidateProfile(2, ["python"], 4, 4, "Builds pipelines in Python daily", full_name="Emily Smith")
        sa, sb = score_candidate(job, a, 50), score_candidate(job, b, 50)
        assert (sa.skills, sa.experience, sa.education, sa.semantic, sa.overall) == (
            sb.skills, sb.experience, sb.education, sb.semantic, sb.overall
        )


# --------------------------------------------------------------- full run
class TestScoreCandidates:
    @staticmethod
    def embed(texts):
        # toy deterministic embedder: vowel counts
        return np.array([[t.count(v) + 0.1 for v in "aeiou"] for t in texts], dtype=float)

    def test_end_to_end_ranked(self):
        job = JobCriteria(["python", "sql"], ["aws"], 3, 4, "Python and SQL data engineer on AWS")
        cands = [
            CandidateProfile(1, ["python"], 1, 2, "Junior analyst who likes spreadsheets", "Poor Fit"),
            CandidateProfile(2, ["python", "sql", "aws"], 5, 5, "Senior data engineer, Python SQL AWS", "Strong Fit"),
        ]
        out = score_candidates(job, cands, self.embed)
        assert [s.full_name for s in out] == ["Strong Fit", "Poor Fit"]
        assert out[0].skills == 100.0 and out[0].rank == 1

    def test_invalid_weights_raise(self):
        job = JobCriteria(["python"], [], 0, 1, "x" * 30, Weights(40, 25, 15, 15))
        with pytest.raises(WeightError):
            score_candidates(job, [], self.embed)

    def test_no_candidates(self):
        job = JobCriteria(["python"], [], 0, 1, "x" * 30)
        assert score_candidates(job, [], self.embed) == []
