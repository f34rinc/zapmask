"""Pure hashcat-mask emission from aggregated coverage."""
import math
from dataclasses import dataclass, field
from collections import defaultdict

from zapmask import model

VALID_LENGTHS = {"smp": {9, 11, 8}, "stfc": {8, 10}}
DEFAULT_LENGTH = {"smp": 9, "stfc": 8}

_DDD_LENGTHS = {11, 10}   # lengths that carry the DDD


def stem_for(service, length, ddd, prefix):
    if service == "smp" and length == 8:
        base = prefix[1:]              # legacy: drop leading 9
    else:
        base = prefix
    if length in _DDD_LENGTHS:
        return ddd + base
    return base


def fine_masks(stem, patterns):
    return [f"{stem}{fixed}{'?d' * free}" for fixed, free in sorted(patterns)]


def coarse_free_digits(target):
    return math.ceil(math.log10(target))


def coarse_stem(base_stem, free, min_keep):
    drop = free - 4                      # fine tail is 4 free digits
    keep = len(base_stem) - drop
    clamped = False
    if keep < min_keep:
        keep = min_keep
        clamped = True
    return base_stem[:keep], clamped


@dataclass
class MaskStats:
    service: str
    length: int
    granularity: str
    mask_count: int
    candidates: int
    assigned: int
    overcover_pct: float
    carrier_order: list
    warnings: list = field(default_factory=list)


def _min_keep(length):
    return 3 if length in _DDD_LENGTHS else 2   # keep DDD + >=1, or >=2 prefix digits


def build_masks(allocations, service, length, granularity, coarse_target):
    with_ddd = length in _DDD_LENGTHS
    coverage = model.aggregate_coverage(allocations, with_ddd)
    kcc = model.key_carrier_counts(allocations, with_ddd)
    order = model.rank_carriers(model.carrier_counts(allocations))
    rank = {name: i for i, name in enumerate(order)}

    def key_parts(key):
        return key if with_ddd else ("", key)  # (ddd, prefix); ddd unused when no-DDD

    def dominant(counter):
        return min(counter, key=lambda n: (rank[n], n))

    assigned = sum(10 ** free for pats in coverage.values() for (fixed, free) in pats)
    warnings_out = []

    if granularity == "fine":
        rows = []
        for key, blocks in coverage.items():
            ddd, prefix = key_parts(key)
            stem = stem_for(service, length, ddd, prefix)
            rows.append((rank[dominant(kcc[key])], key, fine_masks(stem, blocks)))
        rows.sort(key=lambda r: (r[0], r[1]))
        lines = [m for _, _, ms in rows for m in ms]
    else:
        free = coarse_free_digits(coarse_target)
        groups = defaultdict(lambda: defaultdict(int))
        for key in coverage:
            ddd, prefix = key_parts(key)
            base = stem_for(service, length, ddd, prefix)
            gstem, clamped = coarse_stem(base, free, _min_keep(length))
            if clamped and not warnings_out:
                warnings_out.append(
                    f"coarse-target {coarse_target} clamped; over-coverage is high"
                )
            for name, cnt in kcc[key].items():
                groups[gstem][name] += cnt
        ordered = sorted(groups, key=lambda g: (rank[dominant(groups[g])], g))
        lines = [g + "?d" * (length - len(g)) for g in ordered]

    # Candidate count per mask is 10^(number of free-digit tokens), not a flat
    # per-mask constant: fine partial-block masks may carry only 3 free digits
    # ("stem+b+?d?d?d"), and a clamped coarse stem needs more free digits than
    # `free` to reach the target length. Summing 10**('?' count) per line keeps
    # both cases correct.
    candidates = sum(10 ** ln.count("?") for ln in lines)

    overcover = 100.0 * (candidates - assigned) / candidates if candidates else 0.0
    stats = MaskStats(service, length, granularity, len(lines), candidates,
                      assigned, overcover, order, warnings_out)
    return lines, stats
