"""Interactive, colorful drag-and-drop front-end for zapmask.

Drop an ANATEL .txt onto this script (or onto run.py) and answer the
prompts. Everything funnels into zapmask.cli.run so the mask-building
and file-writing logic is shared with the argparse CLI.
"""
import argparse
import os
import re
import sys

from zapmask import cli, masks, parse


# --------------------------------------------------------------------------
# Color: zero-dependency ANSI. Enabled only on a real terminal, and off when
# NO_COLOR is set. On Windows 10+ we flip the console into virtual-terminal
# mode so the escape codes render instead of printing literally.
# --------------------------------------------------------------------------
_CODES = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "cyan": "\033[36m",
}
_COLOR = None  # resolved lazily


def _enable_windows_vt():
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11; ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = k.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if k.GetConsoleMode(handle, ctypes.byref(mode)):
            k.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _color_enabled():
    global _COLOR
    if _COLOR is None:
        if os.environ.get("NO_COLOR") is not None or not sys.stdout.isatty():
            _COLOR = False
        else:
            _enable_windows_vt()
            _COLOR = True
    return _COLOR


def paint(text, *names):
    if not _color_enabled():
        return text
    prefix = "".join(_CODES[n] for n in names)
    return f"{prefix}{text}{_CODES['reset']}"


def title(text):  return paint(text, "bold", "cyan")
def ok(text):     return paint(text, "green")
def warn(text):   return paint(text, "yellow")
def err(text):    return paint("error: " + text, "red")
def dim(text):    return paint(text, "dim")
def q(text):      return paint(text, "bold", "blue")


# --------------------------------------------------------------------------
# Prompt helpers (reader defaults to input so they are trivially testable)
# --------------------------------------------------------------------------
def clean_path(raw):
    """Normalize a path the user typed or dropped into the terminal.

    Dropping a file into a console often wraps the path in quotes (and
    adds a trailing space); strip that so open() gets a real path.
    """
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.strip()


def ask(prompt, default, reader=input):
    """Prompt showing the default in brackets; Enter accepts the default."""
    suffix = f" [{default}]" if default not in (None, "") else ""
    raw = reader(f"{q(prompt)}{dim(suffix)}: ")
    raw = raw.strip()
    return raw if raw else default


def ask_choice(prompt, default, choices, reader=input, out=print):
    """Ask until the answer is one of `choices` (Enter accepts default)."""
    while True:
        value = ask(f"{prompt} ({'/'.join(choices)})", default, reader)
        if value in choices:
            return value
        out(err(f"{value!r} is not one of {', '.join(choices)}"))


def ask_int(prompt, default, reader=input, out=print):
    """Ask until the answer parses as an integer (Enter accepts default)."""
    while True:
        value = ask(prompt, str(default), reader)
        try:
            return int(value)
        except ValueError:
            out(err(f"{value!r} is not a whole number"))


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def wants_wizard(argv):
    """True when we should launch the interactive wizard rather than the CLI.

    The wizard is for no-argument launches and drag-and-drop (a bare file
    path). Any option flag (starts with '-') means the caller is scripting
    the argparse CLI, so route there instead.
    """
    return not any(a.startswith("-") for a in argv)


def source_from_argv(argv):
    """First non-flag argument, cleaned - the file dropped onto the script."""
    for a in argv or []:
        if a and not a.startswith("-"):
            return clean_path(a)
    return None


def sources_from_argv(argv):
    """Every non-flag argument, cleaned - all files dropped onto the script."""
    return [clean_path(a) for a in (argv or []) if a and not a.startswith("-")]


def resolve_sources(argv, reader, out):
    """Return the source paths to process.

    Every file dropped on the launcher arrives as an argument, so all of
    them are processed. If nothing was dropped, prompt for one path.
    """
    paths = [p for p in sources_from_argv(argv) if p]
    if paths:
        return paths
    while True:
        raw = reader(f"{q('Drag the ANATEL .txt here, or paste its path')}: ")
        path = clean_path(raw)
        if not path:
            return []
        if os.path.isfile(path):
            return [path]
        out(err(f"file not found: {path}"))


def expand_ddd(answer, counts):
    """Resolve the area-code answer into a plain comma-separated list.

    Supports three token kinds, freely mixed with commas:
      * ``all``   -> every area code present in the file
      * ``A-B``   -> the present codes whose number falls in [A, B]
                     (bounds may be given in either order; codes absent
                     from the file are not invented)
      * ``NN``    -> a single code, passed through as typed
    Duplicates are collapsed while preserving first-seen order.
    """
    present = sorted(counts, key=lambda c: (int(c) if c.isdigit() else c))
    result, seen = [], set()

    def add(code):
        if code not in seen:
            seen.add(code)
            result.append(code)

    for token in answer.split(","):
        token = token.strip()
        if not token:
            continue
        if token.lower() == "all":
            for c in present:
                add(c)
        elif re.fullmatch(r"\d+\s*-\s*\d+", token):
            lo, hi = sorted(int(x) for x in token.split("-"))
            for c in present:
                if c.isdigit() and lo <= int(c) <= hi:
                    add(c)
        else:
            add(token)
    return ",".join(result)


