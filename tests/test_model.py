import pytest
from zapmask import model
from zapmask.parse import Allocation


def A(carrier="C", ddd="21", prefix="91932", s=0, e=9999):
    return Allocation(carrier, ddd, prefix, s, e)


def test_blocks_for_range_full_and_partial():
    assert model.blocks_for_range(0, 9999) == set(range(10))
    assert model.blocks_for_range(0, 999) == {0}
    assert model.blocks_for_range(2000, 3999) == {2, 3}


def test_blocks_for_range_rejects_unaligned():
    with pytest.raises(ValueError):
        model.blocks_for_range(0, 499)


def test_aggregate_no_ddd_merges_prefix_across_ddds():
    allocs = [A(ddd="21", prefix="91932"), A(ddd="22", prefix="91932", s=0, e=999)]
    cov = model.aggregate_coverage(allocs, with_ddd=False)
    assert cov == {"91932": set(range(10))}  # 22's block 0 already in 21's full set


def test_aggregate_with_ddd_keeps_keys_distinct():
    allocs = [A(ddd="21", prefix="91932"), A(ddd="22", prefix="91932", s=0, e=999)]
    cov = model.aggregate_coverage(allocs, with_ddd=True)
    assert cov == {("21", "91932"): set(range(10)), ("22", "91932"): {0}}


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
