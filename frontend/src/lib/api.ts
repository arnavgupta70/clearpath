export type Role = 'marketer' | 'affiliate' | 'reviewer' | 'lead'
export type Severity = 'critical' | 'major' | 'minor'
export type RiskTier = 'low' | 'medium' | 'high'
export type SubmissionStatus = 'in_review' | 'changes_requested' | 'approved' | 'approved_with_conditions' | 'rejected'
export type FindingStatus = 'open' | 'accepted' | 'dismissed' | 'resolved'
export type Decision = 'approve' | 'approve_with_conditions' | 'request_changes' | 'reject'

export interface User {
  id: number
  name: string
  email: string
  title: string
  role: Role
  org: string
  color: string
}

export interface Snippet {
  id: string
  title: string
  body: string
  products: string[]
  placement?: 'top'
}

export interface Meta {
  demo_password: string
  products: Record<string, string>
  channels: Record<string, string>
  users: User[]
  snippets: Snippet[]
  snippet_for_rule: Record<string, string>
}

// a flagged problem in some copy, before anyone has looked at it
export interface Issue {
  source: 'rule' | 'ai' | 'reviewer'
  rule_id: string | null
  title: string
  severity: Severity
  citation: string | null
  explanation: string
  suggestion: string | null
  quote: string | null
  start: number | null
  end: number | null
}

export interface Finding extends Issue {
  id: number
  status: FindingStatus
  carried_from: number | null
}

export interface RiskFactor {
  label: string
  points: number
}

export interface Precheck {
  findings: Issue[]
  risk_tier: RiskTier
  estimated_decision_by: string
}

export interface SubmissionSummary {
  id: number
  ref: string
  title: string
  product: string
  channel: string
  source: 'internal' | 'affiliate'
  partner: string | null
  status: SubmissionStatus
  risk_score: number
  risk_tier: RiskTier
  current_version: number
  created_at: string
  updated_at: string
  due_at: string
  decided_at: string | null
  approval_code: string | null
  submitter: User
  assignee: User | null
  open_issues: number
}

export interface Version {
  id: number
  number: number
  content: string
  notes: string | null
  created_at: string
  ai_status: 'pending' | 'done' | 'unavailable' | 'error'
  ai_summary: string | null
  findings: Finding[]
}

export interface AuditEvent {
  id: number
  message: string
  created_at: string
  actor: User | null
}

export interface Submission extends SubmissionSummary {
  risk_factors: RiskFactor[]
  decision_note: string | null
  conditions: string[]
  versions: Version[]
  events: AuditEvent[]
}


// [last 30 days, the 30 before that]
type Comparison = [number | null, number | null]

export interface Metrics {
  kpis: { median_days: Comparison; first_pass_rate: Comparison }
  weeks: { week: string; median_days: number | null; first_pass_rate: number | null }[]
  partners: { partner: string; submissions: number; first_pass_rate: number | null; top_issue: string | null }[]
  precision: { rule_id: string; hits: number; confirmed: number; precision: number }[]
}

export interface Draft {
  content: string
  product: string
  channel: string
}

export interface Session {
  token: string
  userId: number
}

const SESSION_KEY = 'clearview.session'
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export function loadSession(): Session | null {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) ?? 'null')
  } catch {
    return null
  }
}

export function saveSession(session: Session | null) {
  if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  else localStorage.removeItem(SESSION_KEY)
}

async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const session = loadSession()
  if (session) headers.Authorization = `Bearer ${session.token}`

  const response = await fetch(BASE_URL + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  if (response.status === 401 && session) {
    // token expired or the server's secret changed: back to the login page
    saveSession(null)
    window.location.reload()
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : `Request failed (${response.status})`)
  }
  return response.json()
}

export const api = {
  meta: () => request<Meta>('/api/meta'),
  login: (email: string, password: string) => request<{ token: string; user: User }>('/api/login', 'POST', { email, password }),
  precheck: (draft: Draft) => request<Precheck>('/api/precheck', 'POST', draft),

  submissions: (mine = false) => request<SubmissionSummary[]>(`/api/submissions${mine ? '?mine=true' : ''}`),
  submission: (id: number) => request<Submission>(`/api/submissions/${id}`),
  submit: (body: Draft & { title: string; notes?: string }) =>
    request<Submission>('/api/submissions', 'POST', body),
  resubmit: (id: number, content: string, notes?: string) => request<Submission>(`/api/submissions/${id}/versions`, 'POST', { content, notes }),
  decide: (id: number, decision: Decision, note?: string) => request<Submission>(`/api/submissions/${id}/decision`, 'POST', { decision, note }),
  triage: (findingId: number, status: 'open' | 'accepted' | 'dismissed') => request<Submission>(`/api/findings/${findingId}`, 'PATCH', { status }),

  metrics: () => request<Metrics>('/api/metrics'),
  resetDemo: () => request<{ ok: boolean }>('/api/demo/reset', 'POST'),
}
