"""Demo data. It's created by running the real workflow functions with backdated timestamps,
so it always matches how the app actually behaves.

The Claude findings below are canned, so the demo works without an API key.
"""

import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from itertools import accumulate

from sqlmodel import Session, select

from . import ai
from .models import Submission, User, utcnow
from .rules import SNIPPETS
from .workflow import create_submission, current_version, decide, findings_for, record_ai_review, resubmit, triage, version_findings

SNIPPET = {s["id"]: s["body"] for s in SNIPPETS}

USERS = [
    dict(name="Maya Chen", title="Growth Marketing Manager", role="marketer", org="ClearPath Financial", color="#0e7490"),
    dict(name="Luis Ortega", title="Lifecycle Marketing Lead", role="marketer", org="ClearPath Financial", color="#7c3aed"),
    dict(name="Sam Patel", title="Partnerships Manager", role="affiliate", org="CreditHero", color="#c2410c"),
    dict(name="Erin Brooks", title="Content Lead", role="affiliate", org="LoanLadder", color="#15803d"),
    dict(name="Kofi Mensah", title="Media Buyer", role="affiliate", org="RateWise Media", color="#b45309"),
    dict(name="Jordan Lee", title="Marketing Compliance Analyst", role="reviewer", org="ClearPath Compliance", color="#1d4ed8"),
    dict(name="Alex Kim", title="Marketing Compliance Analyst", role="reviewer", org="ClearPath Compliance", color="#be185d"),
    dict(name="Dana Whitfield", title="Senior Compliance Counsel", role="lead", org="ClearPath Compliance", color="#334155"),
]


@dataclass
class AINote:
    quote: str
    title: str
    severity: str
    explanation: str
    suggestion: str
    rule_id: str | None = None


class Demo:
    def __init__(self, session: Session):
        self.session = session
        self.users = {u.name.split()[0]: u for u in session.exec(select(User))}

    def submit(self, who: str, at: datetime, title: str, product: str, channel: str, content: str, **extra) -> Submission:
        sub = create_submission(self.session, self.users[who], title=title, product=product, channel=channel,
                                content=content, at=at, **extra)
        self.session.flush()
        return sub

    def ai_review(self, sub: Submission, summary: str, *notes: AINote) -> None:
        version = current_version(self.session, sub)
        findings = [ai.finding(version.content, **asdict(note)) for note in notes]
        record_ai_review(self.session, version, ai.Review(summary, findings), version.created_at + timedelta(seconds=40))
        self.session.flush()

    def review(self, sub: Submission, require=(), dismiss=()) -> None:
        # match findings by rule id or title
        for finding in version_findings(self.session, current_version(self.session, sub)):
            keys = {finding.rule_id, finding.title}
            if finding.status != "open":
                continue
            if keys & set(require):
                triage(self.session, finding, "accepted")
            elif keys & set(dismiss):
                triage(self.session, finding, "dismissed")
        self.session.flush()

    def decide(self, sub: Submission, at: datetime, decision: str, note: str | None = None) -> None:
        decide(self.session, sub, decision, self.session.get(User, sub.assignee_id), note, at)
        self.session.flush()

    def revise(self, sub: Submission, at: datetime, content: str, notes: str | None = None) -> None:
        resubmit(self.session, sub, content, notes, at)
        self.session.flush()


