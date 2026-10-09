import type { Severity, SubmissionStatus } from './api'

export const SEVERITY_ORDER: Severity[] = ['critical', 'major', 'minor']

export const SEVERITY_LABEL: Record<Severity, string> = { critical: 'Critical', major: 'Major', minor: 'Minor' }

export const STATUS_LABEL: Record<SubmissionStatus, string> = {
  in_review: 'In review',
  changes_requested: 'Changes requested',
  approved: 'Approved',
  approved_with_conditions: 'Approved with conditions',
  rejected: 'Rejected',
}

const HOUR = 3_600_000

function duration(ms: number) {
  const hours = Math.abs(ms) / HOUR
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`
  if (hours < 24) return `${Math.round(hours)}h`
  return `${Math.round(hours / 24)}d`
}

export function timeAgo(iso: string) {
  return `${duration(Date.now() - Date.parse(iso))} ago`
}

export function isOverdue(iso: string) {
  return Date.parse(iso) < Date.now()
}

export function dueText(iso: string) {
  const ms = Date.parse(iso) - Date.now()
  return ms < 0 ? `Overdue ${duration(ms)}` : `Due in ${duration(ms)}`
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function percent(value: number | null) {
  return value === null ? '–' : `${Math.round(value * 100)}%`
}

export function plural(count: number, noun: string) {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}
