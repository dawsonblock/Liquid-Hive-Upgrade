import asyncio

import pytest

from internet_agent_advanced.main_tool import internet_fetch
from src.logging_config import get_logger


@pytest.mark.skip(reason="Requires internet access - not suitable for CI")
def test_fetch_smoke():
    res = asyncio.run(internet_fetch(["https://example.com"]))
    assert "trusted" in res.model_dump()
