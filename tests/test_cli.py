from zapmask import cli


def test_no_args_prints_help_and_exits_zero(capsys):
    rc = cli.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "easi.abrtelecom.com.br" in out
    assert "--ddd" in out


def test_parser_defaults():
    parser = cli.build_parser()
    ns = parser.parse_args(["--src", "f.txt", "--ddd", "21"])
    assert ns.ddd == "21"
    assert ns.granularity == "both"
    assert ns.coarse_target == 240000
    assert ns.out == "masks"


SMP_FILE = "\n".join([
    "# Nome;CNPJ;Codigo;Prefixo;Ini;Fim;Status",
    "CLARO;1;21;91932;0000;9999;1",
    "TIM;2;21;98888;0000;9999;1",
])


def test_run_writes_expected_files(tmp_path):
    src = tmp_path / "SMP_x.txt"
    src.write_text(SMP_FILE, encoding="utf-8")
    out = tmp_path / "masks"
    rc = cli.main(["--src", str(src), "--ddd", "21", "--out", str(out)])
    assert rc == 0
    fine = out / "smp_21_9digit_fine.hcmask"
    coarse = out / "smp_21_9digit_coarse.hcmask"
    assert fine.exists() and coarse.exists()
    body = [l for l in fine.read_text().splitlines() if not l.startswith("#")]
    assert "91932?d?d?d?d" in body
    assert "# hashcat -m 22000 -a 3" in fine.read_text()


def test_missing_ddd_errors(capsys):
    rc = cli.main(["--src", "f.txt"])
    assert rc == 2
    assert "--ddd" in capsys.readouterr().err


def test_invalid_length_for_service(tmp_path, capsys):
    src = tmp_path / "SMP_x.txt"
    src.write_text(SMP_FILE, encoding="utf-8")
    rc = cli.main(["--src", str(src), "--ddd", "21", "--length", "10"])
    assert rc == 2
    assert "length" in capsys.readouterr().err.lower()