def active_work(demo: Demo, now: datetime) -> None:
    def hours_ago(hours: float) -> datetime:
        return now - timedelta(hours=hours)

    # in review, lots to triage (Jordan)
    sub = demo.submit("Maya", hours_ago(20), "Debt consolidation — October nurture email", "personal_loan", "email",
        "Subject: {first_name}, one payment instead of five\n\n"
        "Juggling multiple credit card bills? Roll them into one personal loan from ClearPath Financial and pay just $289/month.\n\n"
        "Our customers love having the lowest rates around, and checking your rate won't affect your credit score.\n\n"
        "Borrow $5,000–$50,000 and pay it off in 36 months. Apply in minutes and get funds as soon as the next business day after approval.\n\n"
        "Hurry, this offer won't last.\n\n"
        "[Check my rate]\n\n"
        "ClearPath Financial, 1200 Market Street, Suite 400, Charlotte, NC 28202.")
    demo.ai_review(sub,
        "High risk as written. $289/month triggers the full Reg Z disclosures and doesn't match any amount in the "
        "$5,000–$50,000 range. Tie it to a representative example with an amount, term and APR.",
        AINote("pay just $289/month", "Payment example doesn't match any stated loan", "major",
               "$289/month isn't tied to a loan amount, so readers will assume it applies across the whole $5,000–$50,000 range. "
               "Over 36 months it only works for roughly a $9,000–$10,000 loan.",
               "Use the approved example: “a $10,000 loan with a 36-month term at 14.99% APR has 36 monthly payments of $346.61.”", rule_id="REGZ-CE-TRIGGER"))

    # high-risk affiliate page, routed to senior counsel
    sub = demo.submit("Sam", hours_ago(9), "“Best Personal Loans for Bad Credit (2026)” review page", "personal_loan", "landing_page",
        "Best Personal Loans for Bad Credit in 2026\n\n"
        "Need cash fast? ClearPath is our #1 pick for borrowers with bad credit. You're pre-approved for up to $35,000 with no credit check, "
        "and approval is guaranteed for anyone with a steady income.\n\n"
        "Why we love ClearPath:\n"
        "• Instant funding straight to your bank account\n"
        "• Rates as low as 7.99%\n\n"
        "[Get my money now]")
    demo.ai_review(sub,
        "Not approvable. False statements about approval and credit checks, and no APR disclosure. Recommend rejecting and re-briefing the partner.",
        AINote("for anyone with a steady income", "Implies income is the only approval criterion", "major",
               "Even without “guaranteed”, saying anyone with steady income qualifies misrepresents underwriting, which also looks at credit history and debt-to-income.",
               "Remove it. If eligibility comes up, say “Eligibility depends on credit history, income, and other factors.”", rule_id="UDAAP-GUARANTEED"))

    # overdue mortgage page; Claude catches what the rules don't
    sub = demo.submit("Luis", hours_ago(100), "Mortgage prequal landing page — fall refresh", "mortgage", "landing_page",
        "Your dream home is closer than you think\n\n"
        "See if you prequalify for a home loan in minutes, with no impact to your credit score.\n\n"
        "Our government-backed loan options make homeownership possible for first-time buyers.\n\n"
        "Estimated monthly payment: $1,842/mo on a 30-year term.\n\n"
        "[Get prequalified]")
    demo.ai_review(sub,
        "High risk. No NMLS ID, a payment example without the rate and amount, and “government-backed” suggests a program we don't offer.",
        AINote("government-backed loan options", "Implies a government program", "critical",
               "ClearPath's prequalification isn't an FHA/VA product. Suggesting government backing is a listed misrepresentation under Reg N.",
               "Remove it, or name the specific program accurately if Legal confirms we offer it."),
        AINote("Estimated monthly payment: $1,842/mo", "Payment example missing taxes & insurance", "major",
               "For mortgage ads, a payment figure needs the loan amount, rate/APR and term, and has to say taxes and insurance aren't included.",
               "“$1,842/mo is principal and interest on a $300,000, 30-year fixed loan at 6.25% (6.41% APR). Taxes and insurance not included.”", rule_id="REGZ-CE-TRIGGER"))

    # clean, fast lane
    sub = demo.submit("Maya", hours_ago(2), "Rewards card — 300×250 display banner", "credit_card", "display",
        "Earn 2% cash back on every purchase.\n"
        "0% intro APR on purchases for 15 months, then 21.24% – 29.99% variable APR.\n"
        "$0 annual fee. ClearPath Rewards Card issued by ClearPath Financial. Subject to credit approval.\n"
        "[Apply now]")
    demo.ai_review(sub, "Low risk. The intro APR is labeled, and the duration and go-to APR are right next to it.")

    # v2 resubmission: two changes fixed, one still open, one new Claude finding
    newsletter = (
        "Subject: The loan our readers keep asking about\n\n"
        "Advertiser disclosure: LoanLadder may receive compensation from ClearPath Financial when you apply.\n\n"
        "This month's spotlight: ClearPath Financial personal loans. {offer}\n\n"
        "Payments as low as $150/month. Rates as low as 7.99% APR.\n\n"
        "Unsubscribe | LoanLadder Media, 88 Pine Street, Floor 3, New York, NY 10005")
    sub = demo.submit("Erin", hours_ago(52), "LoanLadder newsletter — ClearPath spotlight", "personal_loan", "email",
        newsletter.format(offer="Borrow up to $50,000 with no credit check to see your rate, and get instant approval online."))
    demo.ai_review(sub,
        "Medium risk. Two false statements (credit check, instant approval) and a payment claim without the amount and term.",
        AINote("Payments as low as $150/month", "Payment claim without amount and term", "major",
               "The APR is there, but a payment amount also requires the repayment terms. $150/month only works on a small loan at the longest term.",
               "Drop the payment line, or use the representative example: “$10,000 over 36 months at 14.99% APR = 36 payments of $346.61.”", rule_id="REGZ-CE-TRIGGER"))
    demo.review(sub, require={"UDAAP-NO-CREDIT-CHECK", "UDAAP-INSTANT", "Payment claim without amount and term"})
    demo.decide(sub, hours_ago(47), "request_changes", "Disclosure is in the right place. Three fixes; the payment line is the important one.")
    demo.revise(sub, hours_ago(3),
        newsletter.format(offer="Borrow up to $50,000 and check your rate without affecting your credit score, then get a decision online."),
        "Took out the credit check and instant approval bits. Kept the payment line since it's our best-performing hook, happy to discuss.")
    demo.ai_review(sub,
        "Most fixes landed. The $150/month line is still there, and the new credit-score line needs the hard-inquiry qualifier.",
        AINote("check your rate without affecting your credit score", "Credit-score claim missing hard-inquiry qualifier", "major",
               "Reworded so the rule doesn't match, but it's the same claim and still needs to say applying triggers a hard inquiry.",
               "Add: “If you apply, a hard credit inquiry may affect your credit score.”", rule_id="FCRA-SOFT-PULL"))

    # back with the submitter (Maya)
    sub = demo.submit("Maya", hours_ago(30), "Home improvement loan — landing page", "personal_loan", "landing_page",
        "Make your home yours again\n\n"
        "From a new roof to a dream kitchen, a ClearPath Financial home improvement loan gets you started.\n\n"
        "Borrow $5,000 to $50,000 with rates as low as 8.49%.\n\n"
        "Get instant approval and see your money tomorrow.\n\n"
        "Checking your rate won't affect your credit score.\n\n"
        "[Check my rate]")
    demo.ai_review(sub,
        "Medium risk. The speed claims overstate funding time and the rate needs to be an APR.",
        AINote("see your money tomorrow", "Funding-time promise", "major",
               "Most people are funded 1–3 business days after approval. “Tomorrow” is a promise.",
               "Use “Funds as soon as the next business day after approval.”", rule_id="UDAAP-INSTANT"))
    demo.review(sub, require={"UDAAP-INSTANT", "REGZ-RATE-AS-APR", "FCRA-SOFT-PULL", "Funding-time promise"})
    demo.decide(sub, hours_ago(22), "request_changes", "Close! Speed claims, say APR, and use the soft-pull wording from the library.")

    # approved with a condition
    sub = demo.submit("Kofi", hours_ago(40), "Balance transfer promo — RateWise email", "credit_card", "email",
        "Subject: Pay down your balance faster\n\n"
        "Advertiser disclosure: RateWise Media may receive compensation from ClearPath Financial.\n\n"
        "Move high-interest balances to the ClearPath Rewards Card. 0% intro APR on balance transfers for 15 months, then "
        "21.24% – 29.99% variable APR. 3% balance transfer fee ($5 min). $0 annual fee. Limited time offer.\n\n"
        "Unsubscribe | RateWise Media, 410 Congress Avenue, Austin, TX 78701")
    demo.ai_review(sub, "Low risk. Only the open-ended urgency needs a real end date.")
    demo.review(sub, require={"UDAAP-URGENCY"})
    demo.decide(sub, hours_ago(26), "approve_with_conditions", "Fine once you add the actual end date. No need to resubmit.")


