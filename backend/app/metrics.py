from collections import Counter, defaultdict
from datetime import timedelta
from statistics import median

from sqlmodel import Session, select

from .models import Finding, FindingStatus, Submission, utcnow
from .workflow import APPROVED, DECIDED

# the reviewer agreed with it: still required, or required and since fixed
CONFIRMED = (FindingStatus.ACCEPTED, FindingStatus.RESOLVED)


def first_pass_rate(subs: list[Submission]) -> float | None:
    decided = [s for s in subs if s.status in DECIDED]
    if not decided:
        return None
    return sum(s.status in APPROVED and s.current_version == 1 for s in decided) / len(decided)


def median_days(subs: list[Submission]) -> float | None:
    days = [(s.decided_at - s.created_at).total_seconds() / 86400 for s in subs if s.decided_at]
    return round(median(days), 1) if days else None


def rule_precision(findings: list[Finding]) -> dict[str, dict]:
    # Of the hits a reviewer actually looked at, how many did they agree with? Claude counts as one "rule".
    # Carried-forward copies are skipped so one decision isn't counted per version.
    stats: dict[str, dict] = defaultdict(lambda: {"hits": 0, "confirmed": 0})
    for f in findings:
        if f.carried_from or f.source == "reviewer" or f.status == FindingStatus.OPEN:
            continue
        row = stats["AI" if f.source == "ai" else f.rule_id]
        row["hits"] += 1
        if f.status in CONFIRMED:
            row["confirmed"] += 1
    for row in stats.values():
        row["precision"] = round(row["confirmed"] / row["hits"], 3)
    return dict(stats)


def compute(session: Session) -> dict:
    now = utcnow()
    subs = session.exec(select(Submission)).all()
    findings = session.exec(select(Finding)).all()

    last_30 = [s for s in subs if s.decided_at and s.decided_at >= now - timedelta(days=30)]
    prior_30 = [s for s in subs if s.decided_at and now - timedelta(days=60) <= s.decided_at < now - timedelta(days=30)]

    # whole weeks only, otherwise the current week always looks like a drop
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weeks = []
    for i in range(10, 0, -1):
        start, end = monday - timedelta(weeks=i), monday - timedelta(weeks=i - 1)
        decided = [s for s in subs if s.decided_at and start <= s.decided_at < end]
        weeks.append({"week": start, "median_days": median_days(decided), "first_pass_rate": first_pass_rate(decided)})

    confirmed = defaultdict(list)
    for f in findings:
        if f.status in CONFIRMED and not f.carried_from:
            confirmed[f.submission_id].append(f.title)
    by_partner = defaultdict(list)
    for s in subs:
        by_partner[s.partner or "ClearPath (internal)"].append(s)
    partners = []
    for name, partner_subs in by_partner.items():
        issues = Counter(title for s in partner_subs for title in confirmed[s.id])
        partners.append({
            "partner": name,
            "submissions": len(partner_subs),
            "first_pass_rate": first_pass_rate(partner_subs),
            "top_issue": issues.most_common(1)[0][0] if issues else None,
        })
    partners.sort(key=lambda p: p["first_pass_rate"] or 0)

    return {
        "kpis": {
            "median_days": [median_days(last_30), median_days(prior_30)],
            "first_pass_rate": [first_pass_rate(last_30), first_pass_rate(prior_30)],
        },
        "weeks": weeks,
        "partners": partners,
        "precision": [{"rule_id": rule_id, **row} for rule_id, row in rule_precision(findings).items()],
    }
