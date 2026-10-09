import clsx from 'clsx'
import type { Finding } from '../lib/api'

// Marks each flagged quote in the copy. If two findings overlap, only the first is marked.
export function HighlightedText({ text, findings, selectedId }: { text: string; findings: Finding[]; selectedId?: number | null }) {
  const spans = findings
    .flatMap((f) => (f.start !== null && f.end !== null ? [{ id: f.id, start: f.start, end: f.end }] : []))
    .sort((a, b) => a.start - b.start)

  const parts = []
  let position = 0
  for (const span of spans) {
    if (span.start < position) continue
    parts.push(text.slice(position, span.start))
    parts.push(
      <mark key={span.id} className={clsx('rounded-sm px-0.5', span.id === selectedId ? 'bg-brand-soft outline-2 outline-brand' : 'bg-minor-soft')}>
        {text.slice(span.start, span.end)}
      </mark>,
    )
    position = span.end
  }
  parts.push(text.slice(position))

  return <div className="max-w-prose text-[15px] leading-7 whitespace-pre-wrap">{parts}</div>
}
