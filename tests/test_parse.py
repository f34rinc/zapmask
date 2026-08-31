import zapmask
import pytest
from zapmask import parse


def test_package_has_version():
    assert isinstance(zapmask.__version__, str)
    assert zapmask.__version__


def test_detect_service_by_column_count():
    assert parse.detect_service(7) == "smp"
    assert parse.detect_service(13) == "stfc"


def test_detect_service_rejects_unknown_width():
    with pytest.raises(ValueError):
        parse.detect_service(5)


SMP_LINES = [
    "# Nome;CNPJ;Codigo;Prefixo;Faixa Inicial;Faixa Final;Status",
    "CLARO;111;21;91932;0000;9999;1",
    "TIM;222;21;98888;0000;9999;1",
    "OLD;333;21;97777;0000;9999;0",       # inactive -> dropped
    "SP CARRIER;444;11;99999;0000;9999;1",  # wrong ddd -> dropped
]

STFC_LINES = [
    "# Nome;CNPJ;UF;Codigo;Prefixo;Ini;Fim;CNL;Loc;Area;Sig;Cod;Status",
    "OI;555;RJ;21;5201;0000;0999;1;RIO;RIO;RJO;1;1",
]


def test_parse_lines_smp_filters_and_normalizes():
    service, allocs = parse.parse_lines(SMP_LINES, ddds={"21"})
    assert service == "smp"
    assert [(a.carrier, a.prefix, a.block_start, a.block_end) for a in allocs] == [
        ("CLARO", "91932", 0, 9999),
        ("TIM", "98888", 0, 9999),
    ]


def test_parse_lines_stfc_uses_col_indices():
    service, allocs = parse.parse_lines(STFC_LINES, ddds={"21"})
    assert service == "stfc"
    a = allocs[0]
    assert (a.carrier, a.ddd, a.prefix, a.block_start, a.block_end) == ("OI", "21", "5201", 0, 999)


def test_parse_lines_service_override():
    # a 7-col line forced to smp still parses; override skips detection
    service, allocs = parse.parse_lines(SMP_LINES, ddds={"21"}, service="smp")
    assert service == "smp"
