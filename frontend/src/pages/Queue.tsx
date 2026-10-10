import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, RiskBadge, StatusBadge } from '../components/badges'
import { Loading, PageHeader } from '../components/ui'
import { api, type SubmissionSummary } from '../lib/api'
import { dueText, isOverdue, plural, timeAgo } from '../lib/format'
import { usePersona, useUser } from '../lib/persona'

const TABS = { mine: 'Assigned to me', all: 'All in review', decided: 'Decided' }
// header and rows share one grid so the columns line up
const COLUMNS = 'grid gap-x-6 gap-y-2 md:grid-cols-[minmax(0,1fr)_8rem_13rem_10rem_6rem] md:items-center'
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
      <div className="mb-4 flex gap-1 rounded-lg bg-surface p-1 shadow-sm ring-1 ring-line w-fit">
        {(Object.keys(TABS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx('rounded-md px-3 py-1.5 text-sm', tab === t ? 'bg-brand text-white shadow-sm' : 'text-ink-2 hover:bg-canvas')}
          >
            {TABS[t]} ({data.filter((s) => inTab(s, t)).length})
          </button>
        ))}
      </div>
      <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className={clsx(COLUMNS, 'hidden bg-canvas px-5 py-2.5 text-xs font-medium text-ink-3 uppercase md:grid')}>
          <span>Submission</span>
          <span>Risk</span>
          <span>{tab === 'decided' ? 'Outcome' : 'Open issues'}</span>
          <span>Reviewer</span>
          <span>{tab === 'decided' ? 'Decided' : 'Due'}</span>
        </div>
        {rows.length === 0 && <p className="p-10 text-center text-sm text-ink-2">Nothing here. Nice.</p>}
        {rows.map((sub) => (
          <Row key={sub.id} sub={sub} />
        ))}
      </div>
    </>
  )
}

function Row({ sub }: { sub: SubmissionSummary }) {
  const { meta } = usePersona()

  return (
    <Link to={`/review/${sub.id}`} className={clsx(COLUMNS, 'px-5 py-4 transition hover:bg-brand-soft/40')}>
      <div className="min-w-0">
        <p className="font-medium">
          {sub.title}{' '}
          {sub.current_version > 1 && <span className="ml-1 rounded bg-brand-soft px-1.5 py-px text-xs font-medium text-brand">v{sub.current_version}</span>}
        </p>
        <p className="mt-0.5 text-sm text-ink-2">
          {sub.ref} · {sub.partner ?? sub.submitter.name} · {meta.products[sub.product]} · {meta.channels[sub.channel]}
        </p>
      </div>
      <span>
        <RiskBadge tier={sub.risk_tier} />
      </span>
      <span className="text-sm text-ink-2">{sub.status === 'in_review' ? plural(sub.open_issues, 'issue') : <StatusBadge status={sub.status} />}</span>
      <span className="flex min-w-0 items-center gap-2 text-sm text-ink-2">
        {sub.assignee && <Avatar user={sub.assignee} />}
        <span className="truncate">{sub.assignee?.name}</span>
      </span>
      {sub.status === 'in_review' ? (
        <span className={clsx('text-sm', isOverdue(sub.due_at) ? 'font-medium text-critical-text' : 'text-ink-2')}>{dueText(sub.due_at)}</span>
      ) : (
        <span className="text-sm text-ink-2">{sub.decided_at && timeAgo(sub.decided_at)}</span>
      )}
    </Link>
  )
}
