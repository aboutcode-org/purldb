import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run_live_fetch",
        action="store_true",
        default=False,
        help="run live_fetch tests",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "live_fetch: mark test as live_fetch to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run_live_fetch"):
        return
    skip_live_fetch = pytest.mark.skip(reason="need --run_live_fetch option to run")
    for item in items:
        if "live_fetch" in item.keywords:
            item.add_marker(skip_live_fetch)
