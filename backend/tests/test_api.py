import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.rules import RULE_LIBRARY, SNIPPETS, run_rules  # noqa: E402

MAYA, SAM, JORDAN, DANA = {"X-User-Id": "1"}, {"X-User-Id": "3"}, {"X-User-Id": "6"}, {"X-User-Id": "8"}


def ids(text, product="personal_loan", channel="display", source="internal"):
    return {h.rule_id for h in run_rules(text, product, channel, source, RULE_LIBRARY)}


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test.db"):
        os.remove("test.db")
    with TestClient(app) as c:
        yield c
    os.remove("test.db")


# ---------------------------------------------------------------- rules engine
def test_trigger_term_requires_apr():
    assert "REGZ-CE-TRIGGER" in ids("Pay just $289/month.")
    assert "REGZ-CE-TRIGGER" not in ids("Pay just $289/month. Rates from 7.99% APR.")


def test_prohibited_claims():
    found = ids("Guaranteed approval with no credit check. You're pre-approved!")
    assert {"UDAAP-GUARANTEED", "UDAAP-NO-CREDIT-CHECK", "FCRA-PREAPPROVED"} <= found


def test_required_rules_depend_on_channel_product_source():
    assert "TCPA-STOP" in ids("Finish your application", channel="sms")
    assert "TCPA-STOP" not in ids("Finish your application. Reply STOP to opt out", channel="sms")
    assert "MORT-NMLS" in ids("Prequalify today", product="mortgage", channel="landing_page")
    assert "MORT-NMLS" not in ids("Prequalify today", product="personal_loan", channel="landing_page")
    assert "FTC-AFFILIATE-DISCLOSURE" in ids("Great loans", source="affiliate")
    assert "FTC-AFFILIATE-DISCLOSURE" not in ids("Great loans", source="internal")


def test_intro_rate_needs_go_to_rate():
    assert "REGZ-INTRO-RATE" in ids("0% APR for 15 months!", product="credit_card")
    assert "REGZ-INTRO-RATE" not in ids("0% intro APR for 15 months, then 21.24% – 29.99% variable APR.", product="credit_card")


@pytest.mark.parametrize("snippet", SNIPPETS, ids=lambda s: s["id"])
def test_approved_disclosures_do_not_trip_rules(snippet):
    """Approved language must never be flagged, or the tool will train people to ignore it."""
    for product in ("personal_loan", "credit_card", "mortgage"):
        if "*" not in snippet["products"] and product not in snippet["products"]:
            continue
        hits = [h for h in run_rules(snippet["body"], product, "display", "internal", RULE_LIBRARY) if h.start is not None]
        assert not hits, f"{snippet['id']} trips {[h.rule_id for h in hits]} for {product}"


