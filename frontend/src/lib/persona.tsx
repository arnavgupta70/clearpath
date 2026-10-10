import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useState, type ReactNode } from 'react'
import { api, loadSession, saveSession, type Meta, type Session, type User } from './api'

// The login token is kept in localStorage and api.ts sends it with every request.

interface PersonaContextValue {
  user: User | null
  meta: Meta
  signIn: (session: Session) => void
  signOut: () => void
}

const PersonaContext = createContext<PersonaContextValue | null>(null)

export function PersonaProvider({ meta, children }: { meta: Meta; children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState(loadSession)

  function changeSession(next: Session | null) {
    saveSession(next)
    setSession(next)
    // cached data belongs to the previous user
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'meta' })
  }

  const user = meta.users.find((u) => u.id === session?.userId) ?? null
  return (
    <PersonaContext value={{ user, meta, signIn: changeSession, signOut: () => changeSession(null) }}>
      {children}
    </PersonaContext>
  )
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
