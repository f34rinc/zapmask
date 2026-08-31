"""Pure aggregation: block coverage and carrier ranking over Allocations."""
from collections import defaultdict


def blocks_for_range(start, end):
    if start % 1000 != 0 or end % 1000 != 999:
        raise ValueError(f"range {start}-{end} is not thousand-aligned")
    return set(range(start // 1000, end // 1000 + 1))


def _key(alloc, with_ddd):
    return (alloc.ddd, alloc.prefix) if with_ddd else alloc.prefix


def aggregate_coverage(allocations, with_ddd):
    cov = defaultdict(set)
    for a in allocations:
        cov[_key(a, with_ddd)] |= blocks_for_range(a.block_start, a.block_end)
    return dict(cov)
