import clsx from 'clsx'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { isReviewer, usePersona } from '../lib/persona'
import { Avatar } from './badges'
import { Logo } from './ui'

const REVIEWER_LINKS = [
  { to: '/queue', label: 'Queue' },
  { to: '/insights', label: 'Insights' },
]
const SUBMITTER_LINKS = [
  { to: '/submissions', label: 'My submissions' },
  { to: '/submissions/new', label: 'New submission' },
]

export function Layout() {
  const { user, signOut } = usePersona()
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
            <div className="ml-auto flex items-center gap-3 text-sm">
              <Avatar user={user} />
              <span className="font-medium">{user.role === 'affiliate' ? `${user.name} (${user.org})` : user.name}</span>
              <button onClick={signOut} className="rounded-md px-2 py-1 text-ink-2 hover:bg-canvas hover:text-ink">
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
