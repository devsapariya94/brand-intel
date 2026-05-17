import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { MonitorCard } from '@/components/MonitorCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { monitorsApi } from '@/api/monitors'
import { brandsApi } from '@/api/brands'
import { formatDateTime, formatRelativeTime } from '@/utils/formatters'
import { Zap, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

export default function Monitors() {
  const queryClient = useQueryClient()
  const [selectedBrand, setSelectedBrand] = useState<string>('')
  const [triggeringMonitor, setTriggeringMonitor] = useState<string | null>(null)

  const { data: monitorStatus } = useQuery({
    queryKey: ['monitor-status'],
    queryFn: monitorsApi.getStatus,
    refetchInterval: 15000,
  })

  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list(true),
  })

  const { data: runs } = useQuery({
    queryKey: ['monitor-runs'],
    queryFn: () => monitorsApi.getRuns({ limit: 20 }),
    refetchInterval: 15000,
  })

  const triggerAllMutation = useMutation({
    mutationFn: (brandId?: string) => monitorsApi.triggerAll(brandId || undefined),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['monitor-status'] })
      queryClient.invalidateQueries({ queryKey: ['monitor-runs'] })
      toast.success(`Scan complete: ${data.total_hits_found} hits found, ${data.total_hits_stored} stored`)
    },
    onError: () => toast.error('Trigger failed'),
  })

  const triggerMonitorMutation = useMutation({
    mutationFn: ({ type, brandId }: { type: string; brandId: string }) =>
      monitorsApi.trigger(type, brandId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['monitor-status'] })
      queryClient.invalidateQueries({ queryKey: ['monitor-runs'] })
      toast.success(`Found ${data.hits_found} hits, ${data.hits_stored} stored`)
    },
    onError: () => toast.error('Trigger failed'),
  })

  const brandOptions = [
    { value: '', label: 'All Active Brands' },
    ...(brands ?? []).map((b) => ({ value: b.id, label: b.name })),
  ]

  return (
    <PageLayout title="Monitor Control Center">
      <div className="space-y-6">
        <Card>
          <div className="flex items-center gap-4">
            <Select
              label="Brand"
              options={brandOptions}
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="max-w-xs"
            />
            <div className="flex-1" />
            <Button
              onClick={() =>
                triggerAllMutation.mutate(selectedBrand || undefined)
              }
              loading={triggerAllMutation.isPending}
            >
              <Zap className="w-4 h-4 mr-1.5" />
              Trigger All Monitors
            </Button>
            <Button
              variant="secondary"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['monitor-status'] })}
            >
              <RefreshCw className="w-4 h-4 mr-1.5" />
              Refresh
            </Button>
          </div>
        </Card>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">Monitor Status</h2>
          {monitorStatus?.monitors ? (
            <div className="grid grid-cols-4 gap-4">
              {monitorStatus.monitors.map((m) => (
                <MonitorCard
                  key={m.type}
                  monitor={m}
                  onTrigger={
                    selectedBrand
                      ? () => {
                          setTriggeringMonitor(m.type)
                          triggerMonitorMutation.mutate(
                            { type: m.type, brandId: selectedBrand },
                            { onSettled: () => setTriggeringMonitor(null) }
                          )
                        }
                      : undefined
                  }
                  loading={triggeringMonitor === m.type}
                />
              ))}
            </div>
          ) : (
            <p className="text-text-muted">No monitors configured</p>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">Circuit Breaker Status</h2>
          {monitorStatus?.circuit_breaker && Object.keys(monitorStatus.circuit_breaker).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(monitorStatus.circuit_breaker).map(([type, state]) => {
                const stateColor =
                  state.state === 'closed' ? 'success' : state.state === 'open' ? 'danger' : 'warning'
                return (
                  <Card key={type} className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="font-medium text-text-primary">{type}</span>
                      <Badge variant={stateColor} dot>
                        {state.state.toUpperCase()}
                      </Badge>
                      <span className="text-sm text-text-muted">
                        Failures: {state.failure_count}
                      </span>
                      {state.last_failure && (
                        <span className="text-sm text-text-muted">
                          Last: {formatDateTime(state.last_failure)}
                        </span>
                      )}
                    </div>
                    {state.state === 'open' && (
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => {
                          monitorsApi.resetCircuitBreaker(type)
                          toast.success(`Circuit breaker reset for ${type}`)
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
            <p className="text-text-muted">No circuit breaker data</p>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">Recent Monitor Runs</h2>
          {runs && runs.length > 0 ? (
            <div className="rounded-xl border border-border-subtle bg-bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Monitor</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Brand</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Status</th>
                    <th className="text-right px-4 py-3 text-text-muted font-medium">Hits</th>
                    <th className="text-right px-4 py-3 text-text-muted font-medium">Duration</th>
                    <th className="text-right px-4 py-3 text-text-muted font-medium">Started</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-b border-border-subtle last:border-0">
                      <td className="px-4 py-2.5 text-text-primary">{run.monitor_type}</td>
                      <td className="px-4 py-2.5 text-text-secondary">{run.brand_name}</td>
                      <td className="px-4 py-2.5">
                        <Badge
                          variant={
                            run.status === 'success'
                              ? 'success'
                              : run.status === 'error'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {run.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-right text-text-secondary">{run.hits_found}</td>
                      <td className="px-4 py-2.5 text-right text-text-secondary">
                        {run.execution_time_seconds.toFixed(1)}s
                      </td>
                      <td className="px-4 py-2.5 text-right text-text-muted">
                        {formatRelativeTime(run.started_at ?? '')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-text-muted">No monitor runs recorded</p>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
