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
