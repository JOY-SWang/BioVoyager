import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'ghost' | 'subtle'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  children: ReactNode
}

const VARIANT: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-white shadow-sm hover:bg-brand-700 hover:shadow disabled:bg-slate-300 disabled:cursor-not-allowed disabled:shadow-none',
  ghost:
    'text-slate-600 hover:bg-slate-100',
  subtle:
    'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50',
}

export function Button({ variant = 'primary', className = '', children, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={
        `inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${VARIANT[variant]} ${className}`
      }
    >
      {children}
    </button>
  )
}
