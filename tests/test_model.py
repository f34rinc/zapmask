import pytest
from zapmask import model
from zapmask.parse import Allocation


def A(carrier="C", ddd="21", prefix="91932", s=0, e=9999):
    return Allocation(carrier, ddd, prefix, s, e)


def test_decompose_range_aligned():
    assert model.decompose_range(0, 9999) == {("", 4)}
    assert model.decompose_range(0, 999) == {("0", 3)}
    assert model.decompose_range(2000, 3999) == {("2", 3), ("3", 3)}


def test_decompose_range_sub_thousand():
    # a real STFC-style range that is NOT thousand-aligned
    assert model.decompose_range(1000, 1524) == {
        ("10", 2), ("11", 2), ("12", 2), ("13", 2), ("14", 2),
        ("150", 1), ("151", 1),
        ("1520", 0), ("1521", 0), ("1522", 0), ("1523", 0), ("1524", 0),
    }


def test_decompose_range_single_number():
    assert model.decompose_range(5, 5) == {("0005", 0)}


def test_decompose_range_exact_number_count():
    # the union of pattern sizes must equal the range length (no gaps/overlap)
    pats = model.decompose_range(1000, 1524)
    assert sum(10 ** free for _, free in pats) == 1524 - 1000 + 1


def test_aggregate_no_ddd_merges_prefix_across_ddds():
    allocs = [A(ddd="21", prefix="91932"), A(ddd="22", prefix="91932", s=0, e=999)]
    cov = model.aggregate_coverage(allocs, with_ddd=False)
    # ("0",3) from the 0-999 row is contained in ("",4) and normalized away
    assert cov == {"91932": {("", 4)}}


def test_aggregate_with_ddd_keeps_keys_distinct():
    allocs = [A(ddd="21", prefix="91932"), A(ddd="22", prefix="91932", s=0, e=999)]
    cov = model.aggregate_coverage(allocs, with_ddd=True)
    assert cov == {("21", "91932"): {("", 4)}, ("22", "91932"): {("0", 3)}}


def test_carrier_counts_and_rank():
    allocs = [
        A(carrier="CLARO", prefix="91111", s=0, e=9999),  # 10000
        A(carrier="TIM", prefix="92222", s=0, e=999),     # 1000
        A(carrier="TIM", prefix="93333", s=0, e=999),     # 1000
    ]
    counts = model.carrier_counts(allocs)
    assert counts == {"CLARO": 10000, "TIM": 2000}
    assert model.rank_carriers(counts) == ["CLARO", "TIM"]


def test_rank_breaks_ties_by_name():
    counts = {"B": 5, "A": 5}
    assert model.rank_carriers(counts) == ["A", "B"]


def test_key_carrier_counts():
    allocs = [
        A(carrier="CLARO", prefix="91111", s=0, e=9999),
        A(carrier="TIM", prefix="91111", s=0, e=999),
    ]
    kcc = model.key_carrier_counts(allocs, with_ddd=False)
    assert kcc == {"91111": {"CLARO": 10000, "TIM": 1000}}
