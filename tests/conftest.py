"""pytest configuration: register the ``live`` marker and gate it.

Tests marked ``@pytest.mark.live`` hit the real Anthropic API and are
skipped by default. To run them: ``uv run pytest --run-live`` (and
ensure ``ANTHROPIC_API_KEY`` is set).
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run tests marked @pytest.mark.live (real Anthropic API calls)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: marks tests that hit the real Anthropic API (default-skipped)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    if config.getoption("--run-live"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.exit(
                "--run-live was passed but ANTHROPIC_API_KEY is not set",
                returncode=2,
            )
        return  # don't skip anything
    skip_live = pytest.mark.skip(reason="live test — pass --run-live to enable")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
