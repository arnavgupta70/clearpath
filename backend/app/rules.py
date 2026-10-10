"""Pattern-based compliance rules.

Three kinds:
  prohibited  the match itself is the problem ("guaranteed approval")
  trigger     the match is fine but requires a disclosure somewhere in the asset
              (a monthly payment amount means the APR has to be there - Reg Z "trigger terms")
  required    the asset has to contain the pattern for this product/channel/source
              (NMLS ID on mortgage ads, "Reply STOP" on SMS)

"""

import re
from dataclasses import dataclass, field

PRODUCTS = {
    "personal_loan": "Personal loan",
    "credit_card": "Credit card",
    "mortgage": "Mortgage prequalification",
}

CHANNELS = {
    "email": "Email",
    "social": "Social post",
    "display": "Display ad",
    "landing_page": "Landing page",
    "search": "Paid search",
    "sms": "SMS",
    "direct_mail": "Direct mail",
}

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}
LENDING = ["personal_loan", "mortgage"]
ALL = ["*"]


@dataclass
class RuleDef:
    id: str
    name: str
    category: str
    severity: str
    kind: str  # prohibited | trigger | required
    citation: str
    explanation: str
    suggestion: str
    patterns: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=lambda: ALL)
    channels: list[str] = field(default_factory=lambda: ALL)
    sources: list[str] = field(default_factory=lambda: ALL)
    snippet_id: str | None = None  # approved disclosure that resolves this rule


