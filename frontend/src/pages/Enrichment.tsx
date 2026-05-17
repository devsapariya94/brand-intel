import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { DonutChart } from '@/components/charts/DonutChart'
import { enrichmentApi } from '@/api/enrichment'
import { formatDateTime } from '@/utils/formatters'
import { toast } from 'sonner'

export default function Enrichment() {
  const queryClient = useQueryClient()
  const [hitId, setHitId] = useState('')
  const [configForm, setConfigForm] = useState<{
    llm_model: string
    llm_temperature: number
    alert_threshold: number
    suppress_threshold: number
    escalate_threshold: number
  } | null>(null)

  const { data: config } = useQuery({
    queryKey: ['enrichment-config'],
    queryFn: enrichmentApi.getConfig,
  })

  const { data: stats } = useQuery({
    queryKey: ['enrichment-stats'],
    queryFn: enrichmentApi.getStats,
  })

  const { data: llmStats } = useQuery({
    queryKey: ['llm-stats'],
    queryFn: enrichmentApi.getLlmCallStats,
  })

  const { data: llmCalls } = useQuery({
    queryKey: ['llm-calls'],
    queryFn: () => enrichmentApi.getLlmCalls(25),
  })

  const updateConfigMutation = useMutation({
    mutationFn: enrichmentApi.updateConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrichment-config'] })
      toast.success('Configuration updated')
    },
    onError: () => toast.error('Failed to update configuration'),
  })

  const processHitMutation = useMutation({
    mutationFn: enrichmentApi.processHit,
    onSuccess: (data) => {
      toast.success(`Decision: ${data.decision}`)
      queryClient.invalidateQueries({ queryKey: ['hits'] })
    },
    onError: () => toast.error('Processing failed'),
  })

  return (
    <PageLayout title="AI Enrichment">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Configuration</h2>
            {config && (
              <>
                <Card className="space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-text-muted">Provider</p>
                      <p className="text-text-primary font-medium">
                        {config.use_anthropic ? 'Anthropic' : 'OpenAI-compatible'}
                      </p>
                    </div>
                    <div>
                      <p className="text-text-muted">Model</p>
                      <p className="text-text-primary font-medium">{config.llm_model}</p>
                    </div>
                    <div>
                      <p className="text-text-muted">Temperature</p>
                      <p className="text-text-primary font-medium">{config.llm_temperature}</p>
                    </div>
                  </div>

                  <div className="border-t border-border-subtle pt-3 space-y-2">
                    <p className="text-sm font-medium text-text-secondary">Thresholds</p>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-xs text-text-muted mb-1">
                          <span>Alert</span>
                          <span>{config.alert_threshold.toFixed(2)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5">
                          <div
                            className="h-full rounded-full bg-red-neon"
                            style={{ width: `${config.alert_threshold * 100}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs text-text-muted mb-1">
                          <span>Suppress</span>
                          <span>{config.suppress_threshold.toFixed(2)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5">
                          <div
                            className="h-full rounded-full bg-green-neon"
                            style={{ width: `${config.suppress_threshold * 100}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs text-text-muted mb-1">
                          <span>Escalate</span>
                          <span>{config.escalate_threshold.toFixed(2)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5">
                          <div
                            className="h-full rounded-full bg-amber-neon"
                            style={{ width: `${config.escalate_threshold * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>

                <details className="rounded-xl border border-border-subtle bg-bg-card">
                  <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                    Update Configuration
                  </summary>
                  <div className="p-4 space-y-4 border-t border-border-subtle">
                    {!configForm && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setConfigForm({
                            llm_model: config.llm_model,
                            llm_temperature: config.llm_temperature,
                            alert_threshold: config.alert_threshold,
                            suppress_threshold: config.suppress_threshold,
                            escalate_threshold: config.escalate_threshold,
                          })
                        }
                      >
                        Edit Config
                      </Button>
                    )}
                    {configForm && (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <Input
                            label="LLM Model"
                            value={configForm.llm_model}
                            onChange={(e) => setConfigForm({ ...configForm, llm_model: e.target.value })}
                          />
                          <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                              Temperature: {configForm.llm_temperature}
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="2"
                              step="0.1"
                              value={configForm.llm_temperature}
                              onChange={(e) =>
                                setConfigForm({ ...configForm, llm_temperature: Number(e.target.value) })
                              }
                              className="w-full"
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                              Alert Threshold: {configForm.alert_threshold}
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={configForm.alert_threshold}
                              onChange={(e) =>
                                setConfigForm({ ...configForm, alert_threshold: Number(e.target.value) })
                              }
                              className="w-full"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                              Suppress Threshold: {configForm.suppress_threshold}
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={configForm.suppress_threshold}
                              onChange={(e) =>
                                setConfigForm({ ...configForm, suppress_threshold: Number(e.target.value) })
                              }
                              className="w-full"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                              Escalate Threshold: {configForm.escalate_threshold}
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={configForm.escalate_threshold}
                              onChange={(e) =>
                                setConfigForm({ ...configForm, escalate_threshold: Number(e.target.value) })
                              }
                              className="w-full"
                            />
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() =>
                              updateConfigMutation.mutate(configForm)
                            }
                            loading={updateConfigMutation.isPending}
                          >
                            Save
                          </Button>
                          <Button variant="ghost" onClick={() => setConfigForm(null)}>
                            Cancel
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                </details>
              </>
            )}
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-text-primary">Statistics</h2>
            {stats && (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <p className="text-sm text-text-muted">Total Processed</p>
                    <p className="text-2xl font-bold text-text-primary">{stats.total_processed}</p>
                  </Card>
                  <Card>
                    <p className="text-sm text-text-muted">Avg Processing Time</p>
                    <p className="text-2xl font-bold text-text-primary">
                          <span>{(stats.avg_processing_time ?? 0).toFixed(2)}s</span>
                    </p>
                  </Card>
                  <Card>
                    <p className="text-sm text-text-muted">Est. Cost</p>
                     <p className="text-2xl font-bold text-text-primary">${(stats.estimated_cost ?? 0).toFixed(4)}</p>
                  </Card>
                </div>
                <Card>
                  <DonutChart
                    data={[
                      { name: 'Alerts', value: stats.alerts_sent },
                      { name: 'Suppressed', value: stats.suppressed },
                      { name: 'Escalated', value: stats.escalated },
                    ]}
                    title="Enrichment Decisions"
                  />
                </Card>
              </>
            )}

            {llmStats && (
              <Card className="space-y-3">
                <h3 className="text-sm font-medium text-text-secondary">LLM Provider Calls</h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-text-muted">Calls</p>
                    <p className="text-text-primary font-medium">{llmStats.total_calls}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Success Rate</p>
                    <p className="text-text-primary font-medium">
                      {((llmStats.success_rate ?? 0) * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-text-muted">Avg Latency</p>
                    <p className="text-text-primary font-medium">{(llmStats.avg_latency_ms ?? 0).toFixed(0)} ms</p>
                  </div>
                </div>
                {llmStats.by_provider?.length > 0 && (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border-subtle">
                        <th className="text-left text-text-muted font-medium">Provider</th>
                        <th className="text-right text-text-muted font-medium">Calls</th>
                        <th className="text-right text-text-muted font-medium">Avg Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {llmStats.by_provider.map((p) => (
                        <tr key={p.provider} className="border-b border-border-subtle last:border-0">
                          <td className="py-2 text-text-primary">{p.provider}</td>
                          <td className="py-2 text-right text-text-secondary">{p.calls ?? 0}</td>
                          <td className="py-2 text-right text-text-secondary">{(p.avg_latency ?? 0).toFixed(0)} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Card>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">Manual Processing</h2>
          <Card>
            <div className="flex items-center gap-4">
              <Input
                label="Hit ID"
                placeholder="Enter hit ID to process"
                value={hitId}
                onChange={(e) => setHitId(e.target.value)}
                className="flex-1"
              />
              <div className="pt-5">
                <Button
                  onClick={() => processHitMutation.mutate(hitId)}
                  loading={processHitMutation.isPending}
                  disabled={!hitId}
                >
                  Process Hit
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">Recent LLM Calls</h2>
          {llmCalls && llmCalls.length > 0 ? (
            <div className="rounded-xl border border-border-subtle bg-bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Time</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Provider</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Model</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Status</th>
                    <th className="text-right px-4 py-3 text-text-muted font-medium">Latency</th>
                    <th className="text-left px-4 py-3 text-text-muted font-medium">Hit</th>
                  </tr>
                </thead>
                <tbody>
                  {llmCalls.map((call) => (
                    <tr key={call.id} className="border-b border-border-subtle last:border-0">
                      <td className="px-4 py-2.5 text-text-muted">{formatDateTime(call.created_at).slice(0, 19)}</td>
                      <td className="px-4 py-2.5 text-text-primary">{call.provider}</td>
                      <td className="px-4 py-2.5 text-text-secondary">{call.model}</td>
                      <td className="px-4 py-2.5 text-text-secondary">{call.status}</td>
                      <td className="px-4 py-2.5 text-right text-text-secondary">{call.latency_ms} ms</td>
                      <td className="px-4 py-2.5 text-text-muted font-mono text-xs">{call.hit_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-text-muted">No LLM calls recorded yet</p>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
