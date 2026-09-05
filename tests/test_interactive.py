from zapmask import cli, interactive, parse


SMP_FILE = "\n".join([
    "# Nome;CNPJ;Codigo;Prefixo;Ini;Fim;Status",
    "CLARO;1;21;91932;0000;9999;1",
    "TIM;2;21;98888;0000;9999;1",
    "VIVO;3;22;97777;0000;9999;1",
    "OI;4;21;96666;0000;9999;0",     # inactive: excluded
])


def test_scan_ddds_counts_active_allocations_per_ddd(tmp_path):
    src = tmp_path / "SMP_x.txt"
    src.write_text(SMP_FILE, encoding="utf-8")
    service, counts = parse.scan_ddds(str(src))
    assert service == "smp"
    assert counts == {"21": 2, "22": 1}


def test_clean_path_strips_surrounding_quotes_and_space():
    assert interactive.clean_path('  "C:\\a b\\SMP.txt" ') == "C:\\a b\\SMP.txt"
    assert interactive.clean_path("'/home/u/SMP.txt'") == "/home/u/SMP.txt"
    assert interactive.clean_path("plain.txt") == "plain.txt"


def test_ask_returns_default_when_user_presses_enter():
    assert interactive.ask("Length", "9", reader=lambda _prompt: "") == "9"


def test_ask_returns_typed_value():
    assert interactive.ask("Length", "9", reader=lambda _prompt: "11") == "11"


def _queued_reader(answers):
    q = list(answers)
    def reader(_prompt):
        return q.pop(0) if q else ""
    return reader


def test_run_wizard_writes_files_from_dropped_path(tmp_path):
    src = tmp_path / "SMP_x.txt"
    src.write_text(SMP_FILE, encoding="utf-8")
    out = tmp_path / "masks"
    # prompts in order: ddd, length, granularity, coarse-target, out
    reader = _queued_reader(["21", "", "", "", str(out)])
    rc = interactive.run_wizard([str(src)], reader=reader, out=lambda *_a, **_k: None)
    assert rc == 0
    assert (out / "smp_21_9digit_fine.hcmask").exists()
    assert (out / "smp_21_9digit_coarse.hcmask").exists()


def test_ask_choice_reasks_until_valid():
    reader = _queued_reader(["nope", "coarse"])
    msgs = []
    got = interactive.ask_choice("Gran", "both", ("fine", "coarse", "both"),
                                 reader=reader, out=msgs.append)
    assert got == "coarse"
    assert any("not one of" in m for m in msgs)


def test_ask_int_reasks_until_integer():
    reader = _queued_reader(["abc", "5000"])
    msgs = []
    got = interactive.ask_int("Target", 240000, reader=reader, out=msgs.append)
    assert got == 5000


def test_source_from_argv_skips_flags_and_cleans():
    assert interactive.source_from_argv(["--foo", '"a b.txt"']) == "a b.txt"
    assert interactive.source_from_argv(["-x"]) is None


def test_run_wizard_prompts_for_source_when_none_dropped(tmp_path):
    src = tmp_path / "STFC_x.txt"
    # 13-column STFC row, status col (index 12) = 1
    src.write_text("A;;;21;3232;0000;9999;;;;;;1\n", encoding="utf-8")
    out = tmp_path / "m"
    # first prompt is the source path, then ddd/length/gran/target/outdir
    reader = _queued_reader([str(src), "21", "", "", "", str(out)])
    rc = interactive.run_wizard([], reader=reader, out=lambda *_a, **_k: None)
    assert rc == 0
    assert (out / "stfc_21_8digit_fine.hcmask").exists()


def test_wants_wizard_true_for_dropped_file_or_no_args():
    assert interactive.wants_wizard([]) is True
    assert interactive.wants_wizard([r"C:\dumps\SMP.txt"]) is True


def test_wants_wizard_false_when_flags_present():
    assert interactive.wants_wizard(["--src", "f.txt", "--ddd", "21"]) is False


def test_hold_window_waits_when_interactive():
    calls = []
    interactive.hold_window(reader=lambda prompt: calls.append(prompt),
                            interactive=True)
    assert len(calls) == 1
    assert "Press Enter" in calls[0]


def test_hold_window_does_not_wait_when_not_interactive():
    calls = []
    interactive.hold_window(reader=lambda prompt: calls.append(prompt),
                            interactive=False)
    assert calls == []


def test_hold_window_survives_eof():
    def eof_reader(_prompt):
        raise EOFError
    # must not propagate: a closed stdin should not crash the pause
    interactive.hold_window(reader=eof_reader, interactive=True)


STFC_FILE = "A;;;21;3232;0000;9999;;;;;;1\n"


