"""
Testa a logica de filtragem do endpoint webhook sem subir RabbitMQ real.
Usa monkeypatch para substituir `publish` por um stub que guarda o payload.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_and_published(monkeypatch):
    import app.webhook as webhook_mod
    import app.main as main_mod

    published: list[dict] = []
    muted: set[str] = set()

    async def fake_publish(message: dict) -> None:
        published.append(message)

    async def fake_is_muted(phone: str) -> bool:
        return phone in muted

    monkeypatch.setattr(webhook_mod, "publish", fake_publish)
    monkeypatch.setattr(webhook_mod.rds, "is_muted", fake_is_muted)
    return TestClient(main_mod.app), published, muted


def test_ignores_own_messages_from_n8n(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={"message": {"track_source": "n8n", "text": "x"}})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    assert pub == []


def test_ignores_ia_source(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={"message": {"track_source": "IA", "text": "x"}})
    assert r.json()["status"] == "ignored"
    assert pub == []


def test_ignores_when_no_phone(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={"message": {"text": "oi"}})
    assert r.json()["status"] == "ignored"
    assert pub == []


def test_queues_text_message(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={
        "message": {
            "sender_pn": "5511999990000@c.us",
            "senderName": "Fulano",
            "text": "quero info",
        }
    })
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert len(pub) == 1
    msg = pub[0]
    assert msg["phone"] == "5511999990000"
    assert msg["push_name"] == "Fulano"
    assert msg["msg"] == "quero info"
    assert msg["msg_type"] == "Conversation"


def test_queues_audio_message(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={
        "message": {
            "sender_pn": "5511888880000@c.us",
            "messageType": "audioMessage",
            "mediaUrl": "https://example.com/audio.ogg",
        }
    })
    assert r.json()["status"] == "queued"
    assert pub[0]["msg_type"] == "AudioMessage"
    assert pub[0]["media_url"] == "https://example.com/audio.ogg"


def test_ignores_unknown_message_type(client_and_published):
    client, pub, _muted = client_and_published
    r = client.post("/testslug", json={
        "message": {"sender_pn": "5511999990000@c.us", "messageType": "stickerMessage"}
    })
    assert r.json()["status"] == "ignored"
    assert pub == []


def test_health_endpoint(client_and_published):
    client, _pub, _muted = client_and_published
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_muted_phone_not_published(client_and_published):
    client, pub, muted = client_and_published
    muted.add("5511999990000")
    r = client.post("/testslug", json={
        "message": {
            "sender_pn": "5511999990000@c.us",
            "senderName": "Fulano",
            "text": "oi",
        }
    })
    assert r.status_code == 200
    assert r.json() == {"status": "ignored", "reason": "muted"}
    assert pub == []
