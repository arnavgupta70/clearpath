# ClearView

A review tool for ClearPath Financial's (fictional) marketing compliance team, to replace the Excel tracker and the email threads.

Live demo: https://arnavgupta70.github.io/clearpath/

There's no login, just pick a user from the dropdown. The API runs on Render's free tier so the first load might take a minute while it wakes up. If you mess the data up there's a "Reset demo data" link on the start page.

## The problem

My guess is the reviewers aren't actually slow. The time goes into other stuff:

- Assets come in with mistakes a computer could have caught, like "guaranteed approval", a monthly payment with no APR, or a missing NMLS ID. Affiliates are the worst for this.
- Feedback lives in email, so every new round means re-reading the whole thing because nobody's sure what changed.
- It's all one queue. A clean display banner sits behind a mortgage landing page that'll take an hour.
- Nobody tracks which partners or which rules cause the most back and forth, so the same mistakes keep coming back.

So I tried to cut the number of rounds and the amount of reading per round, rather than just build a nicer spreadsheet.

## What it does

When someone writes a submission, the rules run as they type. Problems get highlighted (Reg Z trigger terms, UDAAP claims, "pre-approved", missing CAN-SPAM / TCPA / NMLS stuff) and most of them have approved wording you can drop in with one click. They also see the risk tier and roughly when they'll hear back.

Each submission gets a risk score from the product, channel, whether it's from an affiliate, and what the rules found. Low risk gets a 1 day turnaround. High risk mortgage and affiliate work goes to senior counsel, everything else goes to whichever analyst has the shortest queue. The review page shows how the score was added up so nobody has to guess.

Reviewers see the flagged text highlighted, mark each issue as required or dismiss it, and then request changes, approve, approve with conditions (small fixes, no extra round) or reject.

When something comes back, issues that got fixed close themselves, ones that didn't come across already marked, and there's a diff of what changed. Resubmissions get 1 day since only the changes need a look.

There's also an Insights page with cycle time and first-time approval rate by week, how each partner is doing, and which rules reviewers dismiss most (those probably need rewording or turning off).

Claude can run as a second reviewer after submit, for things a regex won't catch, like a payment example that doesn't line up with the APR. Its findings sit in the same list as the rule hits and a person still makes the call. I didn't put an API key on the live demo, so the Claude findings there are seeded and new submissions only get the rules.

If you want a quick tour: be Maya and start a new submission with "Load an example". Then be Jordan, go through the debt consolidation email, and open the LoanLadder newsletter (v2) with "show changes" ticked. Then be Dana and look at Insights.

## Some choices I made

Rules come first and Claude second. A regex with a citation next to it is easy to explain to an examiner, and Claude is only there for the judgment calls.

The pre-check warns, it doesn't block. If it blocked people they'd just go back to email.

It's text only for now since that's most of the volume. Images and PDFs would go through the same flow.

No real auth, just a user picker, so you can try every role quickly.

The demo data isn't inserted directly. The seed script calls the same workflow functions the app uses, with older timestamps, so the demo can't drift from how the app actually behaves.

## Assumptions

I assumed 2 or 3 reviewers, somewhere around 50 to 100 assets a week, and a handful of affiliates. The product details (APR ranges, soft vs hard pull, funding times, the NMLS ID) are made up. The regulations cited are real but the rule set is just an example, not legal advice.

## If I kept going

- Check live affiliate pages against the version we approved
- Images and PDFs
- Slack or email notifications
- A page where compliance can edit the rules, and test a change against past submissions first
- Evals for the Claude reviewer using what reviewers accepted and dismissed

## Running it locally

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

Everything works without an API key. If you want the Claude review, set `ANTHROPIC_API_KEY` before starting the API.

## Deploying

The frontend goes to GitHub Pages through `.github/workflows/pages.yml` on every push to `main`. In the repo settings set Pages source to "GitHub Actions" and add an Actions variable called `API_URL` pointing at the API.

The API is a free Render web service set up from `render.yaml`. You can add `ANTHROPIC_API_KEY` there too if you want Claude on.

## Where things are

```
backend/app/
  main.py       routes
  models.py     tables
  rules.py      the rules, the matcher, approved wording
  risk.py       score, tier, SLA
  workflow.py   submit, triage, decide, resubmit
  ai.py         Claude review
  serialize.py  what the API sends back
  metrics.py    insights numbers
  seed.py       demo data
frontend/src/
  pages/        one per screen
  components/   highlighting, diff, review bits
  lib/          api client, current user, a few hooks
```
