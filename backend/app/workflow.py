"""Submission lifecycle: submit -> triage -> decide -> resubmit.

None of these commit; the route handler does. The optional `at` lets seed.py replay history
through the same code.
"""

import logging
from collections import Counter
from datetime import datetime

from sqlmodel import Session, select

from . import ai, risk
from .db import engine
from .models import Event, Finding, FindingStatus, Role, Rule, Status, Submission, User, Version, utcnow
from .rules import SEVERITY_ORDER, run_rules

log = logging.getLogger(__name__)

APPROVED = (Status.APPROVED, Status.APPROVED_WITH_CONDITIONS)
DECIDED = (*APPROVED, Status.REJECTED)


class WorkflowError(Exception):
    pass


def plural(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"


def source_for(user: User) -> tuple[str, str | None]:
    if user.role == Role.AFFILIATE:
        return "affiliate", user.org
    return "internal", None


def load_rules(session: Session) -> list[Rule]:
    return list(session.exec(select(Rule)).all())


def findings_for(content: str, product: str, channel: str, source: str, rules: list[Rule]) -> list[dict]:
    rules_by_id = {r.id: r for r in rules}
    findings = []
    for hit in run_rules(content, product, channel, source, rules):
        rule = rules_by_id[hit.rule_id]
        findings.append({
            "source": "rule", "rule_id": rule.id, "title": rule.name, "category": rule.category,
            "severity": rule.severity, "citation": rule.citation, "explanation": rule.explanation,
            "suggestion": rule.suggestion, "quote": hit.quote, "start": hit.start, "end": hit.end,
        })
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["start"] or 0))
    return findings


def partner_first_pass(session: Session, partner: str | None) -> float | None:
    if not partner:
        return None
    decided = session.exec(select(Submission).where(Submission.partner == partner, Submission.status.in_(DECIDED))).all()
    if len(decided) < 3:
        return None
    return sum(s.status in APPROVED and s.current_version == 1 for s in decided) / len(decided)


def precheck(session: Session, user: User, content: str, product: str, channel: str) -> dict:
    source, partner = source_for(user)
    findings = findings_for(content, product, channel, source, load_rules(session))
    assessment = risk.assess(product, channel, source, [f["severity"] for f in findings], partner_first_pass(session, partner))
    return {
        "findings": findings,
        "risk": {"score": assessment.score, "tier": assessment.tier, "label": assessment.label, "factors": assessment.factors},
        "estimated_decision_by": assessment.due(utcnow()),
    }


def pick_assignee(session: Session, tier: str, product: str, source: str) -> int | None:
    # high-risk mortgage and affiliate work goes to senior counsel, the rest to whichever analyst has the shortest queue
    role = Role.LEAD if tier == "high" and (product == "mortgage" or source == "affiliate") else Role.REVIEWER
    candidates = session.exec(select(User).where(User.role == role)).all()
    if not candidates:
        return None
    load = Counter(session.exec(select(Submission.assignee_id).where(Submission.status == Status.IN_REVIEW)).all())
    return min(candidates, key=lambda u: (load[u.id], u.id)).id


def log_event(session: Session, sub_id: int, actor_id: int | None, kind: str, message: str, at: datetime) -> None:
    session.add(Event(submission_id=sub_id, actor_id=actor_id, kind=kind, message=message, created_at=at))


def add_findings(session: Session, version: Version, findings: list[dict], at: datetime) -> None:
    for f in findings:
        session.add(Finding(submission_id=version.submission_id, version_id=version.id, created_at=at, **f))


def new_version(session: Session, sub: Submission, number: int, content: str, notes: str | None, at: datetime) -> Version:
    version = Version(submission_id=sub.id, number=number, content=content, notes=notes, created_at=at,
                      ai_status="pending" if ai.enabled() else "unavailable")
    session.add(version)
    session.flush()
    return version