RULE_LIBRARY: list[RuleDef] = [
    RuleDef(
        id="REGZ-CE-TRIGGER",
        name="Closed-end trigger term without APR",
        category="Truth in Lending (Reg Z)",
        severity="critical",
        kind="trigger",
        citation="12 CFR 1026.24(d)",
        explanation=(
            "A payment amount, number of payments, repayment period, or finance-charge amount is a "
            "Reg Z trigger term. Stating one requires the APR, the repayment terms, and any down payment "
            "to be disclosed clearly and conspicuously in the same ad."
        ),
        suggestion="Add the APR range and repayment terms near the claim, or use the approved representative-example disclosure.",
        patterns=[
            r"\$\s?\d[\d,]*(?:\.\d{2})?\s?(?:/\s?mo(?:nth)?\b|per month|a month|monthly)",
            r"(?:low )?monthly payments? (?:of|as low as|from|starting at) \$\s?\d[\d,]*",
            r"\b\d{1,3}[- ](?:month|year)s? (?:term|terms|to repay)\b",
            r"\b(?:over|in) \d{1,3} (?:easy |simple )?(?:monthly )?(?:payments|installments)\b",
            r"\bpay (?:it )?(?:off|back) in \d{1,3} (?:months|years)\b",
        ],
        requires=[r"\bAPR\b", r"annual percentage rate"],
        products=LENDING,
        snippet_id="pl-representative-example",
    ),
    RuleDef(
        id="REGZ-RATE-AS-APR",
        name="Rate stated without “APR”",
        category="Truth in Lending (Reg Z)",
        severity="critical",
        kind="trigger",
        citation="12 CFR 1026.24(c); 1026.16(e)",
        explanation=(
            "If an ad states a rate of finance charge it must be stated as an “annual percentage rate” "
            "(APR). A bare interest rate cannot be more conspicuous than the APR."
        ),
        suggestion="Restate the rate as an APR, e.g. “Rates from 7.99% APR”, and include the APR range.",
        patterns=[
            r"\b\d{1,2}(?:\.\d{1,2})?\s?%\s?(?:interest|rate|fixed rate|variable rate)\b",
            r"\b(?:rates?|interest)\s(?:as low as|from|starting at|of)\s\d{1,2}(?:\.\d{1,2})?\s?%(?!\s?APR)",
        ],
        requires=[r"\bAPR\b", r"annual percentage rate"],
        products=ALL,
    ),
    RuleDef(
        id="REGZ-INTRO-RATE",
        name="Promotional rate missing duration or go-to rate",
        category="Truth in Lending (Reg Z)",
        severity="critical",
        kind="trigger",
        citation="12 CFR 1026.16(g)",
        explanation=(
            "A promotional rate must be labeled “introductory” or “intro” in immediate proximity, and "
            "the ad must state when it ends and the APR that applies afterward."
        ),
        suggestion="Use “0% intro APR for 15 months, then 21.24%–29.99% variable APR.”",
        patterns=[
            r"\b0\s?%\s?(?:intro(?:ductory)?\s)?(?:APR|interest|rate)\b",
            r"\bpromo(?:tional)? (?:APR|rate)\b",
            r"\bintro(?:ductory)? (?:APR|rate)\b",
        ],
        requires=[
            r"(?:after that|thereafter|then)[^.]{0,40}\d{1,2}(?:\.\d{1,2})?\s?%",
            r"\d{1,2}\.\d{2}\s?%\s?(?:-|–|to)\s?\d{1,2}\.\d{2}\s?%\s?(?:variable )?APR",
        ],
        products=["credit_card"],
        snippet_id="cc-terms",
    ),
    RuleDef(
        id="UDAAP-GUARANTEED",
        name="Guaranteed approval claim",
        category="UDAAP",
        severity="critical",
        kind="prohibited",
        citation="12 USC 5531, 5536 (Dodd-Frank UDAAP)",
        explanation=(
            "ClearPath underwrites every application, so approval is never guaranteed. Claiming otherwise "
            "is a deceptive representation and one of the most common CFPB enforcement findings."
        ),
        suggestion="Replace with “Check your rate in minutes” or “See if you prequalify.”",
        patterns=[
            r"\bguarantee(?:d|s)? (?:approval|approved|acceptance|loan|funding|a loan)\b",
            r"\bapproval (?:is )?guaranteed\b",
            r"\b(?:everyone|anyone|all applicants)(?: is| are| gets)? (?:approved|accepted)\b",
            r"\b100\s?% (?:approval|approved|acceptance)\b",
        ],
    ),
    RuleDef(
        id="UDAAP-NO-CREDIT-CHECK",
        name="“No credit check” claim",
        category="UDAAP",
        severity="critical",
        kind="prohibited",
        citation="12 USC 5531, 5536; FCRA 15 USC 1681b",
        explanation=(
            "ClearPath performs a credit check on every application (a soft pull to prequalify, a hard pull "
            "to apply). “No credit check” is literally false."
        ),
        suggestion="Use “Checking your rate won’t affect your credit score” with the hard-inquiry qualifier.",
        patterns=[r"\bno credit checks?\b", r"\bwithout (?:a )?credit checks?\b"],
    ),
    RuleDef(
        id="UDAAP-INSTANT",
        name="Unqualified speed claim",
        category="UDAAP",
        severity="major",
        kind="prohibited",
        citation="12 USC 5531, 5536",
        explanation=(
            "Funding typically takes 1–3 business days after approval and verification. “Instant” "
            "approval or funding overstates what most applicants experience."
        ),
        suggestion="Use “Funds as soon as the next business day after approval.”",
        patterns=[
            r"\binstant(?:ly)? (?:approval|approved|cash|funding|funds|money|loan)\b",
            r"\b(?:cash|money|funds) in minutes\b",
            r"\bsame[- ]day (?:cash|funding|money)\b",
        ],
    ),
    RuleDef(
        id="UDAAP-SUPERLATIVE",
        name="Unsubstantiated superlative",
        category="UDAAP",
        severity="major",
        kind="prohibited",
        citation="12 USC 5531, 5536; FTC Act §5 substantiation doctrine",
        explanation=(
            "Comparative or superlative claims (“lowest rates”, “#1”) must be substantiated at the time "
            "they are made, with the basis disclosed. We have no current substantiation on file."
        ),
        suggestion="Remove the superlative or cite a substantiated, dated source approved by Legal.",
        patterns=[
            r"\b(?<!qualify for the )(?<!qualify for )(?:the )?lowest (?:rates?|APRs?|prices?|payments?|fees?)\b",
            r"\bbest (?:rates?|APRs?|deal|card|loan)s?\b",
            r"(?:^|\s)#1\b",
            r"\bnumber one\b",
            r"\bbeats? any (?:rate|offer)\b",
        ],
    ),
    RuleDef(
        id="UDAAP-URGENCY",
        name="Pressure or false urgency",
        category="UDAAP",
        severity="minor",
        kind="prohibited",
        citation="12 USC 5531 (abusive acts); ClearPath Marketing Standard 3.1",
        explanation=(
            "Urgency language is only allowed when there is a real, stated deadline. Open-ended pressure "
            "can be viewed as abusive, particularly toward financially stressed consumers."
        ),
        suggestion="State the actual offer end date (“Offer ends 11/30/2026”) or remove the urgency.",
        patterns=[
            r"\bact (?:now|fast|today)\b",
            r"\blimited[- ]time\b",
            r"\btoday only\b",
            r"\bhurry\b",
            r"\bdon[’']t miss out\b",
            r"\bbefore it[’']s (?:gone|too late)\b",
            r"\bexpires soon\b",
        ],
    ),
    RuleDef(
        id="FCRA-PREAPPROVED",
        name="“Pre-approved” without a firm offer",
        category="FCRA / Prequalification",
        severity="critical",
        kind="prohibited",
        citation="FCRA 15 USC 1681a(l), 1681m(d)",
        explanation=(
            "“Pre-approved” implies a firm offer of credit, which requires a prescreened list and FCRA "
            "opt-out notices. ClearPath's online flow is prequalification only."
        ),
        suggestion="Use “See if you prequalify” or “Check your rate”.",
        patterns=[
            r"\bpre-?approved\b",
            r"\byou(?:[’']ve| have)? been approved\b",
            r"\byou(?:[’']re| are) (?:already )?approved\b",
        ],
    ),
    RuleDef(
        id="FCRA-SOFT-PULL",
        name="Credit-score claim missing hard-inquiry qualifier",
        category="FCRA / Prequalification",
        severity="major",
        kind="trigger",
        citation="12 USC 5531; ClearPath Marketing Standard 5.4",
        explanation=(
            "Checking a rate uses a soft inquiry, but submitting an application results in a hard inquiry. "
            "The “won't affect your credit” claim must say which step it applies to."
        ),
        suggestion="Add: “Checking your rate won’t affect your credit score. If you apply, a hard inquiry may affect it.”",
        patterns=[
            r"\b(?:won[’']t|will not|doesn[’']t|does not|never)\s(?:affect|impact|hurt|harm|ding)\syour credit(?: score)?\b",
            r"\bno (?:impact|effect) (?:on|to) your credit(?: score)?\b",
        ],
        requires=[r"hard (?:credit )?(?:inquiry|pull)"],
        snippet_id="soft-pull",
    ),
    RuleDef(
        id="MORT-NMLS",
        name="Missing NMLS ID",
        category="Mortgage advertising",
        severity="critical",
        kind="required",
        citation="SAFE Act 12 USC 5101 et seq.; state advertising rules",
        explanation="Mortgage advertising must display ClearPath's NMLS unique identifier.",
        suggestion="Add the approved mortgage footer: “ClearPath Financial, NMLS #1849302.”",
        requires=[r"NMLS\s?(?:ID|#)?\s?:?\s?#?\s?\d{4,}"],
        products=["mortgage"],
        snippet_id="mortgage-footer",
    ),
    RuleDef(
        id="CANSPAM-UNSUB",
        name="Email missing unsubscribe mechanism",
        category="CAN-SPAM",
        severity="major",
        kind="required",
        citation="15 USC 7704(a)(3)",
        explanation="Commercial email must include a clear, working way to opt out of future messages.",
        suggestion="Insert the approved email footer with the unsubscribe link.",
        requires=[r"unsubscribe", r"opt[- ]out", r"email preferences"],
        channels=["email"],
        snippet_id="email-footer",
    ),
    RuleDef(
        id="TCPA-STOP",
        name="SMS missing opt-out instructions",
        category="TCPA",
        severity="critical",
        kind="required",
        citation="47 CFR 64.1200; CTIA Messaging Principles",
        explanation="Marketing texts must tell recipients how to opt out (e.g. “Reply STOP to opt out”).",
        suggestion="Append “Msg&data rates may apply. Reply STOP to opt out.”",
        requires=[r"reply\s+stop", r"text\s+stop", r"stop to (?:opt[- ]out|unsubscribe|end|cancel|quit)"],
        channels=["sms"],
        snippet_id="sms-footer",
    ),
    RuleDef(
        id="FTC-AFFILIATE-DISCLOSURE",
        name="Missing material-connection disclosure",
        category="FTC endorsements",
        severity="major",
        kind="required",
        citation="16 CFR 255.5 (FTC Endorsement Guides)",
        explanation=(
            "Affiliates are paid by ClearPath, so their content must clearly disclose the relationship. "
            "ClearPath is liable for partner marketing under the CFPB's service-provider guidance."
        ),
        suggestion="Add the approved affiliate disclosure at the top of the content.",
        requires=[
            r"#ad\b",
            r"\bsponsored\b",
            r"advertis(?:ing|er) disclosure",
            r"(?:earn|receive|may be paid) (?:a )?(?:commission|compensation)",
            r"paid (?:partner|advertis)",
        ],
        sources=["affiliate"],
        snippet_id="affiliate-disclosure",
    ),
]



