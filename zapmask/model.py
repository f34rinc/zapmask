"""Pure aggregation: block coverage and carrier ranking over Allocations."""
from collections import defaultdict


def decompose_range(start, end, width=4):
    """Minimal set of (fixed_prefix, free_count) tail-patterns exactly covering
    [start, end] inclusive over `width` digits. Each pattern is an aligned block of
    10**free_count consecutive numbers, emitted as literal `fixed` digits + free ?d."""
    patterns = set()
    cur = start
    while cur <= end:
        k = 0
        while True:
            size = 10 ** (k + 1)
            if cur % size == 0 and cur + size - 1 <= end:
                k += 1
            else:
                break
        size = 10 ** k
        fixed_len = width - k
        fixed = str(cur // size).zfill(fixed_len) if fixed_len > 0 else ""
        patterns.add((fixed, k))
        cur += size
    return patterns


def _normalize(patterns):
    """Drop any pattern whose block is fully contained in another (shorter-fixed) one."""
    out = set()
    for fixed, free in patterns:
        contained = any(
            (of, ofree) != (fixed, free) and len(of) < len(fixed) and fixed.startswith(of)
            for of, ofree in patterns
        )
        if not contained:
            out.add((fixed, free))
    return out


def _key(alloc, with_ddd):
    return (alloc.ddd, alloc.prefix) if with_ddd else alloc.prefix


def aggregate_coverage(allocations, with_ddd):
    cov = defaultdict(set)
    for a in allocations:
        cov[_key(a, with_ddd)] |= decompose_range(a.block_start, a.block_end)
    return {k: _normalize(v) for k, v in cov.items()}


def _count(alloc):
    return alloc.block_end - alloc.block_start + 1


def carrier_counts(allocations):
    counts = defaultdict(int)
    for a in allocations:
        counts[a.carrier] += _count(a)
    return dict(counts)


def rank_carriers(counts):
    return sorted(counts, key=lambda name: (-counts[name], name))


def key_carrier_counts(allocations, with_ddd):
    out = defaultdict(lambda: defaultdict(int))
    for a in allocations:
        out[_key(a, with_ddd)][a.carrier] += _count(a)
    return {k: dict(v) for k, v in out.items()}
