import type { Precheck, Snippet } from '../lib/api'
import { formatDateTime } from '../lib/format'
import { usePersona } from '../lib/persona'
import { snippetToInsert } from '../lib/snippets'
import { RiskBadge, SeverityIcon } from './badges'

export function PrecheckPanel({ content, result, onInsert }: { content: string; result?: Precheck; onInsert: (snippet: Snippet) => void }) {
  const { meta } = usePersona()

  if (!content.trim() || !result) {
    return <p className="rounded-xl border border-dashed border-line-strong p-6 text-center text-sm text-ink-2">Compliance issues show up here as you type.</p>
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line bg-canvas px-4 py-3 text-sm">
        <p className="font-semibold">{result.findings.length ? `Pre-check: ${result.findings.length} things to fix` : 'Pre-check: all clear ✓'}</p>
        <p className="mt-1 text-ink-2">
          <RiskBadge tier={result.risk_tier} /> · decision expected by {formatDateTime(result.estimated_decision_by)}
        </p>
      </div>
      <ul className="divide-y divide-line">
        {result.findings.map((issue, i) => {
          const snippet = snippetToInsert(meta, issue.rule_id, content)
          return (
            <li key={i} className="flex gap-2 px-4 py-3 text-sm">
              <SeverityIcon severity={issue.severity} />
              <div>
                <p className="font-medium">{issue.title}</p>
                {issue.quote && <p className="text-ink-2 italic">“{issue.quote}”</p>}
                {issue.suggestion && <p className="mt-1 text-ink-2">{issue.suggestion}</p>}
                {snippet && (
                  <button onClick={() => onInsert(snippet)} className="mt-1 font-medium text-brand hover:underline">
                    + Insert approved wording
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
