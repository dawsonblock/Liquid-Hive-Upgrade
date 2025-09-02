from starlette.testclient import TestClient
from unified_runtime.server import app


def test_chat_minimal():
    with TestClient(app) as client:
        r = client.post('/api/chat', params={'q': 'hello world'})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        assert 'answer' in data


def test_ws_status_channel_connect():
    with TestClient(app) as client:
        with client.websocket_connect('/api/ws') as ws:
            # Expect some initial status frames; drain a few messages non-blocking
            for _ in range(3):
                msg = ws.receive_json()
                assert isinstance(msg, dict)
                assert 'type' in msg
