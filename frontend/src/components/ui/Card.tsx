import { cn } from '@/utils/cn'

interface CardProps {
  children: React.ReactNode
  className?: string
  glow?: boolean
  onClick?: () => void
}

export function Card({ children, className, glow, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border-subtle bg-bg-card backdrop-blur-sm p-4 transition-all duration-200',
        glow && 'border-border-glow shadow-[0_0_15px_rgba(6,182,212,0.15)]',
        onClick && 'cursor-pointer hover:border-border-glow hover:bg-white/[0.05]',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  )
}
