import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'

interface MetricCardProps {
  label: string
  value: string | number
  icon: React.ReactNode
  color?: 'cyan' | 'green' | 'red' | 'amber' | 'purple'
  delay?: number
}

const colorMap = {
  cyan: { bg: 'bg-cyan-neon/10', text: 'text-cyan-neon', border: 'border-cyan-neon/20', glow: 'shadow-[0_0_20px_rgba(6,182,212,0.15)]' },
  green: { bg: 'bg-green-neon/10', text: 'text-green-neon', border: 'border-green-neon/20', glow: 'shadow-[0_0_20px_rgba(34,197,94,0.15)]' },
  red: { bg: 'bg-red-neon/10', text: 'text-red-neon', border: 'border-red-neon/20', glow: 'shadow-[0_0_20px_rgba(239,68,68,0.15)]' },
  amber: { bg: 'bg-amber-neon/10', text: 'text-amber-neon', border: 'border-amber-neon/20', glow: 'shadow-[0_0_20px_rgba(245,158,11,0.15)]' },
  purple: { bg: 'bg-purple-neon/10', text: 'text-purple-neon', border: 'border-purple-neon/20', glow: 'shadow-[0_0_20px_rgba(168,85,247,0.15)]' },
}

export function MetricCard({ label, value, icon, color = 'cyan', delay = 0 }: MetricCardProps) {
  const colors = colorMap[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <div
        className={cn(
          'rounded-xl border bg-bg-card backdrop-blur-sm p-5 transition-all duration-200 hover:border-border-glow',
          colors.border,
          colors.glow
        )}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-text-secondary">{label}</span>
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', colors.bg)}>
            <span className={colors.text}>{icon}</span>
          </div>
        </div>
        <div className={cn('text-3xl font-bold', colors.text)}>{value}</div>
      </div>
    </motion.div>
  )
}
