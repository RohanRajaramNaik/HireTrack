"""Unit tests for the applicant pipeline rules (engine/pipeline.py). No database."""
import pytest

from app.engine import pipeline as p


class TestNextStage:
    @pytest.mark.parametrize(
        "stage,expected",
        [("applied", "screened"), ("screened", "interview"), ("interview", "offer"), ("offer", "hired"), ("hired", None)],
    )
    def test_flow_order(self, stage, expected):
        assert p.next_stage(stage) == expected

    def test_rejected_has_no_next(self):
        assert p.next_stage("rejected") is None


class TestAllowedMoves:
    def test_open_stage_can_advance_or_reject(self):
        assert p.allowed_moves("applied") == ["screened", "rejected"]
        assert p.allowed_moves("offer") == ["hired", "rejected"]

    def test_hired_is_final(self):
        assert p.allowed_moves("hired") == []

    def test_rejected_can_reopen_to_previous_stage(self):
        assert p.allowed_moves("rejected", reopen_to="interview") == ["interview"]

    def test_rejected_without_history_cannot_move(self):
        assert p.allowed_moves("rejected") == []

    def test_unknown_stage(self):
        with pytest.raises(p.StageError):
            p.allowed_moves("archived")


class TestCheckMove:
    def test_valid_forward_move(self):
        p.check_move("applied", "screened")  # no exception

    def test_cannot_skip_stages(self):
        with pytest.raises(p.StageError, match="next stage is Screened"):
            p.check_move("applied", "interview")

    def test_cannot_move_backwards(self):
        with pytest.raises(p.StageError):
            p.check_move("interview", "screened")

    def test_same_stage(self):
        with pytest.raises(p.StageError, match="already at"):
            p.check_move("offer", "offer")

    def test_hired_is_final(self):
        with pytest.raises(p.StageError, match="final"):
            p.check_move("hired", "rejected")

    def test_reject_from_any_open_stage(self):
        for stage in ("applied", "screened", "interview", "offer"):
            p.check_move(stage, "rejected")

    def test_reopen_only_to_the_rejected_from_stage(self):
        p.check_move("rejected", "screened", reopen_to="screened")
        with pytest.raises(p.StageError):
            p.check_move("rejected", "offer", reopen_to="screened")

    def test_unknown_target(self):
        with pytest.raises(p.StageError, match="Unknown"):
            p.check_move("applied", "shortlisted")


class TestFunnel:
    def test_reached_counts_include_later_stages(self):
        furthest = {"applied": 50, "screened": 30, "interview": 15, "offer": 3, "hired": 2}
        current = {"applied": 40, "screened": 20, "interview": 10, "offer": 3, "hired": 2, "rejected": 25}
        rows = {r["stage"]: r for r in p.funnel(furthest, current)}
        assert rows["applied"]["reached"] == 100
        assert rows["screened"]["reached"] == 50
        assert rows["hired"]["reached"] == 2
        assert rows["screened"]["conversion"] == 50.0
        assert rows["applied"]["conversion"] is None
        assert rows["rejected"]["current"] == 25 and rows["rejected"]["reached"] is None

    def test_empty(self):
        rows = p.funnel({}, {})
        assert [r["reached"] for r in rows[:5]] == [0, 0, 0, 0, 0]
        assert all(r["conversion"] is None for r in rows)

    def test_furthest_stage(self):
        assert p.furthest_stage("interview", None) == "interview"
        assert p.furthest_stage("rejected", "offer") == "offer"
        assert p.furthest_stage("rejected", None) == "applied"
