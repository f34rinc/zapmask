#!/usr/bin/env python3
"""Drag an ANATEL .txt onto this file to launch the interactive wizard,
or run it with flags for the classic command-line interface:

    python run.py                          # interactive wizard
    python run.py SMP_20260829_GERAL.txt   # wizard, file pre-filled (drag-drop)
    python run.py --src SMP_...txt --ddd 21 # classic CLI (same as python -m zapmask)
"""
import sys

from zapmask import cli, interactive

if __name__ == "__main__":
    argv = sys.argv[1:]
    if interactive.wants_wizard(argv):
        raise SystemExit(interactive.main(argv))
    raise SystemExit(cli.main(argv))
