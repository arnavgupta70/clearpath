from collections import defaultdict

from sqlmodel import Session, select

from .models import Event, Finding, Submission, User, Version


def user_out(user: User | None) -> dict | None:
    return user.model_dump() if user else None


def summary_out(sub: Submission, users: dict[int, User], findings: list[Finding]) -> dict:
    # a queue row; `findings` are the current version's
    return {
        **sub.model_dump(exclude={"risk_factors", "decision_note", "submitter_id", "assignee_id"}),
        "ref": f"CV-{1000 + sub.id}",
        "submitter": user_out(users.get(sub.submitter_id)),
        "assignee": user_out(users.get(sub.assignee_id)),
        "open_issues": sum(f.status in ("open", "accepted") for f in findings),
    }


def submissions_out(session: Session, submitter_id: int | None = None) -> list[dict]:
    query = select(Submission).order_by(Submission.updated_at.desc())
    if submitter_id is not None:
        query = query.where(Submission.submitter_id == submitter_id)
    subs = session.exec(query).all()
    users = {u.id: u for u in session.exec(select(User))}

    # a few queries in total instead of a few per submission
    latest = {s.id: s.current_version for s in subs}
    current = {
        v.submission_id: v.id
        for v in session.exec(select(Version).where(Version.submission_id.in_(latest)))
        if v.number == latest[v.submission_id]
    }
    findings = defaultdict(list)
    for f in session.exec(select(Finding).where(Finding.version_id.in_(current.values()))):
        findings[f.version_id].append(f)
    return [summary_out(s, users, findings[current[s.id]]) for s in subs]


def detail_out(session: Session, sub: Submission) -> dict:
    users = {u.id: u for u in session.exec(select(User))}
    versions = session.exec(select(Version).where(Version.submission_id == sub.id).order_by(Version.number)).all()
    findings = session.exec(select(Finding).where(Finding.submission_id == sub.id).order_by(Finding.id)).all()
    events = session.exec(select(Event).where(Event.submission_id == sub.id).order_by(Event.created_at, Event.id)).all()
    by_version = defaultdict(list)
    for f in findings:
        by_version[f.version_id].append(f)
    current = versions[sub.current_version - 1]
    return {
        **summary_out(sub, users, by_version[current.id]),
        "risk_factors": sub.risk_factors,
        "decision_note": sub.decision_note,
        # for a conditional approval, the conditions are the required changes on the approved version
        "conditions": [f.suggestion or f.title for f in by_version[current.id] if f.status == "accepted"],
        "versions": [{**v.model_dump(), "findings": [f.model_dump() for f in by_version[v.id]]} for v in versions],
        "events": [{**e.model_dump(exclude={"actor_id"}), "actor": user_out(users.get(e.actor_id))} for e in events],
    }
