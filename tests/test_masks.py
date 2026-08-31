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
