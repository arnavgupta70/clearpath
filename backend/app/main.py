import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from . import ai, metrics, workflow
from .db import engine, get_session, init_db, reset_db
from .models import Finding, Submission, User
from .rules import CHANNELS, PRODUCTS, RULE_LIBRARY, SNIPPETS
from .seed import seed
from .serialize import detail_out, submissions_out
from .workflow import WorkflowError

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(engine) as session:
        if not session.exec(select(User)).first():
            seed(session)
    yield


app = FastAPI(title="ClearView API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(WorkflowError)
def workflow_error(_: Request, error: WorkflowError):
    return JSONResponse(status_code=409, content={"detail": str(error)})


SessionDep = Annotated[Session, Depends(get_session)]


# No real auth: the frontend sends whichever demo user is picked.
def current_user(session: SessionDep, x_user_id: Annotated[int, Header()]) -> User:
    user = session.get(User, x_user_id)
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


def current_reviewer(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_reviewer:
        raise HTTPException(403, "Compliance only")
    return user


UserDep = Annotated[User, Depends(current_user)]
ReviewerDep = Annotated[User, Depends(current_reviewer)]


def get_submission(session: Session, submission_id: int) -> Submission:
    sub = session.get(Submission, submission_id)
    if not sub:
        raise HTTPException(404, "Submission not found")
    return sub


class Draft(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    product: Literal[tuple(PRODUCTS)]
    channel: Literal[tuple(CHANNELS)]


class NewSubmission(Draft):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    notes: str | None = None


class Revision(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    notes: str | None = None


class DecisionIn(BaseModel):
    decision: Literal["approve", "approve_with_conditions", "request_changes", "reject"]
    note: str | None = None


class TriageIn(BaseModel):
    status: Literal["open", "accepted", "dismissed"]




@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/meta")
def meta(session: SessionDep):
    return {
        "products": PRODUCTS,
        "channels": CHANNELS,
        "users": session.exec(select(User).order_by(User.id)).all(),
        "snippets": SNIPPETS,
        "snippet_for_rule": {r.id: r.snippet_id for r in RULE_LIBRARY if r.snippet_id},
    }


@app.post("/api/precheck")
def precheck(draft: Draft, user: UserDep, session: SessionDep):
    return workflow.precheck(session, user, draft.content, draft.product, draft.channel)


@app.get("/api/submissions")
def list_submissions(user: UserDep, session: SessionDep, mine: bool = False):
    if not mine and not user.is_reviewer:
        raise HTTPException(403, "Compliance only")
    return submissions_out(session, submitter_id=user.id if mine else None)


@app.post("/api/submissions")
def create_submission(body: NewSubmission, tasks: BackgroundTasks, user: UserDep, session: SessionDep):
    sub = workflow.create_submission(session, user, **body.model_dump())
    session.commit()
    if ai.enabled():
        tasks.add_task(workflow.run_ai_review, workflow.current_version(session, sub).id)
    return detail_out(session, sub)


@app.get("/api/submissions/{submission_id}")
def get_submission_detail(submission_id: int, user: UserDep, session: SessionDep):
    sub = get_submission(session, submission_id)
    if not user.is_reviewer and sub.submitter_id != user.id:
        raise HTTPException(403, "Not your submission")
    return detail_out(session, sub)


@app.post("/api/submissions/{submission_id}/versions")
def resubmit(submission_id: int, body: Revision, tasks: BackgroundTasks, user: UserDep, session: SessionDep):
    sub = get_submission(session, submission_id)
    if sub.submitter_id != user.id:
        raise HTTPException(403, "Not your submission")
    version = workflow.resubmit(session, sub, body.content, body.notes)
    session.commit()
    if ai.enabled():
        tasks.add_task(workflow.run_ai_review, version.id)
    return detail_out(session, sub)


@app.post("/api/submissions/{submission_id}/decision")
def decide(submission_id: int, body: DecisionIn, reviewer: ReviewerDep, session: SessionDep):
    sub = get_submission(session, submission_id)
    workflow.decide(session, sub, body.decision, reviewer, body.note)
    session.commit()
    return detail_out(session, sub)


@app.patch("/api/findings/{finding_id}")
def triage(finding_id: int, body: TriageIn, _: ReviewerDep, session: SessionDep):
    finding = session.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, "Finding not found")
    workflow.triage(session, finding, body.status)
    session.commit()
    return detail_out(session, get_submission(session, finding.submission_id))


@app.get("/api/metrics")
def get_metrics(session: SessionDep):
    return metrics.compute(session)


@app.post("/api/demo/reset")
def reset_demo():
    reset_db()
    with Session(engine) as session:
        seed(session)
    return {"ok": True}
