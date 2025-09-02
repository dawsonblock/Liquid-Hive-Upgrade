import importlib
import asyncio


def test_budget_status_endpoint_imports():
    # Ensure server module imports and app object exists
    mod = importlib.import_module('unified_runtime.server')
    assert hasattr(mod, 'app')


def test_budget_status_endpoint():
    server = importlib.import_module('unified_runtime.server')

    class DummyStatus:
        exceeded = False
        tokens_used = 123
        usd_spent = 0.45
        next_reset_utc = '2099-01-01T00:00:00Z'

    class DummyBudget:
        async def check_budget(self):
            return DummyStatus()

    class DummyConfig:
        max_oracle_tokens_per_day = 1000
        max_oracle_usd_per_day = 10.0
        budget_enforcement = 'hard'

    class DummyRouter:
        def __init__(self):
            self._budget_tracker = DummyBudget()
            self.config = DummyConfig()

    # Patch ds_router to our dummy, ensure we restore original after test
    original = getattr(server, 'ds_router', None)
    try:
        setattr(server, 'ds_router', DummyRouter())
        # Run the endpoint coroutine
        res = asyncio.get_event_loop().run_until_complete(server.get_budget_status())
        assert res.get('exceeded') is False
        assert res.get('tokens_used') == 123
        assert res.get('limits', {}).get('max_tokens') == 1000
    finally:
        setattr(server, 'ds_router', original)
