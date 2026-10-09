import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { RiskBadge, StatusBadge } from '../components/badges'
import { Loading, PageHeader } from '../components/ui'
import { api, type SubmissionSummary } from '../lib/api'
import { dueText, isOverdue, plural, timeAgo } from '../lib/format'
import { usePersona, useUser } from '../lib/persona'

const TABS = { mine: 'Assigned to me', all: 'All in review', decided: 'Decided' }
type Tab = keyof typeof TABS

export function Queue() {
  const user = useUser()
  const [tab, setTab] = useState<Tab>('mine')
  const { data, error } = useQuery({ queryKey: ['submissions'], queryFn: () => api.submissions() })
  if (error) return <p className="text-critical-text">{error.message}</p>
  if (!data) return <Loading />

  function inTab(sub: SubmissionSummary, tab: Tab) {
    if (tab === 'decided') return sub.decided_at !== null
    return sub.status === 'in_review' && (tab === 'all' || sub.assignee?.id === user.id)
  }

  const rows = data.filter((s) => inTab(s, tab))
  if (tab === 'decided') rows.sort((a, b) => (b.decided_at ?? '').localeCompare(a.decided_at ?? ''))
  else rows.sort((a, b) => a.due_at.localeCompare(b.due_at))

  return (
    <>
      <PageHeader title="Review queue" />
      <div className="mb-3 flex gap-1">
        {(Object.keys(TABS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx('rounded-md px-3 py-1.5 text-sm', tab === t ? 'bg-ink text-white' : 'text-ink-2 hover:bg-surface')}
          >
            {TABS[t]} ({data.filter((s) => inTab(s, t)).length})
          </button>
        ))}
      </div>
      <div className="divide-y divide-line rounded-lg border border-line bg-surface">
        {rows.length === 0 && <p className="p-8 text-center text-sm text-ink-2">Nothing here.</p>}
        {rows.map((sub) => (
          <Row key={sub.id} sub={sub} />
        ))}
      </div>
    </>
  )
}

function Row({ sub }: { sub: SubmissionSummary }) {
  const { meta } = usePersona()
  const openIssues = sub.counts.critical + sub.counts.major + sub.counts.minor

  return (
    <Link to={`/review/${sub.id}`} className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 py-3 hover:bg-canvas">
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {sub.title} {sub.current_version > 1 && <span className="text-xs text-brand">v{sub.current_version}</span>}
        </p>
        <p className="text-sm text-ink-2">
          {sub.ref} · {sub.partner ?? sub.submitter.name} · {meta.products[sub.product]} · {meta.channels[sub.channel]}
        </p>
      </div>
      <RiskBadge tier={sub.risk_tier} />
      {sub.status === 'in_review' ? (
        <>
          <span className="w-24 text-sm text-ink-2">{plural(openIssues, 'issue')}</span>
          <span className="w-28 text-sm text-ink-2">{sub.assignee?.name}</span>
          <span className={clsx('w-28 text-sm', isOverdue(sub.due_at) ? 'font-medium text-critical-text' : 'text-ink-2')}>{dueText(sub.due_at)}</span>
        </>
      ) : (
        <>
          <StatusBadge status={sub.status} />
          <span className="w-28 text-sm text-ink-2">{sub.decided_at && timeAgo(sub.decided_at)}</span>
        </>
      )}
    </Link>
  )
}
