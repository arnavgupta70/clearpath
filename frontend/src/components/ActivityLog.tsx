import type { AuditEvent } from '../lib/api'
import { formatDateTime } from '../lib/format'

export function ActivityLog({ events }: { events: AuditEvent[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {events.map((event) => (
        <li key={event.id}>
          <span className="font-medium">{event.actor?.name ?? 'ClearView'}</span> <span className="text-ink-2">{event.message}</span>
          <span className="ml-2 text-xs text-ink-3">{formatDateTime(event.created_at)}</span>
        </li>
      ))}
    </ul>
  )
}