# (safe, risky) phrasings; "" means the risky draft leaves it out
TEMPLATES = [
    dict(product="personal_loan", channel="email", title="Debt consolidation nurture — {month}", parts=[
        ("Combine high-interest card balances into one fixed monthly payment.", "Combine your cards into one low payment of $199/mo."),
        ("Check your rate in minutes.", "Get instant approval in minutes. Act now!"),
        ("Rates from 7.99% APR to 35.99% APR.", "The lowest rates around, as low as 7.99%."),
        (SNIPPET["email-footer"], ""),
    ]),
    dict(product="personal_loan", channel="search", title="Search ad set — {month}", parts=[
        ("Personal Loans up to $50K | Check Your Rate in 2 Minutes", "Personal Loans - No Credit Check | Instant Funding"),
        (SNIPPET["soft-pull"], "Won't Affect Your Credit Score"),
    ]),
    dict(product="credit_card", channel="display", title="Rewards card display — {month} flight", parts=[
        ("Earn 2% cash back on every purchase.", "The best card for cash back. Limited time!"),
        ("0% intro APR for 15 months, then 21.24% – 29.99% variable APR.", "0% APR for 15 months!"),
    ]),
    dict(product="mortgage", channel="landing_page", title="Mortgage prequal page — {month} test", parts=[
        ("See what you could prequalify for in minutes.", "You're pre-approved, so act fast."),
        (SNIPPET["mortgage-footer"], ""),
    ]),
    dict(product="personal_loan", channel="sms", title="Application reminder SMS — {month}", parts=[
        ("ClearPath: You're 2 steps from seeing your rate. Finish here: cpth.co/r", "ClearPath: You've been approved! Claim your cash: cpth.co/r"),
        (SNIPPET["sms-footer"], ""),
    ]),
    dict(product="personal_loan", channel="landing_page", title="Personal loan review page — {month}", affiliate_only=True, parts=[
        ("ClearPath Financial offers personal loans from $2,000 to $50,000.", "Our #1 pick for bad credit. Approval is guaranteed."),
        (SNIPPET["pl-representative-example"], "Rates as low as 7.99%."),
    ]),
]

