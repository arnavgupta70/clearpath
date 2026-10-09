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
      <Link to="/queue" className="text-sm text-ink-2 hover:text-ink">← Queue</Link>
      <div className="mt-3 mb-5">
        <p className="flex items-center gap-2 text-sm text-ink-3">
          {sub.ref} <StatusBadge status={sub.status} /> <RiskBadge tier={sub.risk_tier} />
          {sub.status === 'in_review' && <span>{dueText(sub.due_at)}</span>}
        </p>
        <h1 className="mt-1 text-xl font-semibold">{sub.title}</h1>
        <p className="text-sm text-ink-2">
          {sub.submitter.name}
          {sub.partner && ` (${sub.partner})`} · {meta.products[sub.product]} · {meta.channels[sub.channel]} · submitted {timeAgo(sub.submitted_at)} ·
          assigned to {sub.assignee?.name ?? 'nobody'}
        </p>
        <p className="mt-1 text-xs text-ink-3">Risk score {sub.risk_score}: {sub.risk_factors.map((f) => `${f.label} (${f.points > 0 ? '+' : ''}${f.points})`).join(', ')}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Card
            title={
              <span className="flex items-center gap-2">
                {sub.versions.map((v) => (
                  <button key={v.number} onClick={() => setViewing(v.number)} className={clsx(v.number === viewing ? 'underline' : 'font-normal text-ink-2')}>
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
            {version.notes && <p className="mb-4 rounded bg-canvas px-3 py-2 text-sm">Note from {sub.submitter.name}: {version.notes}</p>}
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
          <div className="rounded-lg border border-line bg-surface p-3 text-sm">
            <p className="text-xs text-ink-3">Claude review</p>
            <p className="mt-1">{version.ai_status === 'pending' ? 'Running…' : version.ai_status === 'unavailable' ? 'Not configured on this server.' : version.ai_summary}</p>
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
              <ul className="list-inside list-disc text-sm text-ink-2">
                {fixed.map((f) => (
                  <li key={f.id}>{f.title}</li>
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