@dataclass
class Hit:
    rule_id: str
    start: int | None
    end: int | None
    quote: str | None


def _applies(values: list[str], value: str) -> bool:
    return "*" in values or value in values


def applicable(rule, product: str, channel: str, source: str) -> bool:
    return (
        _applies(rule.products, product)
        and _applies(rule.channels, channel)
        and _applies(rule.sources, source)
    )


def _search_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _spans(patterns: list[str], text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            s, e = m.start(), m.end()
            # trim leading whitespace captured by (?:^|\s) style anchors
            while s < e and text[s].isspace():
                s += 1
            spans.append((s, e))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return merged


def run_rules(text: str, product: str, channel: str, source: str) -> list[Hit]:
    hits: list[Hit] = []
    for rule in RULE_LIBRARY:
        if not applicable(rule, product, channel, source):
            continue
        if rule.kind == "required":
            if not _search_any(rule.requires, text):
                hits.append(Hit(rule.id, None, None, None))
            continue
        if rule.kind == "trigger" and _search_any(rule.requires, text):
            continue
        for s, e in _spans(rule.patterns, text):
            hits.append(Hit(rule.id, s, e, text[s:e]))
    return hits


SNIPPETS = [
    {
        "id": "pl-representative-example",
        "title": "Personal loan — APR & representative example",
        "products": ["personal_loan"],
        "body": (
            "Loans offered by ClearPath Financial. APRs range from 7.99% to 35.99%. Loan terms 24 to 60 months. "
            "Representative example: a $10,000 loan with a 36-month term at 14.99% APR has 36 monthly payments "
            "of $346.61. Subject to credit approval. Not all applicants will qualify for the lowest rate."
        ),
    },
    {
        "id": "cc-terms",
        "title": "Credit card — intro APR & key terms",
        "products": ["credit_card"],
        "body": (
            "ClearPath Rewards Card issued by ClearPath Financial. 0% intro APR on purchases for 15 months, then "
            "21.24% – 29.99% variable APR based on your creditworthiness. $0 annual fee. Balance transfer fee: 3% "
            "of each transfer ($5 min). Subject to credit approval."
        ),
    },
    {
        "id": "mortgage-footer",
        "title": "Mortgage — NMLS & Equal Housing footer",
        "products": ["mortgage"],
        "body": (
            "ClearPath Financial, NMLS #1849302. Equal Housing Lender. Prequalification is not a commitment to "
            "lend; rates shown are estimates and are not locked. Subject to credit and property approval."
        ),
    },
    {
        "id": "soft-pull",
        "title": "Soft-pull credit inquiry language",
        "products": ["*"],
        "body": (
            "Checking your rate won’t affect your credit score. If you continue and submit an application, "
            "a hard credit inquiry will be made, which may affect your credit score."
        ),
    },
    {
        "id": "email-footer",
        "title": "Email footer — CAN-SPAM",
        "products": ["*"],
        "body": (
            "You're receiving this email because you opted in at clearpath.com. Unsubscribe or manage email "
            "preferences. ClearPath Financial, 1200 Market Street, Suite 400, Charlotte, NC 28202."
        ),
    },
    {
        "id": "sms-footer",
        "title": "SMS opt-out",
        "products": ["*"],
        "body": "ClearPath Financial: Msg&data rates may apply. Reply STOP to opt out, HELP for help.",
    },
    {
        "id": "affiliate-disclosure",
        "title": "Affiliate advertising disclosure",
        "products": ["*"],
        "placement": "top",  # must come before any offer content
        "body": (
            "Advertiser disclosure: We may receive compensation from ClearPath Financial when you click links "
            "or apply for products on this page. This does not affect our editorial opinions."
        ),
    },
]
