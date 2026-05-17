import { cn } from '@/utils/cn'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && <label className="block text-sm font-medium text-text-secondary">{label}</label>}
      <input
        className={cn(
          'w-full px-3 py-2 rounded-lg bg-white/5 border border-border-subtle text-text-primary placeholder-text-muted',
          'focus:outline-none focus:border-cyan-neon/50 focus:ring-1 focus:ring-cyan-neon/20 transition-all',
          error && 'border-red-neon/50 focus:border-red-neon/50 focus:ring-red-neon/20',
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-neon">{error}</p>}
    </div>
  )
}
