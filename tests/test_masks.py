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
