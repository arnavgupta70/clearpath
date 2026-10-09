"""Second review by Claude, for things regex can't catch (misleading overall impressions,
buried disclosures, numbers that don't add up). A reviewer still accepts or dismisses each finding.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import cache

import anthropic

from .rules import RULE_LIBRARY, SNIPPETS

log = logging.getLogger(__name__)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")
CATEGORIES = sorted({r.category for r in RULE_LIBRARY} | {"Clear & conspicuous", "Accuracy"})


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _system_prompt() -> str:
    # only static data in here so the prompt cache hits
    rules = "\n".join(
        f"- [{r.id}] {r.name} ({r.category}, {r.severity}; {r.citation}): {r.explanation}" for r in RULE_LIBRARY
    )
    snippets = "\n".join(f"- {s['title']}: {s['body']}" for s in SNIPPETS)
    return f"""You are a senior marketing-compliance reviewer at ClearPath Financial, a US consumer lender that offers personal loans, credit cards, and mortgage prequalification online. You review advertising copy from ClearPath's own marketers and from paid affiliate partners before it is published.

## How ClearPath's products actually work (use these facts to spot inaccurate claims)
- Every application is underwritten. Approval is never guaranteed.
- Checking a rate / prequalifying is a soft credit inquiry. Submitting an application is a hard inquiry.
- The online flow is prequalification only. ClearPath does not send firm offers of credit, so nothing is "pre-approved".
- Personal loans: 7.99%–35.99% APR, $2,000–$50,000, 24–60 month terms, 0%–6% origination fee. Funding usually 1–3 business days after approval.
- Credit card: 0% intro APR on purchases for 15 months, then 21.24%–29.99% variable APR, $0 annual fee, 3% balance-transfer fee.
- Mortgage prequalification rates are estimates, not locked, not a commitment to lend. ClearPath's NMLS ID is #1849302.
- ClearPath has no substantiation on file for "lowest", "best" or "#1" claims.

## ClearPath's rule library
A deterministic engine already checks these rules with pattern matching:
{rules}

## Approved disclosure language
{snippets}

## Your job
You will receive one asset plus the findings the deterministic engine already raised. Find the problems the pattern matcher cannot catch, for example:
- misleading net impression, implied claims, or claims that contradict the product facts above
- disclosures that are present but not clear and conspicuous (buried, contradicted, or far from the claim they qualify)
- numbers that are inconsistent or don't add up (e.g. a payment example that doesn't match the stated APR and term)
- testimonials or comparisons without basis, pressure tactics, or targeting that could discourage protected groups
- anything a CFPB examiner would question that the rule list misses

Rules for your output:
- Do NOT repeat an issue the engine already raised for the same text.
- Be precise, not exhaustive. Report only issues a reasonable compliance reviewer would act on. Zero findings is a valid answer for clean copy. Report at most 6.
- `quote` must be copied character-for-character from the asset: the shortest span that pinpoints the problem. Use an empty string only for an issue about something missing from the asset as a whole.
- `related_rule_id` is the closest rule ID from the library, or an empty string.
- `suggestion` is a concrete compliant rewrite or fix, written so the marketer can apply it directly.
- `summary` is one or two sentences for the human reviewer: overall risk and the single most important fix."""


SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "title": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "severity": {"type": "string", "enum": ["critical", "major", "minor"]},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "related_rule_id": {"type": "string"},
                },
                "required": ["quote", "title", "category", "severity", "explanation", "suggestion", "related_rule_id"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "findings"],
    "additionalProperties": False,
}

@cache
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(timeout=120.0)


def locate(quote: str, text: str) -> tuple[int, int] | None:
    # Claude quotes text back; find it in the original even if case or whitespace drifted
    if not quote:
        return None
    i = text.find(quote)
    if i < 0:
        i = text.lower().find(quote.lower())
    if i >= 0:
        return i, i + len(quote)
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    match = re.search(pattern, text, re.IGNORECASE)
    return (match.start(), match.end()) if match else None


def finding(content: str, *, quote: str, title: str, category: str, severity: str, explanation: str,
            suggestion: str, rule_id: str | None) -> dict:
    span = locate(quote, content)
    return {
        "source": "ai",
        "rule_id": rule_id or None,
        "title": title,
        "category": category,
        "severity": severity,
        "explanation": explanation,
        "suggestion": suggestion,
        "quote": content[span[0]:span[1]] if span else None,
        "start": span[0] if span else None,
        "end": span[1] if span else None,
    }


@dataclass
class Review:
    summary: str
    findings: list[dict]


class AIUnavailable(Exception):
    pass


def analyze(content: str, product: str, channel: str, source: str, partner: str | None,
            already_flagged: list[tuple[str, str | None]]) -> Review:
    if not enabled():
        raise AIUnavailable("AI review is not configured on this server")

    flagged = "\n".join(f"- {rule_id}: “{quote or '(asset-level)'}”" for rule_id, quote in already_flagged) or "- (none)"
    author = f"affiliate partner {partner}" if source == "affiliate" else "ClearPath marketing"
    prompt = (
        f"Product: {product}\nChannel: {channel}\nProduced by: {author}\n\n"
        f"Findings already raised by the deterministic engine:\n{flagged}\n\n"
        f"<asset>\n{content}\n</asset>"
    )
    try:
        response = _client().beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=[{"type": "text", "text": _system_prompt(), "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise AIUnavailable("The Anthropic API key was rejected") from e
    except anthropic.RateLimitError as e:
        raise AIUnavailable("Rate limited by the Anthropic API; try again shortly") from e
    except anthropic.APIStatusError as e:
        log.warning("Claude API error %s (request %s): %s", e.status_code, e.request_id, e.message)
        raise AIUnavailable(f"Claude API error ({e.status_code})") from e
    except anthropic.APIConnectionError as e:
        raise AIUnavailable("Could not reach the Anthropic API") from e

    if response.stop_reason == "refusal":
        raise AIUnavailable("Claude declined to analyze this asset")
    if response.stop_reason == "max_tokens":
        raise AIUnavailable("Claude's response was truncated")

    data = json.loads(next(block.text for block in response.content if block.type == "text"))
    log.info("Claude review: %d findings, input=%s cache_read=%s output=%s", len(data["findings"]),
             response.usage.input_tokens, response.usage.cache_read_input_tokens, response.usage.output_tokens)
    findings = [
        finding(content, quote=f["quote"], title=f["title"], category=f["category"], severity=f["severity"],
                explanation=f["explanation"], suggestion=f["suggestion"], rule_id=f["related_rule_id"])
        for f in data["findings"][:6]
    ]
    return Review(data["summary"], findings)
