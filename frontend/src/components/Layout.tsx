import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { isReviewer, usePersona } from '../lib/persona'

const REVIEWER_LINKS = [
  { to: '/queue', label: 'Queue' },
  { to: '/insights', label: 'Insights' },
]
const SUBMITTER_LINKS = [
  { to: '/submissions', label: 'My submissions' },
  { to: '/submissions/new', label: 'New submission' },
]

export function Layout() {
  const { user, meta, switchUser } = usePersona()
  const navigate = useNavigate()
  const links = user && isReviewer(user) ? REVIEWER_LINKS : SUBMITTER_LINKS

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to="/" className="font-semibold">ClearView</Link>
          <nav className="flex gap-4 text-sm">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} end className={({ isActive }) => (isActive ? 'font-medium' : 'text-ink-2 hover:text-ink')}>
                {link.label}
              </NavLink>
            ))}
          </nav>
          {user && (
            <label className="ml-auto text-sm text-ink-2">
              Viewing as{' '}
              <select
                value={user.id}
                onChange={(e) => {
                  switchUser(Number(e.target.value))
                  navigate('/')
                }}
                className="rounded border border-line-strong bg-surface px-1 py-0.5 text-ink"
              >
                {meta.users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.role === 'affiliate' ? u.org : u.title})
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
