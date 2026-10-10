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

const EDGE = { critical: 'border-l-critical', major: 'border-l-major', minor: 'border-l-minor-text' }

export function FindingCard({ finding, selected, editable, carriedOver, onSelect, onTriage }: Props) {
  return (
    <div
      onClick={onSelect}
      className={clsx(
        'cursor-pointer rounded-lg border border-l-4 bg-surface p-3 text-sm shadow-sm transition',
        EDGE[finding.severity],
        selected ? 'border-y-brand border-r-brand ring-2 ring-brand/15' : 'border-y-line border-r-line hover:shadow',
        finding.status === 'dismissed' && 'opacity-60',
      )}
    >
      <p className="flex flex-wrap items-center gap-2">
        <SeverityLabel severity={finding.severity} />
        <span className="rounded bg-canvas px-1.5 py-px font-mono text-[11px] text-ink-2">{finding.source === 'ai' ? 'Claude' : finding.rule_id}</span>
        {carriedOver && <span className="text-xs font-medium text-major-text">not fixed in last version</span>}
      </p>
      <p className="mt-1.5 font-medium">{finding.title}</p>
      <p className="text-ink-2 italic">{finding.quote ? `“${finding.quote}”` : 'Missing from the asset'}</p>

      {selected && (
        <div className="mt-2 space-y-2 text-ink-2">
          <p>{finding.explanation}</p>
          {finding.suggestion && <p className="rounded-md bg-canvas px-3 py-2 text-ink">Fix: {finding.suggestion}</p>}
          {finding.citation && <p className="text-xs text-ink-3">{finding.citation}</p>}
        </div>
      )}

      {editable && (
        <div className="mt-3 flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {finding.status === 'open' ? (
            <>
              <Button variant="primary" onClick={() => onTriage('accepted')}>Require change</Button>
              <Button onClick={() => onTriage('dismissed')}>Dismiss</Button>
            </>
          ) : (
            <>
              <span className={clsx('text-sm font-medium', finding.status === 'accepted' ? 'text-brand' : 'text-ink-3')}>
                {finding.status === 'accepted' ? '✓ Required change' : 'Dismissed'}
              </span>
              <button onClick={() => onTriage('open')} className="ml-auto text-ink-3 hover:text-ink">
                Undo
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
