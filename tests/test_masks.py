import pytest
from zapmask import masks


def test_stem_for_smp_lengths():
    assert masks.stem_for("smp", 9, "21", "91932") == "91932"
    assert masks.stem_for("smp", 11, "21", "91932") == "2191932"
    assert masks.stem_for("smp", 8, "21", "91932") == "1932"   # drop leading 9


def test_stem_for_stfc_lengths():
    assert masks.stem_for("stfc", 8, "21", "5201") == "5201"
    assert masks.stem_for("stfc", 10, "21", "5201") == "215201"


def test_fine_masks_full_and_partial():
    assert masks.fine_masks("91932", set(range(10))) == ["91932?d?d?d?d"]
    assert masks.fine_masks("5201", {0}) == ["52010?d?d?d"]
    assert masks.fine_masks("93333", {2, 3}) == ["933332?d?d?d", "933333?d?d?d"]


def test_coarse_free_digits():
    assert masks.coarse_free_digits(240000) == 6     # -> 1,000,000 masks
    assert masks.coarse_free_digits(1000000) == 6
    assert masks.coarse_free_digits(1000001) == 7


def test_coarse_stem_drops_trailing_digits():
    # smp length 9, base stem = prefix(5); free 6 -> drop 2 -> 3-digit stem
    stem, clamped = masks.coarse_stem("91932", free=6, min_keep=2)
    assert (stem, clamped) == ("919", False)


def test_coarse_stem_clamps_to_min_keep():
    # base 5 digits, free 8 would drop 4 -> only 1 left; min_keep 2 clamps
    stem, clamped = masks.coarse_stem("91932", free=8, min_keep=2)
    assert stem == "91"
    assert clamped is True


from zapmask.parse import Allocation


def _alloc(carrier, ddd, prefix, s=0, e=9999):
    return Allocation(carrier, ddd, prefix, s, e)


def test_build_fine_carrier_sorted():
    allocs = [
        _alloc("TIM", "21", "92222"),
        _alloc("CLARO", "21", "91111"),
        _alloc("CLARO", "21", "91112"),
    ]
    lines, stats = masks.build_masks(allocs, "smp", 9, "fine", 240000)
    # CLARO (2 prefixes = 20000) ranks before TIM (10000): its masks come first
    assert lines[0].startswith("91111") and lines[1].startswith("91112")
    assert lines[2].startswith("92222")
    assert stats.mask_count == 3
    assert stats.candidates == 30000            # 3 * 10^4
    assert stats.carrier_order == ["CLARO", "TIM"]


def test_build_coarse_groups_and_overcovers():
    allocs = [_alloc("CLARO", "21", "91111"), _alloc("CLARO", "21", "91129")]
    lines, stats = masks.build_masks(allocs, "smp", 9, "coarse", 240000)
    # free=6 -> 3-digit stems: both collapse to "911"
    assert lines == ["911?d?d?d?d?d?d"]
    assert stats.candidates == 1000000
    assert stats.assigned == 20000              # 2 full prefixes * 10000
    assert round(stats.overcover_pct, 1) == 98.0