def create_submission(session: Session, submitter: User, *, title: str, product: str, channel: str, content: str,
                      notes: str | None = None, target_launch: str | None = None,
                      at: datetime | None = None) -> Submission:
    at = at or utcnow()
    source, partner = source_for(submitter)
    content = content.strip()
    findings = findings_for(content, product, channel, source, load_rules(session))
    assessment = risk.assess(product, channel, source, [f["severity"] for f in findings], partner_first_pass(session, partner))

    sub = Submission(
        ref="", title=title.strip(), product=product, channel=channel, source=source, partner=partner,
        submitter_id=submitter.id, assignee_id=pick_assignee(session, assessment.tier, product, source),
        risk_score=assessment.score, risk_tier=assessment.tier, risk_factors=assessment.factors,
        target_launch=target_launch,
        created_at=at, updated_at=at, submitted_at=at, due_at=assessment.due(at),
    )
    session.add(sub)
    session.flush()
    sub.ref = f"CV-{1000 + sub.id}"
    version = new_version(session, sub, 1, content, notes, at)
    add_findings(session, version, findings, at)

    log_event(session, sub.id, submitter.id, "submitted", f"Submitted v1 · {plural(len(findings), 'pre-check issue')}", at)
    if sub.assignee_id:
        assignee = session.get(User, sub.assignee_id)
        log_event(session, sub.id, None, "assigned", f"Assigned to {assignee.name} ({assessment.tier} risk)", at)
    return sub


def record_ai_review(session: Session, version: Version, review: ai.Review, at: datetime) -> None:
    add_findings(session, version, review.findings, at)
    version.ai_status = "done"
    version.ai_summary = review.summary
    session.add(version)
    found = plural(len(review.findings), "more issue") if review.findings else "nothing new"
    log_event(session, version.submission_id, None, "ai_review", f"Claude review on v{version.number}: {found}", at)


def run_ai_review(version_id: int) -> None:
    # runs as a background task, so it gets its own session
    with Session(engine) as session:
        version = session.get(Version, version_id)
        sub = session.get(Submission, version.submission_id)
        flagged = [(f.rule_id or f.title, f.quote) for f in version_findings(session, version)]
        try:
            review = ai.analyze(version.content, sub.product, sub.channel, sub.source, sub.partner, flagged)
        except ai.AIUnavailable as e:
            version.ai_status, version.ai_summary = "error", str(e)
        except Exception:
            # nobody is waiting on this request, so record the failure instead of leaving it "pending"
            log.exception("Claude review failed for version %s", version_id)
            version.ai_status, version.ai_summary = "error", "Claude review failed."
        else:
            record_ai_review(session, version, review, utcnow())
        session.add(version)
        session.commit()


def current_version(session: Session, sub: Submission) -> Version:
    return session.exec(select(Version).where(Version.submission_id == sub.id, Version.number == sub.current_version)).one()


def version_findings(session: Session, version: Version) -> list[Finding]:
    return list(session.exec(select(Finding).where(Finding.version_id == version.id).order_by(Finding.id)).all())


def triage(session: Session, finding: Finding, status: FindingStatus, at: datetime | None = None) -> None:
    sub = session.get(Submission, finding.submission_id)
    if sub.status != Status.IN_REVIEW:
        raise WorkflowError("This submission isn't in review")
    if finding.version_id != current_version(session, sub).id:
        raise WorkflowError("Only findings on the latest version can be changed")
    finding.status = status
    finding.triaged_at = None if status == FindingStatus.OPEN else (at or utcnow())
    session.add(finding)


