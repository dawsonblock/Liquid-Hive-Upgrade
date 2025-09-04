import asyncio
from internet_agent_advanced.main_tool import internet_fetch


def test_fetch_smoke():
    res = asyncio.run(internet_fetch(["https://example.com"]))
    assert "trusted" in res.model_dump()
