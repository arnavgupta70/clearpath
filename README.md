# ClearView

Marketing compliance review for ClearPath Financial (fictional), replacing the Excel tracker + email threads.

Demo: https://arnavgupta70.github.io/clearpath/. Sign in as anyone. The API is on Render's free tier, so the first load can take up to a minute.

## The problem

I don't think the reviewers are the bottleneck. Most of the time goes to:

- assets showing up with problems a machine could have caught ("guaranteed approval", a monthly payment with no APR, no NMLS ID), especially from affiliates
- every round needing a full re-read because feedback lives in email and nobody knows what changed
- everything sitting in one queue, so a clean banner waits behind a mortgage landing page
- no record of which partners or rules cause the most rework, so the same mistakes repeat

So the goal is fewer rounds and less reading per round, not a faster spreadsheet.

## What's in it

- **Pre-check while writing.** Submitters see issues highlighted as they type (Reg Z trigger terms, UDAAP claims, "pre-approved", missing CAN-SPAM / TCPA / NMLS bits) and can insert pre-approved wording in one click. They also see their risk tier and when to expect a decision.
- **Claude as a second reviewer.** After submit, Claude reads the copy for things regex can't catch, like a payment example that doesn't match the APR. Its findings go in the same list as the rule hits; a person still decides.
- **Risk routing.** Each submission gets a score (product, channel, affiliate or not, issues found). Low risk gets a 1-day SLA, high-risk mortgage and affiliate work goes to senior counsel. The review page shows how the score was built.
- **Triage.** The reviewer sees the flagged quotes highlighted, marks each finding required or dismissed, then requests changes, approves, approves with conditions (minor fixes, no extra round), or rejects.
- **Resubmissions only show what changed.** Fixed items resolve on their own, unfixed ones carry over already marked, and the reviewer sees a diff. Resubmissions get a 1-day SLA.
- **Insights.** Cycle time and first-time approval rate by week, a partner comparison, and rules reviewers keep dismissing (those are worth rewording or turning off).

Quick tour: as **Maya**, start a new submission and hit "Load an example". As **Jordan**, triage the debt consolidation email, then open the LoanLadder newsletter (v2) and tick "show changes". As **Dana**, look at Insights.

## Decisions

- Rules first, Claude second. A regex with a citation is easy to explain to an examiner. Claude covers the judgment calls but never decides anything.
- Text only for now. That's most of the volume; images/PDFs would go through the same flow.
- The pre-check warns but doesn't block. Blocking would push people back to email.
- No real auth, just a user picker, so it's quick to try every role.
- SQLite with seeded data. The seed runs the real workflow functions with old timestamps instead of inserting rows, so the demo can't drift from the actual behavior.

## Assumptions

- 2–3 reviewers, roughly 50–100 assets a week, a handful of affiliates.
- Product facts (APR ranges, soft vs hard pull, funding times, NMLS ID) are made up.
- The citations are real regulations but the rule set is illustrative, not legal advice.

## Next

- Check live affiliate pages against what was approved
- Images and PDFs
- Slack/email notifications
- A rule library page so compliance can edit rules, with a backtest against past submissions
- Evals for the Claude reviewer using the accept/dismiss history

## Running it

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload   # :8000, seeds itself on first run
uv run pytest
```

```bash
cd frontend
npm install
npm run dev                            # :5173
```

Set `ANTHROPIC_API_KEY` before starting the API to turn on the Claude review. Without it everything else works.

## Deploying

- Frontend: `.github/workflows/pages.yml` publishes to GitHub Pages on push to `main`. Set Pages → Source to "GitHub Actions" and add an Actions variable `API_URL`.
- API: `render.yaml` sets up a free Render web service. Add `ANTHROPIC_API_KEY` there.

## Layout

```
backend/app/
  rules.py      the rules, the matcher, approved wording
  risk.py       score -> tier -> SLA
  workflow.py   submit, triage, decide, resubmit
  ai.py         Claude review
  metrics.py    insights
  seed.py       demo data
frontend/src/
  pages/        one per screen
  components/   highlighting, diff, review panel
  lib/          api client, current user, small hooks
```
