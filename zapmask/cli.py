"""Command-line interface: args, orchestration, file writing."""
import argparse
import sys

from zapmask import masks

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
    # orchestration is added in Task 11; for THIS task:
    return 0
