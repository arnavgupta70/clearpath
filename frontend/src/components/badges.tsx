import clsx from 'clsx'
import { CircleAlert, OctagonAlert, TriangleAlert } from 'lucide-react'
import type { RiskTier, Severity, SubmissionStatus, User } from '../lib/api'
import { SEVERITY_LABEL, STATUS_LABEL } from '../lib/format'

const SEVERITY_ICON = { critical: OctagonAlert, major: TriangleAlert, minor: CircleAlert }
const SEVERITY_COLOR = { critical: 'text-critical-text', major: 'text-major-text', minor: 'text-minor-text' }

export function SeverityIcon({ severity }: { severity: Severity }) {
  const Icon = SEVERITY_ICON[severity]
  return <Icon className={clsx('mt-0.5 size-4 shrink-0', SEVERITY_COLOR[severity])} />
}

export function SeverityLabel({ severity }: { severity: Severity }) {
  return <span className={clsx('text-xs font-semibold', SEVERITY_COLOR[severity])}>{SEVERITY_LABEL[severity]}</span>
}

const STATUS_COLOR: Record<SubmissionStatus, string> = {
  in_review: 'bg-brand-soft text-brand',
  changes_requested: 'bg-major-soft text-major-text',
  approved: 'bg-good-soft text-good-text',
  approved_with_conditions: 'bg-good-soft text-good-text',
  rejected: 'bg-critical-soft text-critical-text',
}

export function StatusBadge({ status }: { status: SubmissionStatus }) {
  return <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap', STATUS_COLOR[status])}>{STATUS_LABEL[status]}</span>
}

const RISK_COLOR: Record<RiskTier, string> = {
  high: 'border-critical/40 text-critical-text',
  medium: 'border-major/50 text-major-text',
  low: 'border-line-strong text-ink-2',
}

export function RiskBadge({ tier }: { tier: RiskTier }) {
  return <span className={clsx('rounded border px-1.5 py-px text-xs font-medium whitespace-nowrap', RISK_COLOR[tier])}>{tier} risk</span>
}

export function Avatar({ user }: { user: User }) {
  const initials = user.name.split(' ').map((part) => part[0]).join('')
  return (
    <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold text-white" style={{ backgroundColor: user.color }}>
      {initials}
    </span>
  )
}
