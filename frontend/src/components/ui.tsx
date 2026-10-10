import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function Logo() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="flex size-7 items-center justify-center rounded-lg bg-brand text-sm text-white">✓</span>
      ClearView
    </span>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
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
  primary: 'bg-brand text-white shadow-sm hover:bg-brand-hover',
  secondary: 'border border-line-strong bg-surface hover:bg-canvas',
  danger: 'border border-critical/40 bg-surface text-critical-text hover:bg-critical-soft',
}

export function Button({ variant = 'secondary', className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof VARIANTS }) {
  return (
    <button
      className={clsx('inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition disabled:opacity-50', VARIANTS[variant], className)}
      {...props}
    />
  )
}

export function Card({ title, children, className }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('rounded-xl border border-line bg-surface shadow-sm', className)}>
      {title && <h2 className="border-b border-line px-5 py-3 text-sm font-semibold">{title}</h2>}
      <div className="p-5">{children}</div>
    </section>
  )
}

// shared look for text inputs, selects and textareas
export const inputClass = 'mt-1 block w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm font-normal shadow-sm focus:border-brand'
