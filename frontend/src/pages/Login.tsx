import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/badges'
import { Button, inputClass, Logo } from '../components/ui'
import { api, type Role, type User } from '../lib/api'
import { usePersona } from '../lib/persona'

const TEAMS: { title: string; roles: Role[] }[] = [
  { title: 'Marketing', roles: ['marketer'] },
  { title: 'Affiliate partners', roles: ['affiliate'] },
  { title: 'Compliance', roles: ['reviewer', 'lead'] },
]

export function Login() {
  const { meta, signIn } = usePersona()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const submitButton = useRef<HTMLButtonElement>(null)

  const login = useMutation({
    mutationFn: () => api.login(email, password),
    onSuccess: ({ token, user }) => {
      signIn({ token, userId: user.id })
      navigate('/')
    },
  })
  const reset = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: () => queryClient.invalidateQueries(),
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    login.mutate()
  }

  function fillIn(user: User) {
    setEmail(user.email)
    setPassword(meta.demo_password)
    login.reset()
    submitButton.current?.focus()
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <Logo />
      <h1 className="mt-10 text-2xl font-semibold tracking-tight">Sign in</h1>

      <form onSubmit={submit} className="mt-6 space-y-4 rounded-xl border border-line bg-surface p-5 shadow-sm">
        <label className="block text-sm font-medium">
          Email
          <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
        </label>
        {login.error && <p className="text-sm text-critical-text">{login.error.message}</p>}
        <Button ref={submitButton} type="submit" variant="primary" disabled={login.isPending} className="w-full justify-center py-2">
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <h2 className="mt-10 text-sm font-medium">Demo accounts</h2>
      <p className="mt-1 text-sm text-ink-2">
        They all use the password <code className="rounded bg-canvas px-1">{meta.demo_password}</code>. Click one to fill in the form.
      </p>
      {TEAMS.map((team) => (
        <section key={team.title} className="mt-4">
          <h3 className="text-xs font-medium text-ink-3">{team.title}</h3>
          <ul className="mt-2 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
            {meta.users
              .filter((u) => team.roles.includes(u.role))
              .map((user) => (
                <li key={user.id}>
                  <button onClick={() => fillIn(user)} className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition hover:bg-brand-soft/50">
                    <Avatar user={user} />
                    <span className="min-w-0 text-sm">
                      <span className="font-medium">{user.name}</span>
                      <span className="text-ink-3"> · {user.role === 'affiliate' ? user.org : user.title}</span>
                      <span className="block truncate text-xs text-ink-3">{user.email}</span>
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        </section>
      ))}

      <p className="mt-8 text-xs text-ink-3">
        ClearPath Financial and everyone here are made up.{' '}
        <button onClick={() => reset.mutate()} disabled={reset.isPending} className="underline hover:text-ink-2 disabled:opacity-50">
          {reset.isSuccess ? 'Data reset' : 'Reset demo data'}
        </button>
      </p>
    </div>
  )
}
