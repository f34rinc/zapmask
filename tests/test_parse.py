import zapmask


def test_package_has_version():
    assert isinstance(zapmask.__version__, str)
    assert zapmask.__version__
