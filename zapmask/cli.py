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
    p.add_argument("--granularity", choices=["fine", "coarse", "both"], default="both")
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
    ddd_token = "-".join(sorted(ddds))

    for length in lengths:
        for gran in grans:
            lines, stats = masks.build_masks(allocations, service, length, gran, args.coarse_target)
            name = f"{service}_{ddd_token}_{length}digit_{gran}.hcmask"
            path = os.path.join(args.out, name)
            _write_file(path, lines, stats, args.src, ddd_token)
            print(f"{name}: {stats.mask_count} masks / {stats.candidates:,} candidates "
                  f"({stats.overcover_pct:.1f}% over)")
            for w in stats.warnings:
                print(f"  warning: {w}")
    return 0


def _write_file(path, lines, stats, src, ddd_token):
    header = [
        f"# zapmask {stats.service} {stats.length}-digit {stats.granularity} | DDD {ddd_token}",
        f"# source: {os.path.basename(str(src))}",
        f"# carriers (biggest first): {', '.join(stats.carrier_order)}",
        f"# {stats.mask_count} masks / {stats.candidates:,} candidates "
        f"/ {stats.overcover_pct:.1f}% over-coverage",
        "# hashcat -m 22000 -a 3 <hash.hc22000> <this file>",
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(header) + "\n")
        fh.write("\n".join(lines) + "\n")
