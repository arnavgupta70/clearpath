import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/badges'
import { Loading, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { timeAgo } from '../lib/format'
import { usePersona } from '../lib/persona'

export function MySubmissions() {
  const { meta } = usePersona()
  const { data, error } = useQuery({ queryKey: ['submissions', 'mine'], queryFn: () => api.submissions(true) })
  if (error) return <p className="text-critical-text">{error.message}</p>
  if (!data) return <Loading />

  // things waiting on you first
  const sorted = [...data].sort((a, b) => Number(b.status === 'changes_requested') - Number(a.status === 'changes_requested'))

  return (
    <>
      <PageHeader title="My submissions" actions={<Link to="/submissions/new" className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white">New submission</Link>} />
      {sorted.length === 0 && <p className="text-sm text-ink-2">Nothing submitted yet.</p>}
      <div className="divide-y divide-line rounded-lg border border-line bg-surface">
        {sorted.map((sub) => (
          <Link key={sub.id} to={`/submissions/${sub.id}`} className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 py-3 hover:bg-canvas">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{sub.title}</p>
              <p className="text-sm text-ink-2">
                {sub.ref} · {meta.products[sub.product]} · {meta.channels[sub.channel]} · updated {timeAgo(sub.updated_at)}
              </p>
            </div>
            <StatusBadge status={sub.status} />
          </Link>
        ))}
      </div>
    </>
  )
}
