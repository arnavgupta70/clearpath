import clsx from 'clsx'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { isReviewer, usePersona } from '../lib/persona'
import { Avatar } from './badges'
import { Logo } from './ui'

const REVIEWER_LINKS = [
  { to: '/queue', label: 'Queue' },
  { to: '/insights', label: 'Insights' },
]
const TEAMS = [
  { label: 'Marketing', roles: ['marketer'] },
  { label: 'Affiliate partners', roles: ['affiliate'] },
  { label: 'Compliance', roles: ['reviewer', 'lead'] },
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
      <header className="sticky top-0 z-10 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3">
          <Link to="/">
            <Logo />
          </Link>
          <nav className="flex gap-1 text-sm">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end
                className={({ isActive }) => clsx('rounded-md px-3 py-1.5', isActive ? 'bg-brand-soft font-medium text-brand' : 'text-ink-2 hover:bg-canvas hover:text-ink')}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          {user && (
            <label className="ml-auto flex items-center gap-2 text-sm">
              <Avatar user={user} />
              <select
                value={user.id}
                onChange={(e) => {
                  switchUser(Number(e.target.value))
                  navigate('/')
                }}
                className="max-w-64 truncate rounded-md border border-line bg-surface py-1 pr-1 pl-2 font-medium hover:border-line-strong"
                aria-label="Viewing as"
              >
                {TEAMS.map((team) => (
                  <optgroup key={team.label} label={team.label}>
                    {meta.users
                      .filter((u) => team.roles.includes(u.role))
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.role === 'affiliate' ? `${u.name} (${u.org})` : u.name}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
            </label>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
