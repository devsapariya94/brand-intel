import { cn } from '@/utils/cn'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'
  className?: string
  dot?: boolean
}

const variants = {
  default: 'bg-white/10 text-text-secondary',
  success: 'bg-green-neon/15 text-green-neon',
  warning: 'bg-amber-neon/15 text-amber-neon',
  danger: 'bg-red-neon/15 text-red-neon',
  info: 'bg-cyan-neon/15 text-cyan-neon',
  purple: 'bg-purple-neon/15 text-purple-neon',
}

export function Badge({ children, variant = 'default', className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'success' && 'bg-green-neon',
            variant === 'warning' && 'bg-amber-neon',
            variant === 'danger' && 'bg-red-neon',
            variant === 'info' && 'bg-cyan-neon',
            variant === 'purple' && 'bg-purple-neon',
            variant === 'default' && 'bg-text-muted'
          )}
        />
      )}
      {children}
    </span>
  )
}
