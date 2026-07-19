"""The HTTP contract.

These load the real models, so they are marked slow and excluded from the quick
suite (`pytest -m "not slow"`), which is what CI runs.
"""

import pytest

pytestmark = pytest.mark.slow

pytest.importorskip("spacy", reason="needs the NER models installed")
pytest.importorskip("transformers", reason="needs the NER models installed")

# These imports sit below the importorskip calls on purpose, so the module skips
# cleanly when the models are not installed. The noqa E402 markers below tell the
# linter that the late position is deliberate rather than a mistake.
from fastapi.testclient import TestClient  # noqa: E402

from anonymizer import api  # noqa: E402

SAMPLE = "Maria Lopez works at Contoso Ltd, reach her at m.lopez@example.org."


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as started:
        yield started


def test_health_reports_the_limits_in_force(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["models_loaded"] > 0
    assert body["limits"]["limited_text_chars"] == api.LIMITED_MAX_TEXT_CHARS
    assert body["limits"]["max_concurrency"] == api._MAX_CONCURRENT


def test_configs_are_listed_with_exactly_one_default(client):
    configs = client.get("/api/configs").json()
    assert len(configs) > 1
    assert sum(1 for c in configs if c["default"]) == 1


def test_anonymize_replaces_entities_and_reports_them(client):
    body = client.post("/api/anonymize", json={"text": SAMPLE}).json()
    assert "<PERSON>" in body["anonymized"]
    assert "<EMAIL_ADDRESS>" in body["anonymized"]
    assert "m.lopez@example.org" not in body["anonymized"]
    assert body["entity_counts"]["EMAIL_ADDRESS"] == 1


def test_entity_offsets_point_at_the_original_text(client):
    body = client.post("/api/anonymize", json={"text": SAMPLE}).json()
    for entity in body["entities"]:
        assert SAMPLE[entity["start"] : entity["end"]] == entity["text"]


def test_the_original_is_withheld_unless_asked_for(client):
    body = client.post("/api/anonymize", json={"text": SAMPLE}).json()
    assert body["original"] is None


def test_the_original_is_returned_when_requested(client):
    body = client.post(
        "/api/anonymize", json={"text": SAMPLE, "include_original": True}
    ).json()
    assert body["original"] == SAMPLE


def test_an_unknown_config_is_rejected_and_lists_the_valid_ones(client):
    response = client.post("/api/anonymize", json={"text": "hi", "config": "nope"})
    assert response.status_code == 422
    assert "spacy" in response.json()["detail"]


def test_empty_text_is_rejected(client):
    assert client.post("/api/anonymize", json={"text": ""}).status_code == 422


# --- deployment restrictions ------------------------------------------------


def test_a_disallowed_tier_is_refused(client, monkeypatch):
    monkeypatch.setattr(api, "_REQUIRED_TIERS", {"admin", "invited"})
    response = client.post(
        "/api/anonymize",
        json={"text": SAMPLE},
        headers={"X-Session-Tier": "anonymous"},
    )
    assert response.status_code == 403


def test_a_missing_tier_fails_closed(client, monkeypatch):
    # Behind the gateway the header is always set for /api, so its absence means
    # something is wrong and the request must not be served.
    monkeypatch.setattr(api, "_REQUIRED_TIERS", {"admin", "invited"})
    assert client.post("/api/anonymize", json={"text": SAMPLE}).status_code == 403


def test_an_allowed_tier_is_served(client, monkeypatch):
    monkeypatch.setattr(api, "_REQUIRED_TIERS", {"admin", "invited"})
    response = client.post(
        "/api/anonymize", json={"text": SAMPLE}, headers={"X-Session-Tier": "admin"}
    )
    assert response.status_code == 200


def test_tiers_are_unrestricted_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(api, "_REQUIRED_TIERS", set())
    assert client.post("/api/anonymize", json={"text": SAMPLE}).status_code == 200


# --- per-tier text length ---------------------------------------------------


def oversized() -> str:
    return "x" * (api.LIMITED_MAX_TEXT_CHARS + 1)


def test_a_long_submission_is_refused_for_an_invited_session(client, monkeypatch):
    monkeypatch.setattr(api, "_REQUIRED_TIERS", {"admin", "invited"})
    response = client.post(
        "/api/anonymize",
        json={"text": oversized()},
        headers={"X-Session-Tier": "invited"},
    )
    assert response.status_code == 413


def test_an_admin_session_has_no_length_limit(client, monkeypatch):
    monkeypatch.setattr(api, "_REQUIRED_TIERS", {"admin", "invited"})
    response = client.post(
        "/api/anonymize",
        json={"text": oversized()},
        headers={"X-Session-Tier": "admin"},
    )
    assert response.status_code == 200


def test_length_is_unlimited_when_no_tiers_are_configured(client, monkeypatch):
    # A local run (the way the project is handed over) applies no length limit.
    monkeypatch.setattr(api, "_REQUIRED_TIERS", set())
    response = client.post("/api/anonymize", json={"text": oversized()})
    assert response.status_code == 200
