import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { formatRelativeTime } from '@/utils/formatters'
import type { MonitorStatus } from '@/types'

interface MonitorCardProps {
  monitor: MonitorStatus
  onTrigger?: () => void
  loading?: boolean
}

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  healthy: 'success',
  degraded: 'warning',
  unhealthy: 'danger',
  unknown: 'default',
}

export function MonitorCard({ monitor, onTrigger, loading }: MonitorCardProps) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                monitor.status === 'healthy'
                  ? 'bg-green-neon animate-pulse'
                  : monitor.status === 'degraded'
                  ? 'bg-amber-neon animate-pulse'
                  : 'bg-red-neon animate-pulse'
              }`}
            />
            <span className="font-medium text-text-primary">{monitor.name}</span>
          </div>
          <Badge variant={statusVariant[monitor.status]} dot>
            {monitor.status}
          </Badge>
        </div>

        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-text-muted text-xs">Success Rate</p>
            <p className="text-text-primary font-medium">
              {(monitor.success_rate * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-text-muted text-xs">Avg Time</p>
            <p className="text-text-primary font-medium">{monitor.avg_execution_time.toFixed(2)}s</p>
          </div>
          <div>
            <p className="text-text-muted text-xs">Last Run</p>
            <p className="text-text-primary font-medium">
              {formatRelativeTime(monitor.last_run ?? '')}
            </p>
          </div>
        </div>

        {onTrigger && (
          <Button variant="secondary" size="sm" onClick={onTrigger} loading={loading} className="w-full">
            Trigger Scan
          </Button>
        )}
      </Card>
    </motion.div>
  )
}
