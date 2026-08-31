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
