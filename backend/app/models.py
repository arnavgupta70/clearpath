from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(StrEnum):
    MARKETER = "marketer"
    AFFILIATE = "affiliate"
    REVIEWER = "reviewer"
    LEAD = "lead"


class Status(StrEnum):
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED = "rejected"


class FindingStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"  # i.e. a required change
    DISMISSED = "dismissed"
    RESOLVED = "resolved"  # accepted earlier, fixed in a later version


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    title: str
    role: str
    org: str
    color: str

    @property
    def is_reviewer(self) -> bool:
        return self.role in (Role.REVIEWER, Role.LEAD)


class Rule(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    category: str
    severity: str
    kind: str
    citation: str
    explanation: str
    suggestion: str
    patterns: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    requires: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    products: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    channels: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    sources: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    snippet_id: str | None = None


class Submission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ref: str = Field(index=True)
    title: str
    product: str
    channel: str
    source: str  # internal | affiliate
    partner: str | None = None
    submitter_id: int = Field(foreign_key="user.id")
    assignee_id: int | None = Field(default=None, foreign_key="user.id")
    status: str = Status.IN_REVIEW
    risk_score: int
    risk_tier: str
    risk_factors: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    current_version: int = 1
    target_launch: str | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime  # start of the current review round
    due_at: datetime
    decided_at: datetime | None = None
    approval_code: str | None = None
    decision_note: str | None = None
    conditions: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class Version(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", index=True)
    number: int
    content: str
    notes: str | None = None
    created_at: datetime
    ai_status: str  # pending | done | unavailable | error
    ai_summary: str | None = None


class Finding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", index=True)
    version_id: int = Field(foreign_key="version.id", index=True)
    source: str  # rule | ai | reviewer
    rule_id: str | None = None
    title: str
    category: str
    severity: str
    citation: str | None = None
    explanation: str
    suggestion: str | None = None
    quote: str | None = None
    start: int | None = None
    end: int | None = None
    status: str = FindingStatus.OPEN
    carried_from: int | None = None
    created_by: int | None = None
    created_at: datetime
    triaged_at: datetime | None = None


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", index=True)
    actor_id: int | None = Field(default=None, foreign_key="user.id")
    kind: str
    message: str
    created_at: datetime
