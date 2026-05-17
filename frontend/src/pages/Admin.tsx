import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { healthApi } from '@/api/health'
import { adminApi } from '@/api/admin'
import { monitorsApi } from '@/api/monitors'
import { formatDateTime, formatRelativeTime } from '@/utils/formatters'
import { toast } from 'sonner'

export default function Admin() {
  const [activeTab, setActiveTab] = useState<'health' | 'dlq' | 'circuit' | 'maintenance'>('health')
  const queryClient = useQueryClient()

  const { data: health } = useQuery({
    queryKey: ['health-detailed'],
    queryFn: healthApi.getDetailed,
    refetchInterval: 15000,
  })

  const { data: dlqItems } = useQuery({
    queryKey: ['dlq'],
    queryFn: () => adminApi.getDLQ(),
    refetchInterval: 15000,
  })

  const { data: monitorStatus } = useQuery({
    queryKey: ['monitor-status'],
    queryFn: monitorsApi.getStatus,
    refetchInterval: 15000,
  })

  const retryDLQMutation = useMutation({
    mutationFn: adminApi.retryDLQ,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
      toast.success('Retry queued')
    },
    onError: () => toast.error('Retry failed'),
  })

  const deleteDLQMutation = useMutation({
    mutationFn: adminApi.deleteDLQ,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
      toast.success('Item deleted')
    },
    onError: () => toast.error('Delete failed'),
  })

  const cleanupMutation = useMutation({
    mutationFn: adminApi.triggerCleanup,
    onSuccess: (data) => {
      toast.success(`Cleanup complete. Deleted ${data.monitor_runs_deleted} old runs.`)
    },
    onError: () => toast.error('Cleanup failed'),
  })

  const tabs = [
    { id: 'health' as const, label: 'Health' },
    { id: 'dlq' as const, label: 'Dead Letter Queue' },
    { id: 'circuit' as const, label: 'Circuit Breaker' },
    { id: 'maintenance' as const, label: 'Maintenance' },
  ]

  return (
    <PageLayout title="Administration">
      <div className="space-y-6">
        <div className="flex gap-2 border-b border-border-subtle pb-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-cyan-neon/10 text-cyan-neon'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'health' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">System Health</h2>
            {health && (
              <>
                <Card>
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-3 h-3 rounded-full ${
                        health.status === 'healthy'
                          ? 'bg-green-neon animate-pulse'
                          : health.status === 'degraded'
                          ? 'bg-amber-neon animate-pulse'
                          : 'bg-red-neon animate-pulse'
                      }`}
                    />
                    <span className="text-lg font-semibold text-text-primary">
                      {health.status.toUpperCase()}
                    </span>
                  </div>
                </Card>

                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <h3 className="text-sm font-medium text-text-secondary mb-3">Database</h3>
                    <Badge
                      variant={health.database.status === 'healthy' ? 'success' : 'danger'}
                      dot
                    >
                      {health.database.status.toUpperCase()}
                    </Badge>
                  </Card>

                  <Card>
                    <h3 className="text-sm font-medium text-text-secondary mb-3">DLQ</h3>
                    <div className="flex gap-4 text-sm">
                      <span className="text-text-secondary">
                        <span className="text-amber-neon font-medium">{health.dlq.pending}</span> pending
                      </span>
                      <span className="text-text-secondary">
                        <span className="text-red-neon font-medium">{health.dlq.failed}</span> failed
                      </span>
                    </div>
                  </Card>
                </div>

                <Card>
                  <h3 className="text-sm font-medium text-text-secondary mb-3">Monitors</h3>
                  <div className="space-y-2">
                    {Object.entries(health.monitors).map(([name, m]) => (
                      <div key={name} className="flex items-center justify-between">
                        <span className="text-text-primary">{name}</span>
                        <Badge
                          variant={
                            m.status === 'healthy'
                              ? 'success'
                              : m.status === 'degraded'
                              ? 'warning'
                              : 'danger'
                          }
                          dot
                        >
                          {m.status.toUpperCase()}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Card>

                {health.uptime_seconds > 0 && (
                  <Card>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-text-muted">Uptime</p>
                        <p className="text-text-primary font-medium">
                          {Math.floor(health.uptime_seconds / 3600)}h{' '}
                          {Math.floor((health.uptime_seconds % 3600) / 60)}m
                        </p>
                      </div>
                      {health.last_scan && (
                        <div>
                          <p className="text-text-muted">Last Scan</p>
                          <p className="text-text-primary font-medium">
                            {formatRelativeTime(health.last_scan)}
                          </p>
                        </div>
                      )}
                    </div>
                  </Card>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'dlq' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Dead Letter Queue</h2>
            {dlqItems && dlqItems.length > 0 ? (
              <>
                <p className="text-sm text-text-muted">{dlqItems.length} items in DLQ</p>
                <div className="space-y-3">
                  {dlqItems.map((item) => (
                    <Card key={item.id} className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-text-primary">{item.brand_name}</p>
                          <p className="text-sm text-text-muted">Source: {item.source}</p>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-text-muted">
                            Retries: {item.retry_count}/{item.max_retries}
                          </span>
                          <Badge
                            variant={item.status === 'pending' ? 'warning' : 'danger'}
                          >
                            {item.status}
                          </Badge>
                          <span className="text-text-muted">
                            {formatDateTime(item.created_at).slice(0, 19)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => retryDLQMutation.mutate(item.id)}
                            loading={retryDLQMutation.isPending}
                          >
                            Retry
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => deleteDLQMutation.mutate(item.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                      {item.error && (
                        <p className="text-sm text-red-neon bg-red-neon/5 rounded-lg p-3">{item.error}</p>
                      )}
                    </Card>
                  ))}
                </div>
              </>
            ) : (
              <Card>
                <p className="text-green-neon text-center py-4">DLQ is empty</p>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'circuit' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Circuit Breaker Management</h2>
            {monitorStatus?.circuit_breaker && Object.keys(monitorStatus.circuit_breaker).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(monitorStatus.circuit_breaker).map(([type, state]) => {
                  const stateColor =
                    state.state === 'closed' ? 'success' : state.state === 'open' ? 'danger' : 'warning'
                  return (
                    <Card key={type} className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <span className="font-medium text-text-primary">{type}</span>
                        <Badge variant={stateColor} dot>{state.state.toUpperCase()}</Badge>
                        <span className="text-sm text-text-muted">
                          Failures: {state.failure_count}
                        </span>
                        {state.last_failure && (
                          <span className="text-sm text-text-muted">
                            Last failure: {formatDateTime(state.last_failure).slice(0, 19)}
                          </span>
                        )}
                      </div>
                      {state.state === 'open' && (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => {
                            monitorsApi.resetCircuitBreaker(type)
                            toast.success(`Reset ${type}`)
                            queryClient.invalidateQueries({ queryKey: ['monitor-status'] })
                          }}
                        >
                          Reset
                        </Button>
                      )}
                    </Card>
                  )
                })}
              </div>
            ) : (
              <p className="text-text-muted">No circuit breaker data available</p>
            )}
          </div>
        )}

        {activeTab === 'maintenance' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Maintenance Tasks</h2>
            <div className="grid grid-cols-2 gap-6">
              <Card>
                <h3 className="font-medium text-text-primary mb-1">Cleanup Old Data</h3>
                <p className="text-sm text-text-muted mb-4">
                  Remove monitor runs older than 30 days
                </p>
                <Button
                  onClick={() => cleanupMutation.mutate()}
                  loading={cleanupMutation.isPending}
                >
                  Run Cleanup
                </Button>
              </Card>

              <Card>
                <h3 className="font-medium text-text-primary mb-1">System Information</h3>
                <p className="text-sm text-text-muted mb-4">API and system details</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-muted">API Name</span>
                    <span className="text-text-primary">Brand Intel API</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Version</span>
                    <span className="text-text-primary">1.0.0</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Status</span>
                    <span className="text-green-neon">Running</span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  )
}
