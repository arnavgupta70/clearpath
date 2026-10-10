import clsx from 'clsx'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ActivityLog } from '../components/ActivityLog'
import { RiskBadge, StatusBadge } from '../components/badges'
import { DiffText } from '../components/DiffText'
import { FindingCard } from '../components/FindingCard'
import { HighlightedText } from '../components/HighlightedText'
import { Button, Card, Loading } from '../components/ui'
import { api, type Decision, type Finding, type Submission } from '../lib/api'
import { dueText, SEVERITY_ORDER, timeAgo } from '../lib/format'
import { usePersona } from '../lib/persona'
import { useSaveSubmission, useSubmission } from '../lib/useSubmission'

export function Review() {
  const id = Number(useParams().id)
  const { data, error } = useSubmission(id)
  if (error) return <p className="text-critical-text">{error.message}</p>
  if (!data) return <Loading />
  return <ReviewPage key={id} sub={data} />
}

const bySeverity = (a: Finding, b: Finding) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)

function ReviewPage({ sub }: { sub: Submission }) {
  const { meta } = usePersona()
  const { save, error } = useSaveSubmission(sub.id)
  const [viewing, setViewing] = useState(sub.current_version)
  const [showChanges, setShowChanges] = useState(sub.current_version > 1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [note, setNote] = useState('')

  const version = sub.versions[viewing - 1]
  const previous = sub.versions[viewing - 2]
  const editable = viewing === sub.current_version && sub.status === 'in_review'
  const findings = version.findings.filter((f) => f.status !== 'resolved')
  const fixed = previous?.findings.filter((f) => f.status === 'resolved') ?? []
  const required = findings.filter((f) => f.status === 'accepted')

  const groups = [
    { title: 'To review', items: findings.filter((f) => f.status === 'open').sort(bySeverity) },
    { title: 'Required changes', items: required.sort(bySeverity) },
    { title: 'Dismissed', items: findings.filter((f) => f.status === 'dismissed') },
  ]

  function decide(decision: Decision) {
    save(api.decide(sub.id, decision, note.trim() || undefined))
  }

  return (
    <>
      <Link to="/queue" className="text-sm text-ink-2 hover:text-ink">← Back to queue</Link>
      <div className="mt-3 mb-6 rounded-xl border border-line bg-surface p-5 shadow-sm">
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-mono text-ink-3">{sub.ref}</span>
          <StatusBadge status={sub.status} />
          <RiskBadge tier={sub.risk_tier} />
          {sub.status === 'in_review' && <span className="text-ink-2">· {dueText(sub.due_at)}</span>}
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{sub.title}</h1>
        <p className="mt-1 text-sm text-ink-2">
          {sub.submitter.name}
          {sub.partner && ` (${sub.partner})`} · {meta.products[sub.product]} · {meta.channels[sub.channel]} · submitted{' '}
          {timeAgo(sub.versions[sub.current_version - 1].created_at)} · reviewer {sub.assignee?.name ?? 'unassigned'}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="font-medium text-ink-2">Risk score {sub.risk_score}</span>
          {sub.risk_factors.map((f) => (
            <span key={f.label} className="rounded-full bg-canvas px-2 py-0.5 text-ink-2">
              {f.label} <span className="text-ink-3">{f.points > 0 ? '+' : ''}{f.points}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Card
            title={
              <span className="flex items-center gap-1">
                {sub.versions.map((v) => (
                  <button
                    key={v.number}
                    onClick={() => setViewing(v.number)}
                    className={clsx('rounded-md px-2.5 py-0.5', v.number === viewing ? 'bg-brand text-white' : 'font-normal text-ink-2 hover:bg-canvas')}
                  >
                    v{v.number}
                  </button>
                ))}
                {previous && (
                  <label className="ml-auto flex items-center gap-1 font-normal text-ink-2">
                    <input type="checkbox" checked={showChanges} onChange={(e) => setShowChanges(e.target.checked)} /> show changes
                  </label>
                )}
              </span>
            }
          >
            {version.notes && (
              <p className="mb-5 rounded-lg border-l-4 border-brand bg-brand-soft/50 px-4 py-2 text-sm">
                <span className="font-medium">{sub.submitter.name}:</span> {version.notes}
              </p>
            )}
            {showChanges && previous ? (
              <DiffText before={previous.content} after={version.content} />
            ) : (
              <HighlightedText text={version.content} findings={findings.filter((f) => f.status !== 'dismissed')} selectedId={selectedId} />
            )}
          </Card>
          <Card title="Activity">
            <ActivityLog events={sub.events} />
          </Card>
        </div>

        <div className="space-y-5">
          <div className="rounded-xl border border-line bg-surface p-4 text-sm shadow-sm">
            <p className="text-xs font-semibold text-ink-3 uppercase">Claude review</p>
            <p className="mt-1.5 leading-relaxed">{version.ai_status === 'pending' ? 'Running…' : version.ai_status === 'unavailable' ? 'Not configured on this server.' : version.ai_summary}</p>
          </div>

          {groups.map(
            (group) =>
              group.items.length > 0 && (
                <section key={group.title}>
                  <h2 className="mb-2 text-xs font-semibold text-ink-3 uppercase">
                    {group.title} ({group.items.length})
                  </h2>
                  <div className="space-y-2">
                    {group.items.map((f) => (
                      <FindingCard
                        key={f.id}
                        finding={f}
                        selected={f.id === selectedId}
                        editable={editable}
                        carriedOver={f.carried_from !== null}
                        onSelect={() => setSelectedId(f.id)}
                        onTriage={(status) => save(api.triage(f.id, status))}
                      />
                    ))}
                  </div>
                </section>
              ),
          )}

          {fixed.length > 0 && (
            <section>
              <h2 className="mb-2 text-xs font-semibold text-ink-3 uppercase">Fixed in v{viewing}</h2>
              <ul className="space-y-1 text-sm text-ink-2">
                {fixed.map((f) => (
                  <li key={f.id}>
                    <span className="mr-1.5 font-semibold text-good-text">✓</span>
                    {f.title}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {editable ? (
            <Card title="Decision">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                placeholder="Note to the submitter (needed to reject)"
                className="w-full rounded border border-line-strong px-2 py-1.5 text-sm"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {required.length === 0 && <Button variant="primary" onClick={() => decide('approve')}>Approve</Button>}
                <Button variant={required.length ? 'primary' : 'secondary'} onClick={() => decide('request_changes')}>
                  Request changes
                </Button>
                {required.length > 0 && <Button onClick={() => decide('approve_with_conditions')}>Approve with conditions</Button>}
                <Button variant="danger" onClick={() => decide('reject')}>Reject</Button>
              </div>
              {error && <p className="mt-2 text-sm text-critical-text">{error}</p>}
            </Card>
          ) : (
            sub.status !== 'in_review' && (
              <Card title="Decision">
                <StatusBadge status={sub.status} />
                {sub.approval_code && <p className="mt-2 font-mono text-sm">{sub.approval_code}</p>}
                {sub.decision_note && <p className="mt-2 text-sm italic">“{sub.decision_note}”</p>}
              </Card>
            )
          )}
        </div>
      </div>
    </>
  )
}
