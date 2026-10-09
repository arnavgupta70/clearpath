import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Submission } from './api'

export function useSubmission(id: number) {
  return useQuery({
    queryKey: ['submission', id],
    queryFn: () => api.submission(id),
    // Claude's review runs in the background after a submit, so keep checking until it's done
    refetchInterval: (query) => (query.state.data?.versions.some((v) => v.ai_status === 'pending') ? 3000 : false),
  })
}

// every action on a submission returns the updated submission, so just put it in the cache
export function useSaveSubmission(id: number) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  async function save(request: Promise<Submission>) {
    setError(null)
    try {
      queryClient.setQueryData(['submission', id], await request)
      queryClient.invalidateQueries({ queryKey: ['submissions'] })
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return { save, error }
}
