import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ActivityLog } from '../components/ActivityLog'
import { SeverityIcon, StatusBadge } from '../components/badges'
import { HighlightedText } from '../components/HighlightedText'
import { PrecheckPanel } from '../components/PrecheckPanel'
import { Button, Card, inputClass, Loading } from '../components/ui'
import { api, type Submission } from '../lib/api'
import { formatDateTime } from '../lib/format'
import { usePersona } from '../lib/persona'
import { withSnippet } from '../lib/snippets'
import { usePrecheck } from '../lib/usePrecheck'
import { useSaveSubmission, useSubmission } from '../lib/useSubmission'

export function SubmissionDetail() {
  const id = Number(useParams().id)
  const { data, error } = useSubmission(id)
  if (error) return <p className="text-critical-text">{error.message}</p>
  if (!data) return <Loading />
  return <SubmissionPage key={id} sub={data} />
}

const BANNER: Record<Submission['status'], string> = {
  in_review: 'border-brand bg-brand-soft/60',
  changes_requested: 'border-major bg-major-soft',
  approved: 'border-good-text bg-good-soft',
  approved_with_conditions: 'border-good-text bg-good-soft',
  rejected: 'border-critical bg-critical-soft',
}

function statusMessage(sub: Submission) {
  switch (sub.status) {
    case 'in_review':
      return `${sub.assignee?.name ?? 'Compliance'} is reviewing it. Expect a decision by ${formatDateTime(sub.due_at)}.`
    case 'changes_requested':
      return 'Compliance asked for the changes below. Resubmissions are reviewed within a business day.'
    case 'approved':
      return `Approved. Put ${sub.approval_code} in your launch ticket.`
    case 'approved_with_conditions':
      return `Approved (${sub.approval_code}) as long as you make these changes before launch: ${sub.conditions.join(' ')}`
    case 'rejected':
      return 'Rejected.'
  }
}

function SubmissionPage({ sub }: { sub: Submission }) {
  const { meta } = usePersona()
  const [revising, setRevising] = useState(false)
  const current = sub.versions[sub.current_version - 1]
  const required = current.findings.filter((f) => f.status === 'accepted')

  return (
    <>
      <Link to="/submissions" className="text-sm text-ink-2 hover:text-ink">← My submissions</Link>
      <div className="mt-3 mb-5">
        <p className="flex items-center gap-2 text-sm text-ink-3">
          <span className="font-mono">{sub.ref}</span> <StatusBadge status={sub.status} /> v{sub.current_version}
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{sub.title}</h1>
        <p className="text-sm text-ink-2">
          {meta.products[sub.product]} · {meta.channels[sub.channel]}
        </p>
      </div>

      <div className={`mb-6 rounded-xl border-l-4 p-5 text-sm shadow-sm ${BANNER[sub.status]}`}>
        <p>{statusMessage(sub)}</p>
        {sub.decision_note && sub.status !== 'in_review' && <p className="mt-2 italic">“{sub.decision_note}”</p>}
        {sub.status === 'changes_requested' && !revising && (
          <Button variant="primary" className="mt-3" onClick={() => setRevising(true)}>Revise and resubmit</Button>
        )}
      </div>

      {revising ? (
        <Revise sub={sub} onDone={() => setRevising(false)} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-6">
            <Card title={`Version ${current.number}`}>
              <HighlightedText text={current.content} findings={required} />
            </Card>
            <Card title="History">
              <ActivityLog events={sub.events} />
            </Card>
          </div>
          {sub.status === 'changes_requested' && <RequiredChanges sub={sub} />}
        </div>
      )}
    </>
  )
}

function RequiredChanges({ sub }: { sub: Submission }) {
  const required = sub.versions[sub.current_version - 1].findings.filter((f) => f.status === 'accepted')
  return (
    <ul className="space-y-2">
      {required.map((f) => (
        <li key={f.id} className="flex gap-2 rounded-xl border border-line bg-surface p-4 text-sm shadow-sm">
          <SeverityIcon severity={f.severity} />
          <div>
            <p className="font-medium">{f.title}</p>
            {f.quote && <p className="text-ink-2 italic">“{f.quote}”</p>}
            {f.suggestion && <p className="mt-1">{f.suggestion}</p>}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Revise({ sub, onDone }: { sub: Submission; onDone: () => void }) {
  const [content, setContent] = useState(sub.versions[sub.current_version - 1].content)
  const [notes, setNotes] = useState('')
  const precheck = usePrecheck(content, sub.product, sub.channel)
  const { save, error } = useSaveSubmission(sub.id)

  async function resubmit() {
    await save(api.resubmit(sub.id, content, notes || undefined))
    onDone()
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={14} className={`${inputClass} leading-7`} />
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          placeholder="What changed? (optional)"
          className={inputClass}
        />
        {error && <p className="text-sm text-critical-text">{error}</p>}
        <div className="flex gap-2">
          <Button variant="primary" onClick={resubmit}>Resubmit</Button>
          <Button onClick={onDone}>Cancel</Button>
        </div>
      </div>
      <div className="space-y-4">
        <RequiredChanges sub={sub} />
        <PrecheckPanel content={content} result={precheck.data} onInsert={(snippet) => setContent(withSnippet(content, snippet))} />
      </div>
    </div>
  )
}
