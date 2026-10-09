import type { Meta, Snippet } from './api'

/** The approved disclosure that resolves a rule, unless the draft already contains it. */
export function snippetToInsert(meta: Meta, ruleId: string | null, content: string): Snippet | undefined {
  const id = ruleId ? meta.snippet_for_rule[ruleId] : undefined
  const snippet = meta.snippets.find((s) => s.id === id)
  return snippet && !content.includes(snippet.body) ? snippet : undefined
}

/** Add a snippet to a draft: at the top if it has to precede the offer, otherwise as a footer. */
export function withSnippet(content: string, snippet: Snippet): string {
  return snippet.placement === 'top' ? `${snippet.body}\n\n${content.trimStart()}` : `${content.trimEnd()}\n\n${snippet.body}`
}