def decide(session: Session, sub: Submission, decision: str, reviewer: User, note: str | None = None,
           at: datetime | None = None) -> None:
    at = at or utcnow()
    if sub.status != Status.IN_REVIEW:
        raise WorkflowError("This submission isn't in review")
    version = current_version(session, sub)
    findings = version_findings(session, version)
    required = [f for f in findings if f.status == FindingStatus.ACCEPTED]
    code = f"CP-MKT-{sub.created_at.year}-{sub.id:04d}"

    if decision == "approve":
        if required:
            raise WorkflowError("There are still required changes. Request changes or approve with conditions.")
        for f in findings:
            if f.status == FindingStatus.OPEN:
                f.status, f.triaged_at = FindingStatus.DISMISSED, at
                session.add(f)
        sub.status, sub.approval_code = Status.APPROVED, code
        message = f"Approved v{version.number} ({code})"
    elif decision == "approve_with_conditions":
        if not required:
            raise WorkflowError("Mark at least one required change first.")
        if any(f.severity == "critical" for f in required):
            raise WorkflowError("Critical issues need another round. Request changes instead.")
        sub.status, sub.approval_code = Status.APPROVED_WITH_CONDITIONS, code
        sub.conditions = [f.suggestion or f.title for f in required]
        message = f"Approved v{version.number} with {plural(len(required), 'condition')} ({code})"
    elif decision == "request_changes":
        if not required and not note:
            raise WorkflowError("Mark at least one required change or leave a note.")
        sub.status = Status.CHANGES_REQUESTED
        message = f"Requested {plural(len(required), 'change')} on v{version.number}"
    elif decision == "reject":
        if not note:
            raise WorkflowError("Add a note saying why it's rejected.")
        sub.status = Status.REJECTED
        message = f"Rejected v{version.number}"
    else:
        raise WorkflowError(f"Unknown decision {decision!r}")

    sub.decision_note = note or None
    sub.decided_at = at if sub.status in DECIDED else None
    sub.updated_at = at
    session.add(sub)
    log_event(session, sub.id, reviewer.id, decision, message + (f': "{note}"' if note else ""), at)


def resubmit(session: Session, sub: Submission, content: str, notes: str | None = None, at: datetime | None = None) -> Version:
    at = at or utcnow()
    if sub.status != Status.CHANGES_REQUESTED:
        raise WorkflowError("Only submissions with requested changes can be revised")
    previous = current_version(session, sub)
    version = new_version(session, sub, previous.number + 1, content.strip(), notes, at)
    findings, resolved, still_open = carry_forward(session, sub, version_findings(session, previous), version, at)

    assessment = risk.assess(sub.product, sub.channel, sub.source, [f["severity"] for f in findings],
                             partner_first_pass(session, sub.partner), version.number)
    sub.risk_score, sub.risk_tier, sub.risk_factors = assessment.score, assessment.tier, assessment.factors
    sub.current_version = version.number
    sub.status = Status.IN_REVIEW
    sub.submitted_at = sub.updated_at = at
    sub.due_at = risk.add_business_days(at, 1)  # only the changes need reviewing
    session.add(sub)

    message = f"Submitted v{version.number} · {resolved} of {plural(resolved + still_open, 'required change')} fixed"
    log_event(session, sub.id, sub.submitter_id, "resubmitted", message, at)
    return version


def carry_forward(session: Session, sub: Submission, previous: list[Finding], version: Version, at: datetime):
    """Re-check a new version against the reviewer's decisions on the last one.

    A required change that no longer applies is resolved. One that still applies comes across
    already accepted, so the reviewer doesn't triage it twice. Returns (findings, resolved, still_open).
    """
    content = version.content
    findings = findings_for(content, sub.product, sub.channel, sub.source, load_rules(session))
    required = [f for f in previous if f.status == FindingStatus.ACCEPTED]
    required_rules = {f.rule_id: f for f in required if f.source == "rule"}

    for f in findings:
        earlier = required_rules.get(f["rule_id"])
        if earlier:
            f.update(status=FindingStatus.ACCEPTED, carried_from=earlier.id, triaged_at=at)

    firing = {f["rule_id"] for f in findings}
    still_required = {f.id for f in required if f.source == "rule" and f.rule_id in firing}

    resolved = 0
    for earlier in required:
        if earlier.id in still_required:
            continue
        # Claude and reviewer findings have no rule to re-run, so they stand while the quoted text is still there
        span = ai.locate(earlier.quote, content) if earlier.source != "rule" and earlier.quote else None
        if span:
            findings.append({
                "source": earlier.source, "rule_id": earlier.rule_id, "title": earlier.title,
                "category": earlier.category, "severity": earlier.severity, "explanation": earlier.explanation,
                "suggestion": earlier.suggestion, "quote": content[span[0]:span[1]], "start": span[0], "end": span[1],
                "status": FindingStatus.ACCEPTED, "carried_from": earlier.id, "triaged_at": at,
            })
            still_required.add(earlier.id)
        else:
            earlier.status = FindingStatus.RESOLVED
            session.add(earlier)
            resolved += 1

    add_findings(session, version, findings, at)
    return findings, resolved, len(still_required)
