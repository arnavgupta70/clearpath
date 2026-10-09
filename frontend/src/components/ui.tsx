import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-2">{description}</p>}
      </div>
      {actions}
    </div>
  )
}

export function Loading() {
  return <p className="py-16 text-center text-sm text-ink-3">Loading…</p>
}

const VARIANTS = {
  primary: 'bg-brand text-white hover:bg-brand-hover',
  secondary: 'border border-line-strong bg-surface hover:bg-canvas',
  danger: 'border border-critical/40 bg-surface text-critical-text hover:bg-critical-soft',
}

export function Button({ variant = 'secondary', className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof VARIANTS }) {
  return (
    <button
      className={clsx('inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50', VARIANTS[variant], className)}
      {...props}
    />
  )
}

export function Card({ title, children, className }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('rounded-lg border border-line bg-surface', className)}>
      {title && <h2 className="border-b border-line px-4 py-3 text-sm font-semibold">{title}</h2>}
      <div className="p-4">{children}</div>
    </section>
  )
}
