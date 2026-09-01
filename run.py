#!/usr/bin/env python3
"""Convenience shim so you can run zapmask without installing it or
remembering the -m syntax:

    python run.py --src SMP_20260829_GERAL.txt --ddd 21

It is exactly equivalent to `python -m zapmask ...`.
"""
from zapmask.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