# ---------------------------------------------------------------- workflow
def test_full_review_cycle(client):
    pre = client.post("/api/precheck", headers=MAYA, json={
        "content": "Rates as low as 7.99%. Hurry!", "product": "personal_loan", "channel": "social"}).json()
    assert {f["rule_id"] for f in pre["findings"]} >= {"REGZ-RATE-AS-APR", "UDAAP-URGENCY"}
    assert pre["risk"]["tier"] in ("low", "medium", "high")

    sub = client.post("/api/submissions", headers=MAYA, json={
        "title": "Test post", "product": "personal_loan", "channel": "social",
        "content": "Rates as low as 7.99%. Hurry, limited time!"}).json()
    assert sub["status"] == "in_review" and sub["assignee"]["role"] in ("reviewer", "lead")
    findings = sub["versions"][0]["findings"]
    apr = next(f for f in findings if f["rule_id"] == "REGZ-RATE-AS-APR")
    urgency = [f for f in findings if f["rule_id"] == "UDAAP-URGENCY"]

    # submitters can't triage or decide
    assert client.patch(f"/api/findings/{apr['id']}", headers=MAYA, json={"status": "accepted"}).status_code == 403

    client.patch(f"/api/findings/{apr['id']}", headers=JORDAN, json={"status": "accepted"})
    for u in urgency:
        client.patch(f"/api/findings/{u['id']}", headers=JORDAN, json={"status": "dismissed"})

    # can't approve while a required change is outstanding; critical blocks conditional approval
    assert client.post(f"/api/submissions/{sub['id']}/decision", headers=JORDAN, json={"decision": "approve"}).status_code == 409
    assert client.post(f"/api/submissions/{sub['id']}/decision", headers=JORDAN, json={"decision": "approve_with_conditions"}).status_code == 409
    r = client.post(f"/api/submissions/{sub['id']}/decision", headers=JORDAN, json={"decision": "request_changes"})
    assert r.json()["status"] == "changes_requested"

    # resubmit with the APR fixed: that required change resolves, nothing is carried over
    v2 = client.post(f"/api/submissions/{sub['id']}/versions", headers=MAYA, json={
        "content": "Rates as low as 7.99% APR. Subject to credit approval. Hurry, limited time!"}).json()
    assert v2["current_version"] == 2 and v2["status"] == "in_review"
    v1f = {f["id"]: f for f in v2["versions"][0]["findings"]}
    assert v1f[apr["id"]]["status"] == "resolved"
    assert not [f for f in v2["versions"][1]["findings"] if f["status"] == "accepted"]

    done = client.post(f"/api/submissions/{sub['id']}/decision", headers=JORDAN, json={"decision": "approve"}).json()
    assert done["status"] == "approved" and done["approval_code"].startswith("CP-MKT-")
    assert [e["kind"] for e in done["events"]][-1] == "approve"


def test_unfixed_change_carries_forward(client):
    sub = client.post("/api/submissions", headers=SAM, json={
        "title": "Partner page", "product": "personal_loan", "channel": "landing_page",
        "content": "#ad ClearPath Financial loans. No credit check!"}).json()
    f = next(f for f in sub["versions"][0]["findings"] if f["rule_id"] == "UDAAP-NO-CREDIT-CHECK")
    reviewer = DANA if sub["assignee"]["role"] == "lead" else JORDAN
    client.patch(f"/api/findings/{f['id']}", headers=reviewer, json={"status": "accepted"})
    client.post(f"/api/submissions/{sub['id']}/decision", headers=reviewer, json={"decision": "request_changes"})
    v2 = client.post(f"/api/submissions/{sub['id']}/versions", headers=SAM, json={
        "content": "#ad ClearPath Financial loans. Still no credit check!"}).json()
    carried = next(x for x in v2["versions"][1]["findings"] if x["rule_id"] == "UDAAP-NO-CREDIT-CHECK")
    assert carried["status"] == "accepted" and carried["carried_from"] == f["id"]


def test_metrics_shape(client):
    m = client.get("/api/metrics").json()
    assert len(m["weeks"]) == 10 and m["partners"] and m["precision"]


def test_rule_that_still_fires_is_not_counted_as_fixed(client):
    sub = client.post("/api/submissions", headers=MAYA, json={
        "title": "Two payments", "product": "personal_loan", "channel": "display",
        "content": "Just $100/month. Or $200/month."}).json()
    reviewer = JORDAN if sub["assignee"]["role"] == "reviewer" else DANA
    for f in sub["versions"][0]["findings"]:
        if f["rule_id"] == "REGZ-CE-TRIGGER":
            client.patch(f"/api/findings/{f['id']}", headers=reviewer, json={"status": "accepted"})
    client.post(f"/api/submissions/{sub['id']}/decision", headers=reviewer, json={"decision": "request_changes"})

    v2 = client.post(f"/api/submissions/{sub['id']}/versions", headers=MAYA, json={"content": "Just $100/month."}).json()
    assert not [f for f in v2["versions"][0]["findings"] if f["status"] == "resolved"]
    assert "0 of 2 required changes fixed" in v2["events"][-1]["message"]
