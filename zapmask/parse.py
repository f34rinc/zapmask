"""Read an ANATEL numbering .txt dump into normalized Allocation records."""
import os
import warnings
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


def _data_rows(lines):
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        yield line.split(";")


def parse_lines(lines, ddds, service=None):
    allocations = []
    resolved = service
    for cols in _data_rows(lines):
        if resolved is None:
            resolved = detect_service(len(cols))
        idx = _IDX[resolved]
        if cols[idx["status"]].strip() != "1":
            continue
        ddd = cols[idx["ddd"]].strip()
        if ddd not in ddds:
            continue
        allocations.append(Allocation(
            carrier=cols[idx["carrier"]].strip(),
            ddd=ddd,
            prefix=cols[idx["prefix"]].strip(),
            block_start=int(cols[idx["start"]]),
            block_end=int(cols[idx["end"]]),
        ))
    if resolved is None:
        raise ValueError("no data rows found in input")
    return resolved, allocations


def parse_file(path, ddds, service=None):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        resolved, allocations = parse_lines(fh, ddds, service=service)
    name = os.path.basename(str(path)).upper()
    hinted = SMP if name.startswith("SMP_") else STFC if name.startswith("STFC_") else None
    if hinted is not None and hinted != resolved:
        warnings.warn(
            f"filename prefix suggests {hinted} but content parsed as {resolved}",
            UserWarning,
        )
    return resolved, allocations
