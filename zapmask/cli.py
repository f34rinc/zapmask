"""Command-line interface: args, orchestration, file writing."""
import argparse
import os
import sys

from zapmask import masks
from zapmask import parse

_EPILOG = (
    "Getting the data (captcha-gated, download yourself):\n"
    "  https://easi.abrtelecom.com.br/nsapn/#/public/files\n\n"
    "Example:\n"
    "  zapmask --src SMP_20260829_GERAL.txt --ddd 21\n\n"
    "For authorized auditing of networks you own or are permitted to test."
)


def build_parser():
    p = argparse.ArgumentParser(
        prog="zapmask",
        description="ANATEL phone-number hashcat masks - mobile (SMP) + landline (STFC).",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--src", help="ANATEL numbering .txt (semicolon-delimited) from the EASI portal")
    p.add_argument("--ddd", help="area code(s), comma-separated, e.g. 21,22")
    p.add_argument("--length", help="digit lengths, comma-separated; default: SMP 9 / STFC 8")
    p.add_argument("--granularity", choices=["fine", "coarse", "both"], default="both",
                   help="fine = exact assigned keyspace; coarse = bigger GPU-saturating "
                        "masks; both (default) writes each")
    p.add_argument("--coarse-target", type=int, default=240000,
                   dest="coarse_target", help="min base words per coarse mask (default 240000)")
    p.add_argument("--out", default="masks", help="output directory (default: masks)")
    p.add_argument("--service", choices=["smp", "stfc"], help="override auto-detection")
    return p


def main(argv=None):
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ValueError as exc:
        return _fail(str(exc))


def _fail(msg):
    sys.stderr.write(f"zapmask: error: {msg}\n")
    return 2


def run(args):
    if not args.src:
        return _fail("--src is required")
    if not args.ddd:
        return _fail("--ddd is required")
    ddds = {d.strip() for d in args.ddd.split(",") if d.strip()}
    if args.coarse_target < 1:
        return _fail("--coarse-target must be a positive integer")

    service, allocations = parse.parse_file(args.src, ddds, service=args.service)

    if args.length:
        try:
            lengths = [int(x) for x in args.length.split(",")]
        except ValueError:
            return _fail("--length must be integers, e.g. 9,11")
    else:
        lengths = [masks.DEFAULT_LENGTH[service]]
    bad = [n for n in lengths if n not in masks.VALID_LENGTHS[service]]
    if bad:
        return _fail(f"length(s) {bad} invalid for {service}; "
                     f"valid: {sorted(masks.VALID_LENGTHS[service])}")

    grans = ["fine", "coarse"] if args.granularity == "both" else [args.granularity]
    os.makedirs(args.out, exist_ok=True)
    ddd_token = ddd_filename_token(ddds, label=getattr(args, "ddd_label", None))
    ddd_desc = ddd_header_desc(ddds, ddd_token)

    for length in lengths:
        for gran in grans:
            lines, stats = masks.build_masks(allocations, service, length, gran, args.coarse_target)
            if stats.mask_count == 0:
                print(f"no active allocations for {ddd_desc} in {os.path.basename(str(args.src))} "
                      f"({service} {length}-digit)")
                continue
            name = f"{service}_{ddd_token}_{length}digit_{gran}.hcmask"
            path = os.path.join(args.out, name)
            _write_file(path, lines, stats, args.src, ddd_desc)
            print(f"{name}: {stats.mask_count} masks / {stats.candidates:,} candidates "
                  f"({stats.overcover_pct:.1f}% over)")
            for w in stats.warnings:
                print(f"  warning: {w}")
    return 0


def ddd_filename_token(ddds, label=None):
    """Short, filename-safe tag for the selected area code(s).

    One code keeps its number; an explicit `label` (the wizard passes
    'all' when every code in the file was selected) wins; otherwise a
    multi-code selection collapses to 'multi' so filenames stay short.
    """
    ddds = sorted(ddds)
    if len(ddds) == 1:
        return ddds[0]
    if label:
        return label
    return "multi"


def ddd_header_desc(ddds, token):
    """Human-readable area-code line for the in-file header comment.

    Keeps the real list when it's short enough to be useful; falls back
    to a count when there are too many to list without bloating the file.
    """
    ddds = sorted(ddds)
    if len(ddds) == 1:
        return f"DDD {ddds[0]}"
    if len(ddds) <= 12:
        return f"DDD {token}: {','.join(ddds)}"
    return f"DDD {token} ({len(ddds)} area codes)"


def _write_file(path, lines, stats, src, ddd_desc):
    header = [
        f"# zapmask {stats.service} {stats.length}-digit {stats.granularity} | {ddd_desc}",
        f"# source: {os.path.basename(str(src))}",
        f"# carriers (biggest first): {', '.join(stats.carrier_order)}",
        f"# {stats.mask_count} masks / {stats.candidates:,} candidates "
        f"/ {stats.overcover_pct:.1f}% over-coverage",
        "# hashcat -m 22000 -a 3 <hash.hc22000> <this file>",
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(header) + "\n")
        fh.write("\n".join(lines) + "\n")
