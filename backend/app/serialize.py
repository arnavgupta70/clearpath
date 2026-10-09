from collections import Counter, defaultdict

from sqlmodel import Session, select

from .models import Event, Finding, FindingStatus, Submission, User, Version

ACTIVE = (FindingStatus.OPEN, FindingStatus.ACCEPTED)


def user_out(user: User | None) -> dict | None:
    return user.model_dump() if user else None


def _users(session: Session) -> dict[int, User]:
    return {u.id: u for u in session.exec(select(User)).all()}


def summary_out(sub: Submission, users: dict[int, User], version: Version, findings: list[Finding]) -> dict:
    """Queue-row shape; `findings` are the current version's."""
    severities = Counter(f.severity for f in findings if f.status in ACTIVE)
    return {
        **sub.model_dump(exclude={"risk_factors", "conditions", "decision_note", "submitter_id", "assignee_id"}),
        "submitter": user_out(users.get(sub.submitter_id)),
        "assignee": user_out(users.get(sub.assignee_id)),
        "ai_status": version.ai_status,
        "counts": {
            "critical": severities["critical"],
            "major": severities["major"],
            "minor": severities["minor"],
            "untriaged": sum(f.status == FindingStatus.OPEN for f in findings),
            "required": sum(f.status == FindingStatus.ACCEPTED for f in findings),
        },
    }


def submissions_out(session: Session, submitter_id: int | None = None) -> list[dict]:
    query = select(Submission).order_by(Submission.updated_at.desc())
    if submitter_id is not None:
        query = query.where(Submission.submitter_id == submitter_id)
    subs = session.exec(query).all()
    ids = [s.id for s in subs]
    versions = {(v.submission_id, v.number): v for v in session.exec(select(Version).where(Version.submission_id.in_(ids)))}
    current = {s.id: versions[(s.id, s.current_version)] for s in subs}
    findings: dict[int, list[Finding]] = defaultdict(list)
    for f in session.exec(select(Finding).where(Finding.version_id.in_([v.id for v in current.values()]))):
        findings[f.version_id].append(f)
    users = _users(session)
    return [summary_out(s, users, current[s.id], findings[current[s.id].id]) for s in subs]


def detail_out(session: Session, sub: Submission) -> dict:
    users = _users(session)
    versions = session.exec(select(Version).where(Version.submission_id == sub.id).order_by(Version.number)).all()
    findings = session.exec(select(Finding).where(Finding.submission_id == sub.id).order_by(Finding.id)).all()
    events = session.exec(select(Event).where(Event.submission_id == sub.id).order_by(Event.created_at, Event.id)).all()
    by_version: dict[int, list[Finding]] = defaultdict(list)
    for f in findings:
        by_version[f.version_id].append(f)
    current = versions[sub.current_version - 1]
    return {
        **summary_out(sub, users, current, by_version[current.id]),
        "risk_factors": sub.risk_factors,
        "decision_note": sub.decision_note,
        "conditions": sub.conditions,
        "versions": [{**v.model_dump(), "findings": [f.model_dump() for f in by_version[v.id]]} for v in versions],
        "events": [{**e.model_dump(exclude={"actor_id"}), "actor": user_out(users.get(e.actor_id))} for e in events],
    }
