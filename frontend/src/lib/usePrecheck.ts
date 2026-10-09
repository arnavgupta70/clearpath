import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, type Draft } from './api'

// re-run the rules on the draft, waiting until the person stops typing for a moment
export function usePrecheck(content: string, product: string, channel: string) {
  const [draft, setDraft] = useState<Draft>({ content, product, channel })

  useEffect(() => {
    const timer = setTimeout(() => setDraft({ content, product, channel }), 400)
    return () => clearTimeout(timer)
  }, [content, product, channel])

  return useQuery({
    queryKey: ['precheck', draft],
    queryFn: () => api.precheck(draft),
    enabled: draft.content.trim() !== '',
    placeholderData: keepPreviousData,
  })
}
