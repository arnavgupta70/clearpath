import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { PrecheckPanel } from '../components/PrecheckPanel'
import { Button, PageHeader } from '../components/ui'
import { api, type Snippet } from '../lib/api'
import { plural } from '../lib/format'
import { usePersona, useUser } from '../lib/persona'
import { withSnippet } from '../lib/snippets'
import { usePrecheck } from '../lib/usePrecheck'

// for trying the app out quickly
const EXAMPLES = {
  internal: {
    title: 'Holiday debt consolidation email',
    channel: 'email',
    content:
      'Subject: Start 2027 debt-free\n\nTired of juggling card payments? Combine them into one loan and pay as little as $199/month. ' +
      "Get instant approval, and checking your rate won't affect your credit score.\n\nOur lowest rates of the year end soon, so act now!\n\n[Check my rate]",
  },
  affiliate: {
    title: 'Top 5 personal loans this month',
    channel: 'landing_page',
    content:
      '#3: ClearPath, best for fair credit\n\nYou could be pre-approved in minutes with no credit check. Rates as low as 7.99% and ' +
      'funding the same day.\n\n[See my offer]',
  },
}

export function NewSubmission() {
  const user = useUser()
  const { meta } = usePersona()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [product, setProduct] = useState('personal_loan')
  const [channel, setChannel] = useState('email')
  const [content, setContent] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const precheck = usePrecheck(content, product, channel)

  function loadExample() {
    const example = EXAMPLES[user.role === 'affiliate' ? 'affiliate' : 'internal']
    setTitle(example.title)
    setProduct('personal_loan')
    setChannel(example.channel)
    setContent(example.content)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    const critical = precheck.data?.findings.filter((f) => f.severity === 'critical').length ?? 0
    if (critical && !window.confirm(`There are still ${plural(critical, 'critical issue')}. Compliance will send them back. Submit anyway?`)) return
    setSubmitting(true)
    try {
      const sub = await api.submit({ title, product, channel, content, notes: notes || undefined })
      navigate(`/submissions/${sub.id}`)
    } catch (err) {
      setError((err as Error).message)
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="New submission" actions={<Button onClick={loadExample}>Load an example</Button>} />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-medium">
            Name
            <input value={title} onChange={(e) => setTitle(e.target.value)} required className="mt-1 block w-full rounded border border-line-strong px-3 py-2 font-normal" />
          </label>
          <div className="flex gap-4">
            <label className="text-sm font-medium">
              Product
              <select value={product} onChange={(e) => setProduct(e.target.value)} className="mt-1 block rounded border border-line-strong px-2 py-2 font-normal">
                {Object.entries(meta.products).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium">
              Channel
              <select value={channel} onChange={(e) => setChannel(e.target.value)} className="mt-1 block rounded border border-line-strong px-2 py-2 font-normal">
                {Object.entries(meta.channels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-sm font-medium">
            Copy (include footers and fine print)
            <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12} required className="mt-1 block w-full rounded border border-line-strong px-3 py-2 font-normal" />
          </label>
          <label className="block text-sm font-medium">
            Anything the reviewer should know?
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="mt-1 block w-full rounded border border-line-strong px-3 py-2 font-normal" />
          </label>
          {error && <p className="text-sm text-critical-text">{error}</p>}
          <Button type="submit" variant="primary" disabled={submitting}>Submit for review</Button>
        </form>
        <PrecheckPanel content={content} result={precheck.data} onInsert={(snippet: Snippet) => setContent(withSnippet(content, snippet))} />
      </div>
    </>
  )
}
