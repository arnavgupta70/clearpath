"""Risk score -> tier -> SLA and routing.

The score is a plain sum of labeled factors so a reviewer can see why something landed in
the priority queue, and so the weights are easy to argue about.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

PRODUCT_WEIGHT = {"mortgage": 25, "credit_card": 15, "personal_loan": 15}
CHANNEL_WEIGHT = {"sms": 10, "social": 10, "landing_page": 10, "email": 5, "display": 5, "search": 5, "direct_mail": 5}
SEVERITY_WEIGHT = {"critical": 12, "major": 5, "minor": 1}
SEVERITY_CAP = 36
AFFILIATE_WEIGHT = 15
WEAK_PARTNER_WEIGHT = 8  # partner's first-pass approval rate is below 50%
RESUBMISSION_CREDIT = -10  # a resubmission only needs the diff reviewed

TIER_THRESHOLDS = [(55, "high"), (30, "medium"), (0, "low")]
SLA_BUSINESS_DAYS = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class Assessment:
    score: int
    tier: str
    factors: list[dict]

    def due(self, start: datetime) -> datetime:
        return add_business_days(start, SLA_BUSINESS_DAYS[self.tier])


def assess(
    product: str,
    channel: str,
    source: str,
    severities: list[str],
    partner_first_pass: float | None = None,
    round_number: int = 1,
) -> Assessment:
    factors = [
        {"label": f"Product: {product.replace('_', ' ')}", "points": PRODUCT_WEIGHT[product]},
        {"label": f"Channel: {channel.replace('_', ' ')}", "points": CHANNEL_WEIGHT[channel]},
    ]
    if source == "affiliate":
        factors.append({"label": "Affiliate-produced content", "points": AFFILIATE_WEIGHT})
        if partner_first_pass is not None and partner_first_pass < 0.5:
            factors.append({"label": f"Partner first-pass approval {partner_first_pass:.0%}", "points": WEAK_PARTNER_WEIGHT})
    for severity, weight in SEVERITY_WEIGHT.items():
        count = severities.count(severity)
        if count:
            noun = "issue" if count == 1 else "issues"
            factors.append({"label": f"{count} {severity} pre-check {noun}", "points": min(count * weight, SEVERITY_CAP)})
    if round_number > 1:
        factors.append({"label": f"Resubmission (round {round_number})", "points": RESUBMISSION_CREDIT})

    score = max(0, min(100, sum(f["points"] for f in factors)))
    tier = next(tier for threshold, tier in TIER_THRESHOLDS if score >= threshold)
    return Assessment(score, tier, factors)


def add_business_days(start: datetime, days: int) -> datetime:
    day = start
    while days:
        day += timedelta(days=1)
        if day.weekday() < 5:
            days -= 1
    return day
