import clsx from 'clsx'
import type { Finding } from '../lib/api'
import { SeverityLabel } from './badges'
import { Button } from './ui'

interface Props {
  finding: Finding
  selected: boolean
  editable: boolean
  carriedOver: boolean
  onSelect: () => void
  onTriage: (status: 'open' | 'accepted' | 'dismissed') => void
}

export function FindingCard({ finding, selected, editable, carriedOver, onSelect, onTriage }: Props) {
  return (
    <div
      onClick={onSelect}
      className={clsx(
        'cursor-pointer rounded-lg border bg-surface p-3 text-sm',
        selected ? 'border-brand' : 'border-line hover:border-line-strong',
        finding.status === 'dismissed' && 'opacity-60',
      )}
    >
      <p className="flex gap-2">
        <SeverityLabel severity={finding.severity} />
        <span className="font-mono text-xs text-ink-3">{finding.source === 'ai' ? 'Claude' : finding.rule_id}</span>
        {carriedOver && <span className="text-xs text-major-text">not fixed in last version</span>}
      </p>
      <p className="mt-1 font-medium">{finding.title}</p>
      <p className="text-ink-2 italic">{finding.quote ? `“${finding.quote}”` : 'Missing from the asset'}</p>

      {selected && (
        <div className="mt-2 space-y-1 text-ink-2">
          <p>{finding.explanation}</p>
          {finding.suggestion && <p className="text-ink">Fix: {finding.suggestion}</p>}
          {finding.citation && <p className="text-xs text-ink-3">{finding.citation}</p>}
        </div>
      )}

      {editable && (
        <div className="mt-2 flex gap-2" onClick={(e) => e.stopPropagation()}>
          {finding.status === 'open' ? (
            <>
              <Button variant="primary" onClick={() => onTriage('accepted')}>Require</Button>
              <Button onClick={() => onTriage('dismissed')}>Dismiss</Button>
            </>
          ) : (
            <button onClick={() => onTriage('open')} className="text-ink-2 hover:text-ink">
              {finding.status === 'accepted' ? 'Required' : 'Dismissed'} · undo
            </button>
          )}
        </div>
      )}
    </div>
  )
}
