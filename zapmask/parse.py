"""Read an ANATEL numbering .txt dump into normalized Allocation records."""
from dataclasses import dataclass

SMP = "smp"
STFC = "stfc"

_NCOLS = {7: SMP, 13: STFC}

_IDX = {
    SMP:  {"carrier": 0, "ddd": 2, "prefix": 3, "start": 4, "end": 5, "status": 6},
    STFC: {"carrier": 0, "ddd": 3, "prefix": 4, "start": 5, "end": 6, "status": 12},
}


@dataclass(frozen=True)
class Allocation:
    carrier: str
    ddd: str
    prefix: str
    block_start: int
    block_end: int


def detect_service(ncols: int) -> str:
    try:
        return _NCOLS[ncols]
    except KeyError:
        raise ValueError(f"unrecognized column count {ncols}; expected 7 (SMP) or 13 (STFC)")