# how often reviewers agree with each rule (feeds the "rules worth tuning" panel); unlisted rules: 93%
AGREEMENT = {"UDAAP-URGENCY": 0.45, "UDAAP-SUPERLATIVE": 0.85, "REGZ-RATE-AS-APR": 0.88, "FCRA-SOFT-PULL": 0.8}
# chance of each risky phrase showing up in someone's first draft
SLOPPINESS = {"Maya": 0.22, "Luis": 0.18, "Sam": 0.6, "Erin": 0.35, "Kofi": 0.28}
SUBMITTERS = ["Maya", "Maya", "Luis", "Luis", "Sam", "Erin", "Kofi"]
PRECHECK_LAUNCHED_WEEKS_AGO = 5
# hours for: first decision, submitter fixing it, second decision. Before the pre-check the queue was backed up.
HOURS_BEFORE = [(30, 130), (20, 70), (8, 40)]
HOURS_AFTER = [(6, 44), (4, 28), (2, 14)]
NO_AI_FINDINGS = "Nothing beyond what the rules caught."


def history(demo: Demo, now: datetime, rng: random.Random) -> None:
    monday = (now - timedelta(days=now.weekday())).replace(hour=9, minute=0, second=0, microsecond=0)

    for weeks_ago in range(10, 0, -1):
        launched = weeks_ago <= PRECHECK_LAUNCHED_WEEKS_AGO
        for _ in range(rng.randint(11, 15) if launched else rng.randint(8, 11)):
            who = rng.choice(SUBMITTERS)
            affiliate = demo.users[who].role == "affiliate"
            template = rng.choice([t for t in TEMPLATES if affiliate or not t.get("affiliate_only")])

            def draft(risk_rate: float) -> str:
                parts = [SNIPPET["affiliate-disclosure"] if affiliate and rng.random() > risk_rate / 2 else ""]
                parts += [risky if rng.random() < risk_rate else safe for safe, risky in template["parts"]]
                return "\n\n".join(p for p in parts if p)

            start = monday - timedelta(weeks=weeks_ago) + timedelta(days=rng.randint(0, 4), hours=rng.randint(0, 8))
            hours = HOURS_AFTER if launched else HOURS_BEFORE
            _, first_decision, revised, second_decision = accumulate(
                [start, *(timedelta(hours=rng.uniform(lo, hi)) for lo, hi in hours)])
            if second_decision > now:
                continue

            content = draft(SLOPPINESS[who] * (0.55 if launched else 1))
            hits = findings_for(content, template["product"], template["channel"], "affiliate" if affiliate else "internal")
            required = {h["rule_id"] for h in hits if rng.random() < AGREEMENT.get(h["rule_id"], 0.93)}
            dismissed = {h["rule_id"] for h in hits} - required
            critical = any(h["severity"] == "critical" and h["rule_id"] in required for h in hits)

            sub = demo.submit(who, start, template["title"].format(month=start.strftime("%b")), template["product"],
                              template["channel"], content)
            demo.ai_review(sub, NO_AI_FINDINGS)
            demo.review(sub, require=required, dismiss=dismissed)
            if not required:
                demo.decide(sub, first_decision, "approve")
            elif not critical and len(required) <= 2 and rng.random() < 0.5:
                demo.decide(sub, first_decision, "approve_with_conditions")
            else:
                demo.decide(sub, first_decision, "request_changes")
                demo.revise(sub, revised, draft(0))
                demo.ai_review(sub, NO_AI_FINDINGS)
                demo.decide(sub, second_decision, "approve")


def seed(session: Session) -> None:
    session.add_all(User(**user) for user in USERS)
    session.commit()
    demo = Demo(session)
    now = utcnow()
    history(demo, now, random.Random(7))
    active_work(demo, now)
    session.commit()
