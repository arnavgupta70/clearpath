import { diffSentences } from 'diff'

export function DiffText({ before, after }: { before: string; after: string }) {
  // Sentence-level reads better than word-level for rewritten copy. The trailing newline stops an
  // edit to the last paragraph from marking the line before it as changed.
  const parts = diffSentences(before + '\n', after + '\n')
  return (
    <div className="text-[15px] leading-7 break-words whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (part.added) return <ins key={i} className="diff">{part.value}</ins>
        if (part.removed) return <del key={i} className="diff">{part.value}</del>
        return part.value
      })}
    </div>
  )
}