def test_expand_ddd_all_returns_every_present_code():
    counts = {"21": 5, "11": 2, "31": 9}
    assert interactive.expand_ddd("all", counts) == "11,21,31"
    assert interactive.expand_ddd("ALL", counts) == "11,21,31"


def test_expand_ddd_passes_explicit_list_through():
    counts = {"21": 5, "11": 2}
    assert interactive.expand_ddd("21", counts) == "21"


def test_run_wizard_processes_each_dropped_file(tmp_path):
    smp = tmp_path / "SMP_x.txt"
    smp.write_text(SMP_FILE, encoding="utf-8")
    stfc = tmp_path / "STFC_x.txt"
    stfc.write_text(STFC_FILE, encoding="utf-8")
    out = tmp_path / "m"
    # per file: ddd, length, granularity, coarse-target, out (blank ddd => all)
    reader = _queued_reader(["", "", "", "", str(out),      # SMP file
                             "", "", "", "", str(out)])      # STFC file
    rc = interactive.run_wizard([str(smp), str(stfc)],
                                reader=reader, out=lambda *_a, **_k: None)
    assert rc == 0
    assert list(out.glob("smp_*fine.hcmask"))
    assert list(out.glob("stfc_*fine.hcmask"))


def test_expand_ddd_range_limited_to_present_codes():
    counts = {"11": 1, "21": 5, "22": 3, "31": 2, "43": 9}
    # 21-43 spans the present 21,22,31,43 but not 11 (outside), and does
    # not invent absent codes like 25/30 in the gap
    assert interactive.expand_ddd("21-43", counts) == "21,22,31,43"


def test_expand_ddd_reversed_range_is_normalized():
    counts = {"21": 1, "22": 1, "23": 1}
    assert interactive.expand_ddd("23-21", counts) == "21,22,23"


def test_expand_ddd_mixes_ranges_lists_and_all():
    counts = {"11": 1, "21": 1, "22": 1, "31": 1, "41": 1}
    assert interactive.expand_ddd("21-22,41", counts) == "21,22,41"
    # explicit single code still passes through even if not present
    assert interactive.expand_ddd("21,99", counts) == "21,99"
    # duplicates collapsed
    assert interactive.expand_ddd("21-22,22", counts) == "21,22"


def test_format_ddd_listing_shows_all_codes_and_grouped_counts():
    counts = {"11": 66243, "12": 7416, "9": 5}
    grid = interactive.format_ddd_listing(counts, width=80)
    for code, n in counts.items():
        assert code in grid
        assert f"{n:,}" in grid
    # counts right-aligned to a common width (small count padded)
    assert f"{5:>6,}" in grid


def test_format_ddd_listing_wraps_into_columns_by_width():
    counts = {str(11 + i): i for i in range(12)}
    wide = interactive.format_ddd_listing(counts, width=1000)
    narrow = interactive.format_ddd_listing(counts, width=18)
    assert "\n" not in wide          # everything fits on one row
    assert "\n" in narrow            # forced to wrap
    # no data lost when wrapping
    for code in counts:
        assert code in narrow


def test_format_ddd_listing_colors_codes_and_counts_differently(monkeypatch):
    monkeypatch.setattr(interactive, "_COLOR", True)   # force color on
    grid = interactive.format_ddd_listing({"21": 5}, width=80)
    assert interactive._CODES["cyan"] in grid     # area codes
    assert interactive._CODES["dim"] in grid       # counts
    # plain digits still present (color codes wrap them, don't replace)
    assert "21" in grid and "5" in grid


def test_run_wizard_all_selection_names_file_all(tmp_path):
    smp = tmp_path / "SMP_x.txt"
    smp.write_text(SMP_FILE, encoding="utf-8")   # DDDs 21 and 22
    out = tmp_path / "m"
    reader = _queued_reader(["", "", "", "", str(out)])   # blank ddd => all
    interactive.run_wizard([str(smp)], reader=reader, out=lambda *_a, **_k: None)
    assert list(out.glob("smp_all_9digit_fine.hcmask"))


def test_run_wizard_partial_selection_names_file_multi(tmp_path):
    # three present codes, pick two -> 'multi'
    smp = tmp_path / "SMP_x.txt"
    smp.write_text("\n".join([
        "# h",
        "CLARO;1;21;91932;0000;9999;1",
        "TIM;2;22;98888;0000;9999;1",
        "VIVO;3;31;97777;0000;9999;1",
    ]), encoding="utf-8")
    out = tmp_path / "m"
    reader = _queued_reader(["21,22", "", "", "", str(out)])
    interactive.run_wizard([str(smp)], reader=reader, out=lambda *_a, **_k: None)
    assert list(out.glob("smp_multi_9digit_fine.hcmask"))
