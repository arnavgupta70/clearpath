import { useQuery } from '@tanstack/react-query'
import { TrendChart } from '../components/TrendChart'
import { Card, Loading, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { formatDate, percent } from '../lib/format'

export function Insights() {
  const { data, error } = useQuery({ queryKey: ['metrics'], queryFn: api.metrics })
  if (error) return <p className="text-critical-text">{error.message}</p>
  if (!data) return <Loading />

  const { kpis, weeks, partners, precision } = data
  const days = (v: number | null) => (v === null ? '–' : `${v.toFixed(1)} days`)
  const noisyRules = precision.filter((r) => r.rule_id !== 'AI' && r.hits >= 5 && r.precision < 0.6)
  const claude = precision.find((r) => r.rule_id === 'AI')

  return (
    <>
      <PageHeader title="Insights" description="Last 30 days vs. the 30 before. (Demo data: the pre-check went live five weeks ago.)" />

      <div className="grid gap-4 sm:grid-cols-2">
        <Kpi label="Median time to decision" now={kpis.median_days[0]} before={kpis.median_days[1]} format={days} lowerIsBetter />
        <Kpi label="Approved first time" now={kpis.first_pass_rate[0]} before={kpis.first_pass_rate[1]} format={percent} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Median days to decision, by week">
          <TrendChart data={weeks.map((w) => ({ label: formatDate(w.week), value: w.median_days }))} format={(v) => `${v}d`} />
        </Card>
        <Card title="Approved first time, by week">
          <TrendChart data={weeks.map((w) => ({ label: formatDate(w.week), value: w.first_pass_rate }))} format={percent} domain={[0, 1]} />
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="By partner">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-ink-3">
              <tr>
                <th className="pr-4 pb-2 font-medium">Source</th>
                <th className="pr-4 pb-2 font-medium">Approved first time</th>
                <th className="pr-4 pb-2 font-medium">Most common issue</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => (
                <tr key={p.partner} className="border-t border-line">
                  <td className="py-2.5 pr-4">{p.partner}</td>
                  <td className="py-2.5 pr-4">{percent(p.first_pass_rate)}</td>
                  <td className="py-2.5 text-ink-2">{p.top_issue ?? '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Rules reviewers keep dismissing">
          {noisyRules.length === 0 && <p className="text-sm text-ink-2">None right now.</p>}
          <ul className="space-y-1 text-sm">
            {noisyRules.map((r) => (
              <li key={r.rule_id}>
                <span className="font-mono text-xs">{r.rule_id}</span>: agreed with {percent(r.precision)} of {r.hits} hits
              </li>
            ))}
          </ul>
          {claude && <p className="mt-3 text-sm text-ink-2">Claude: reviewers agreed with {percent(claude.precision)} of {claude.hits} findings.</p>}
        </Card>
      </div>
    </>
  )
}

function Kpi(props: { label: string; now: number | null; before: number | null; format: (v: number | null) => string; lowerIsBetter?: boolean }) {
  const { label, now, before, format, lowerIsBetter } = props
  const improved = now !== null && before !== null && (lowerIsBetter ? now < before : now > before)
  return (
    <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <p className="text-sm text-ink-2">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight">{format(now)}</p>
      {before !== null && (
        <p className={improved ? 'text-sm text-good-text' : 'text-sm text-critical-text'}>
          {now !== null && now < before ? '↓' : '↑'} from {format(before)}
        </p>
      )}
    </div>
  )
}
