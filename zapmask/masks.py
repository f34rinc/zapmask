"""Pure hashcat-mask emission from aggregated coverage."""
import math

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


def fine_masks(stem, blocks):
    if blocks == set(range(10)):
        return [stem + "?d?d?d?d"]
    return [f"{stem}{b}?d?d?d" for b in sorted(blocks)]
