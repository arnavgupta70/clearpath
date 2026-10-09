import json
from types import SimpleNamespace

import pytest

from app import ai


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def fake_response(payload: dict, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=json.dumps(payload))],
        usage=SimpleNamespace(input_tokens=10, cache_read_input_tokens=0, output_tokens=5),
    )


@pytest.fixture
def fake_claude(monkeypatch):
    def install(response):
        messages = FakeMessages(response)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        monkeypatch.setattr(ai, "_client", lambda: SimpleNamespace(beta=SimpleNamespace(messages=messages)))
        return messages

    return install


def test_locate_tolerates_case_and_whitespace():
    text = "Get instant  approval\ntoday"
    assert ai.locate("instant approval", text) == (4, 21)
    assert ai.locate("GET INSTANT", text) == (0, 11)
    assert ai.locate("not there", text) is None


def test_analyze_anchors_quotes_and_maps_fields(fake_claude):
    content = "Pay just $289/month. Our customers love us."
    messages = fake_claude(fake_response({
        "summary": "Risky.",
        "findings": [
            {"quote": "pay just $289/month", "title": "Payment claim", "category": "Accuracy", "severity": "major",
             "explanation": "x", "suggestion": "y", "related_rule_id": "REGZ-CE-TRIGGER"},
            {"quote": "", "title": "Missing disclosure", "category": "Accuracy", "severity": "minor",
             "explanation": "x", "suggestion": "y", "related_rule_id": ""},
        ],
    }))

    review = ai.analyze(content, "personal_loan", "email", "internal", None, [("UDAAP-URGENCY", "Hurry")])

    assert review.summary == "Risky."
    first, second = review.findings
    assert (first["start"], first["end"], first["quote"]) == (0, 19, "Pay just $289/month")
    assert first["source"] == "ai" and first["rule_id"] == "REGZ-CE-TRIGGER"
    assert second["quote"] is None and second["rule_id"] is None
    # the static rule library goes in a cacheable system block; the asset goes in the user turn
    assert messages.kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "UDAAP-URGENCY" in messages.kwargs["messages"][0]["content"]


def test_refusal_is_reported_not_parsed(fake_claude):
    fake_claude(fake_response({}, stop_reason="refusal"))
    with pytest.raises(ai.AIUnavailable):
        ai.analyze("text", "personal_loan", "email", "internal", None, [])


def test_disabled_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ai.AIUnavailable):
        ai.analyze("text", "personal_loan", "email", "internal", None, [])
