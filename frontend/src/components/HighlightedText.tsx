import clsx from 'clsx'
import type { Finding } from '../lib/api'

const MARK_COLOR = {
  critical: 'bg-critical-soft decoration-critical',
  major: 'bg-major-soft decoration-major',
  minor: 'bg-minor-soft decoration-minor-text',
}

// Marks each flagged quote in the copy, tinted by severity. If two findings overlap, only the first is marked.
export function HighlightedText({ text, findings, selectedId }: { text: string; findings: Finding[]; selectedId?: number | null }) {
  const spans = findings
    .flatMap((f) => (f.start !== null && f.end !== null ? [{ id: f.id, start: f.start, end: f.end, severity: f.severity }] : []))
    .sort((a, b) => a.start - b.start)

  const parts = []
  let position = 0
  for (const span of spans) {
    if (span.start < position) continue
    parts.push(text.slice(position, span.start))
    parts.push(
      <mark
        key={span.id}
        className={clsx(
          'rounded-sm px-0.5 text-ink underline decoration-2 underline-offset-4',
          MARK_COLOR[span.severity],
          span.id === selectedId && 'outline-2 outline-offset-1 outline-brand',
        )}
      >
        {text.slice(span.start, span.end)}
      </mark>,
    )
    position = span.end
  }
  parts.push(text.slice(position))

  return <div className="max-w-prose text-[15px] leading-8 whitespace-pre-wrap">{parts}</div>
}
