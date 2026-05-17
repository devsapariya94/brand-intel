import { useQuery } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { MetricCard } from '@/components/MetricCard'
import { MonitorCard } from '@/components/MonitorCard'
import { HitCard } from '@/components/HitCard'
import { TimelineChart } from '@/components/charts/TimelineChart'
import { SourceBarChart } from '@/components/charts/SourceBarChart'
import { healthApi } from '@/api/health'
import { hitsApi } from '@/api/hits'
import { monitorsApi } from '@/api/monitors'
import { Building2, AlertTriangle, CheckCircle, Inbox } from 'lucide-react'

export default function Dashboard() {
  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: healthApi.getMetrics,
    refetchInterval: 30000,
  })

  const { data: hitsStats } = useQuery({
    queryKey: ['hits-stats'],
    queryFn: () => hitsApi.getStats({ days: 7 }),
    refetchInterval: 30000,
  })

  const { data: monitorStatus } = useQuery({
    queryKey: ['monitor-status'],
    queryFn: monitorsApi.getStatus,
    refetchInterval: 30000,
  })

  const { data: recentHits } = useQuery({
    queryKey: ['recent-hits'],
    queryFn: () => hitsApi.list({ limit: 5 }),
    refetchInterval: 30000,
  })

  return (
    <PageLayout title="Dashboard">
      <div className="space-y-6">
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Total Brands"
            value={metrics?.total_brands ?? 0}
            icon={<Building2 className="w-4 h-4" />}
            color="cyan"
            delay={0}
          />
          <MetricCard
            label="Total Alerts"
            value={metrics?.total_hits ?? 0}
            icon={<AlertTriangle className="w-4 h-4" />}
            color="amber"
            delay={0.1}
          />
          <MetricCard
            label="Success Rate"
            value={`${((metrics?.success_rate ?? 0) * 100).toFixed(1)}%`}
            icon={<CheckCircle className="w-4 h-4" />}
            color="green"
            delay={0.2}
          />
          <MetricCard
            label="DLQ Pending"
            value={metrics?.dlq_pending ?? 0}
            icon={<Inbox className="w-4 h-4" />}
            color={(metrics?.dlq_pending ?? 0) > 0 ? 'red' : 'green'}
            delay={0.3}
          />
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Monitor Status</h2>
            {monitorStatus?.monitors ? (
              <div className="grid grid-cols-2 gap-4">
                {monitorStatus.monitors.map((m) => (
                  <MonitorCard key={m.type} monitor={m} />
                ))}
              </div>
            ) : (
              <p className="text-text-muted text-sm">No monitors configured</p>
            )}
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">7-Day Hit Trend</h2>
            {hitsStats?.timeline && hitsStats.timeline.length > 0 ? (
              <TimelineChart data={hitsStats.timeline} />
            ) : (
              <p className="text-text-muted text-sm">No hit data yet. Run monitors to see trends.</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Hits by Source</h2>
            {hitsStats?.by_source && Object.keys(hitsStats.by_source).length > 0 ? (
              <SourceBarChart data={hitsStats.by_source} />
            ) : (
              <p className="text-text-muted text-sm">No source data available</p>
            )}
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Top Keywords</h2>
            {hitsStats?.top_keywords && hitsStats.top_keywords.length > 0 ? (
              <div className="rounded-xl border border-border-subtle bg-bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="text-left px-4 py-3 text-text-muted font-medium">Keyword</th>
                      <th className="text-right px-4 py-3 text-text-muted font-medium">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hitsStats.top_keywords.map((kw) => (
                      <tr key={kw.keyword} className="border-b border-border-subtle last:border-0">
                        <td className="px-4 py-2.5 text-text-primary">{kw.keyword}</td>
                        <td className="px-4 py-2.5 text-right text-text-secondary">{kw.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-text-muted text-sm">No keyword data available</p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">Recent Hits</h2>
          {recentHits?.hits && recentHits.hits.length > 0 ? (
            <div className="space-y-3">
              {recentHits.hits.map((hit) => (
                <HitCard key={hit.id} hit={hit} />
              ))}
            </div>
          ) : (
            <p className="text-text-muted text-sm">No hits recorded yet</p>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
