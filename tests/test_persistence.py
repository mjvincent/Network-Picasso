from __future__ import annotations

from network_picasso import persistence


def test_persistence_disabled_without_database_url(monkeypatch):
    monkeypatch.delenv("NETWORK_PICASSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = persistence.status()

    assert result.enabled is False
    assert result.connected is False
    assert "disabled" in result.message.lower()
