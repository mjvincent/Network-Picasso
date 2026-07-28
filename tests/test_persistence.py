from __future__ import annotations

from network_picasso import persistence


def test_persistence_disabled_without_database_url(monkeypatch):
    monkeypatch.delenv("NETWORK_PICASSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = persistence.status()

    assert result.enabled is False
    assert result.connected is False
    assert "disabled" in result.message.lower()


def test_retention_policy_documents_autosave_limit():
    policy = persistence.retention_policy()

    assert policy["autosaveLimit"] >= 1
    assert policy["milestonesRetained"] is True
    assert "autosave" in policy["description"].lower()


def test_retention_limit_env_override_is_safe(monkeypatch):
    monkeypatch.setenv("NETWORK_PICASSO_AUTOSAVE_RETENTION", "50")
    assert persistence.autosave_retention_limit() == 50

    monkeypatch.setenv("NETWORK_PICASSO_AUTOSAVE_RETENTION", "0")
    assert persistence.autosave_retention_limit() == 1

    monkeypatch.setenv("NETWORK_PICASSO_AUTOSAVE_RETENTION", "not-a-number")
    assert persistence.autosave_retention_limit() == 25


def test_retention_policy_accepts_settings_value():
    policy = persistence.retention_policy("12")

    assert policy["autosaveLimit"] == 12
