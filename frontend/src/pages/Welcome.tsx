import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/badges'
import { api, type Role } from '../lib/api'
import { usePersona } from '../lib/persona'

const TEAMS: { title: string; roles: Role[] }[] = [
  { title: 'Marketing', roles: ['marketer'] },
  { title: 'Affiliate partners', roles: ['affiliate'] },
  { title: 'Compliance', roles: ['reviewer', 'lead'] },
]

export function Welcome() {
  const { meta, switchUser } = usePersona()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const reset = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: () => queryClient.invalidateQueries(),
  })

  function signIn(id: number) {
    switchUser(id)
    navigate('/')
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <div className="flex items-center gap-2 font-semibold">
        <ShieldCheck className="size-5 text-brand" aria-hidden />
        ClearView
      </div>
      <h1 className="mt-8 text-lg font-semibold">Sign in</h1>
      <p className="mt-1 text-sm text-ink-2">No passwords in the demo. Pick a user; you can switch from the menu in the top right.</p>

      {TEAMS.map((team) => (
        <section key={team.title} className="mt-6">
          <h2 className="text-xs font-medium text-ink-3">{team.title}</h2>
          <ul className="mt-2 divide-y divide-line rounded-lg border border-line bg-surface">
            {meta.users
              .filter((u) => team.roles.includes(u.role))
              .map((user) => (
                <li key={user.id}>
                  <button onClick={() => signIn(user.id)} className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-canvas">
                    <Avatar user={user} />
                    <span className="text-sm">
                      <span className="font-medium">{user.name}</span>
                      <span className="text-ink-3"> · {user.role === 'affiliate' ? user.org : user.title}</span>
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
