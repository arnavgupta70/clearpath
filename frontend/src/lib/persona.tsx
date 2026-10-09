import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useState, type ReactNode } from 'react'
import { api, USER_KEY, type Meta, type User } from './api'

// There's no real login. You pick a demo user, it's saved in localStorage, and api.ts sends it as X-User-Id.

interface PersonaContextValue {
  user: User | null
  meta: Meta
  switchUser: (id: number | null) => void
}

const PersonaContext = createContext<PersonaContextValue | null>(null)

export function PersonaProvider({ meta, children }: { meta: Meta; children: ReactNode }) {
  const queryClient = useQueryClient()
  const [userId, setUserId] = useState(() => Number(localStorage.getItem(USER_KEY)) || null)

  function switchUser(id: number | null) {
    setUserId(id)
    if (id === null) localStorage.removeItem(USER_KEY)
    else localStorage.setItem(USER_KEY, String(id))
    // cached data belongs to the previous user
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'meta' })
  }

  const user = meta.users.find((u) => u.id === userId) ?? null
  return <PersonaContext value={{ user, meta, switchUser }}>{children}</PersonaContext>
}

export function usePersona() {
  const context = useContext(PersonaContext)
  if (!context) throw new Error('usePersona needs a PersonaProvider')
  return context
}

// for pages you can only reach once signed in
export function useUser(): User {
  const { user } = usePersona()
  if (!user) throw new Error('not signed in')
  return user
}

export function useMeta() {
  return useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
}

export function isReviewer(user: User) {
  return user.role === 'reviewer' || user.role === 'lead'
}