def format_ddd_listing(counts, width=None, indent=2, gap=3):
    """Lay the area codes out as an aligned multi-column grid.

    A long comma-run is unreadable; a grid of right-aligned ``NN count``
    cells, wrapped to the terminal width, lets the eye scan down columns.
    Every code is shown - nothing is truncated.
    """
    codes = sorted(counts, key=lambda c: (int(c) if c.isdigit() else c))
    ddw = max(len(c) for c in codes)
    cntw = max(len(f"{counts[c]:,}") for c in codes)
    # Colour codes and counts differently so the eye can separate the two
    # columns at a glance. Padding is applied to the plain text first, then
    # wrapped in colour, so the (zero-width) escapes don't disturb alignment.
    cells = [paint(f"{c:>{ddw}}", "cyan") + "  " + paint(f"{counts[c]:>{cntw},}", "dim")
             for c in codes]
    cellw = ddw + 2 + cntw

    if width is None:
        try:
            import shutil
            width = shutil.get_terminal_size((80, 20)).columns
        except Exception:
            width = 80

    usable = max(1, width - indent)
    ncols = max(1, (usable + gap) // (cellw + gap))
    sep = " " * gap
    lines = []
    for i in range(0, len(cells), ncols):
        row = sep.join(cells[i:i + ncols])
        lines.append(" " * indent + row)
    return "\n".join(lines)


def build_namespace(src, ddd, length, granularity, coarse_target, out, service,
                    ddd_label=None):
    """Assemble the argparse.Namespace that cli.run consumes."""
    return argparse.Namespace(
        src=src, ddd=ddd, length=length or None, granularity=granularity,
        coarse_target=coarse_target, out=out, service=service,
        ddd_label=ddd_label,
    )


def process_source(src, reader, out):
    """Detect service, prompt options, and build masks for one file."""
    try:
        service, counts = parse.scan_ddds(src)
    except ValueError as exc:
        out(err(str(exc)))
        return 2
    if not counts:
        out(err("no active allocations found in that file"))
        return 2

    out(ok(f"Detected {service.upper()}  -  {len(counts)} area code(s) present"))
    out(format_ddd_listing(counts) + "\n")

    ddd = expand_ddd(
        ask("Area code(s) to build masks for  (e.g. 21,22 or 21-43, or 'all')",
            "all", reader),
        counts)
    # Tag the output 'all' when the selection covers every code in the file,
    # so the filename reads smp_all_... instead of a giant code list.
    selected = {d.strip() for d in ddd.split(",") if d.strip()}
    ddd_label = "all" if selected == set(counts) else None

    valid = ",".join(str(n) for n in sorted(masks.VALID_LENGTHS[service]))
    length = ask(f"Digit length(s)  (valid: {valid})",
                 str(masks.DEFAULT_LENGTH[service]), reader)

    granularity = ask_choice("Granularity", "both",
                             ("fine", "coarse", "both"), reader, out)

    coarse_target = ask_int("Coarse target (min base words per mask)",
                            240000, reader, out)

    out_dir = ask("Output directory", "masks", reader)

    ns = build_namespace(src=src, ddd=ddd, length=length, granularity=granularity,
                         coarse_target=coarse_target, out=out_dir, service=service,
                         ddd_label=ddd_label)

    out(dim("\nBuilding masks...\n"))
    rc = cli.run(ns)
    if rc == 0:
        out(ok(f"Done - masks written under {out_dir}/"))
    return rc


def run_wizard(argv=None, reader=input, out=print):
    if argv is None:
        argv = sys.argv[1:]

    out(title("zapmask - interactive mode"))
    out(dim("ANATEL phone-number hashcat masks. Drop a file, pick options, go.\n"))

    sources = resolve_sources(argv, reader, out)
    if not sources:
        out(err("no source file given; nothing to do"))
        return 2

    result = 0
    for i, src in enumerate(sources, 1):
        if len(sources) > 1:
            out(title(f"\n[{i}/{len(sources)}] {os.path.basename(src)}"))
        if not os.path.isfile(src):
            out(err(f"file not found: {src}"))
            result = result or 2
            continue
        rc = process_source(src, reader, out)
        result = result or rc
    return result


def hold_window(reader=input, interactive=None):
    """Keep a drag-and-drop console window open so the user can read the
    result (or the error) before it vanishes.

    When you drop a file on the script, the OS opens a throwaway console
    that closes the instant the process exits — so a failure just flashes
    by. Pause on a real interactive console; stay silent when piped or in
    a persistent terminal-less context so scripts and tests don't hang.
    """
    if interactive is None:
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        return
    try:
        reader(dim("\nPress Enter to close..."))
    except (EOFError, KeyboardInterrupt):
        pass


def main(argv=None):
    try:
        rc = run_wizard(argv)
    except (KeyboardInterrupt, EOFError):
        print()
        print(warn("cancelled"))
        rc = 130
    hold_window()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
