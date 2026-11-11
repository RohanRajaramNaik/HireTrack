"""Unit tests for resource allocation maths (engine/allocation.py). No database."""
from datetime import date

import pytest

from app.engine.allocation import Booking, check_new_booking, load_on, overlaps, peak_load, utilisation_band

D = date


class TestOverlaps:
    def test_touching_ranges_overlap(self):
        assert overlaps(D(2026, 1, 1), D(2026, 1, 31), D(2026, 1, 31), D(2026, 2, 28))

    def test_separate_ranges(self):
        assert not overlaps(D(2026, 1, 1), D(2026, 1, 31), D(2026, 2, 1), D(2026, 2, 28))


class TestLoad:
    def test_load_on_day_sums_covering_bookings(self):
        b = [Booking(50, D(2026, 1, 1), D(2026, 3, 31)), Booking(30, D(2026, 2, 1), D(2026, 2, 28))]
        assert load_on(b, D(2026, 1, 15)) == 50
        assert load_on(b, D(2026, 2, 15)) == 80
        assert load_on(b, D(2026, 4, 1)) == 0

    def test_peak_finds_overlap_inside_range(self):
        b = [
            Booking(40, D(2026, 1, 1), D(2026, 1, 31)),
            Booking(40, D(2026, 1, 20), D(2026, 2, 10)),
            Booking(30, D(2026, 2, 5), D(2026, 2, 20)),
        ]
        peak, day = peak_load(b, D(2026, 1, 1), D(2026, 2, 28))
        assert peak == 80 and day == D(2026, 1, 20)

    def test_peak_after_a_booking_ends(self):
        b = [Booking(60, D(2026, 1, 1), D(2026, 1, 10)), Booking(20, D(2026, 1, 11), D(2026, 1, 31))]
        assert peak_load(b, D(2026, 1, 5), D(2026, 1, 31)) == (60, D(2026, 1, 5))

    def test_peak_empty(self):
        assert peak_load([], D(2026, 1, 1), D(2026, 1, 2)) == (0, None)


class TestCheckNewBooking:
    existing = [Booking(60, D(2026, 3, 1), D(2026, 5, 31), allocation_id=1)]

    def test_fits_exactly_100(self):
        check_new_booking(self.existing, Booking(40, D(2026, 4, 1), D(2026, 4, 30)))

    def test_rejects_over_100_with_clear_message(self):
        with pytest.raises(ValueError, match=r"110% on 01 Apr 2026 \(already 60% allocated\).*most you can add.*40%"):
            check_new_booking(self.existing, Booking(50, D(2026, 4, 1), D(2026, 4, 30)))

    def test_no_overlap_allows_full_time(self):
        check_new_booking(self.existing, Booking(100, D(2026, 6, 1), D(2026, 6, 30)))

    def test_editing_ignores_its_own_old_row(self):
        check_new_booking(self.existing, Booking(100, D(2026, 3, 1), D(2026, 5, 31)), ignore_id=1)

    def test_end_before_start(self):
        with pytest.raises(ValueError, match="End date"):
            check_new_booking([], Booking(10, D(2026, 2, 1), D(2026, 1, 1)))

    @pytest.mark.parametrize("pct", [0, 101, -5])
    def test_percent_range(self, pct):
        with pytest.raises(ValueError, match="between 1% and 100%"):
            check_new_booking([], Booking(pct, D(2026, 1, 1), D(2026, 1, 2)))


@pytest.mark.parametrize("pct,band", [(0, "bench"), (10, "light"), (49, "light"), (50, "healthy"), (89, "healthy"), (90, "full"), (100, "full")])
def test_bands(pct, band):
    assert utilisation_band(pct) == band
