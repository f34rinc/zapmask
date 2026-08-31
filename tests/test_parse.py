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
