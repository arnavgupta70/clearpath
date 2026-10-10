from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    password_hash: str = Field(exclude=True)  # never sent to the frontend
    title: str
    role: str  # marketer, affiliate, reviewer or lead
    org: str
    color: str

    @property
    def is_reviewer(self) -> bool:
        return self.role in ("reviewer", "lead")


class Submission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    product: str
    channel: str
    source: str  # internal or affiliate
    partner: str | None = None
    submitter_id: int = Field(foreign_key="user.id")
    assignee_id: int | None = Field(default=None, foreign_key="user.id")
    status: str = "in_review"  # changes_requested, approved, approved_with_conditions, rejected
    risk_score: int
    risk_tier: str
    risk_factors: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    current_version: int = 1
    created_at: datetime
    updated_at: datetime
    due_at: datetime
    decided_at: datetime | None = None
    approval_code: str | None = None
    decision_note: str | None = None


class Version(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id")
    number: int
    content: str
    notes: str | None = None
    created_at: datetime
    ai_status: str  # pending, done, unavailable or error
    ai_summary: str | None = None


class Finding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id")
    version_id: int = Field(foreign_key="version.id")
    source: str  # rule, ai or reviewer
    rule_id: str | None = None
    title: str
    severity: str
    citation: str | None = None
    explanation: str
    suggestion: str | None = None
    quote: str | None = None
    start: int | None = None
    end: int | None = None
    # open -> accepted (a required change) or dismissed; accepted -> resolved once fixed in a later version
    status: str = "open"
    carried_from: int | None = None


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id")
    actor_id: int | None = Field(default=None, foreign_key="user.id")
    message: str
    created_at: datetime
