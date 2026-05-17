import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { HitCard } from '@/components/HitCard'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { hitsApi } from '@/api/hits'
import { brandsApi } from '@/api/brands'
import { formatNumber } from '@/utils/formatters'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

export default function Alerts() {
  const queryClient = useQueryClient()
  const [brandFilter, setBrandFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [sourceFilter, setSourceFilter] = useState('All')
  const [decisionFilter, setDecisionFilter] = useState('All')
  const [severityFilter, setSeverityFilter] = useState('All')
  const [limit, setLimit] = useState(50)

  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list(),
  })

  const { data: hitsStats } = useQuery({
    queryKey: ['hits-stats'],
    queryFn: () => hitsApi.getStats(),
  })

  const { data: hitsData, isLoading } = useQuery({
    queryKey: ['hits', brandFilter, statusFilter, sourceFilter, limit],
    queryFn: () =>
      hitsApi.list({
        brand_id: brandFilter || undefined,
        status: statusFilter !== 'All' ? statusFilter : undefined,
        source: sourceFilter !== 'All' ? sourceFilter : undefined,
        limit,
      }),
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ hitId, status }: { hitId: string; status: string }) =>
      hitsApi.updateStatus(hitId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hits'] })
      queryClient.invalidateQueries({ queryKey: ['hits-stats'] })
      toast.success('Status updated')
    },
  })

  const brandOptions = [
    { value: '', label: 'All Brands' },
    ...(brands ?? []).map((b) => ({ value: b.id, label: b.name })),
  ]

  const filteredHits = hitsData?.hits.filter((hit) => {
    if (decisionFilter !== 'All') {
      if (decisionFilter === 'Not processed') {
        if (hit.enrichment) return false
      } else {
        if (hit.enrichment?.decision !== decisionFilter) return false
      }
    }
    if (severityFilter !== 'All') {
      if (hit.enrichment?.evaluation?.severity !== severityFilter) return false
    }
    return true
  })

  const handleExport = () => {
    if (!filteredHits?.length) return
    const csv = [
      'Brand,Source,Status,Detected At,URL,Keywords,Preview',
      ...filteredHits.map((h) =>
        [
          h.brand_name,
          h.source,
          h.processing_status,
          h.detected_at,
          h.source_url,
          (h.match_details?.matched_keywords ?? []).join('; '),
          `"${(h.content_preview ?? '').slice(0, 200).replace(/"/g, '""')}"`,
        ].join(',')
      ),
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'hits_export.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <PageLayout title="Alerts & Hits">
      <div className="space-y-6">
        <Card>
          <div className="grid grid-cols-7 gap-4">
            <Select
              label="Brand"
              options={brandOptions}
              value={brandFilter}
              onChange={(e) => setBrandFilter(e.target.value)}
            />
            <Select
              label="Status"
              options={[
                { value: 'All', label: 'All' },
                { value: 'pending', label: 'Pending' },
                { value: 'reviewed', label: 'Reviewed' },
                { value: 'false_positive', label: 'False Positive' },
              ]}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            />
            <Select
              label="Source"
              options={[
                { value: 'All', label: 'All' },
                { value: 'github', label: 'GitHub' },
                { value: 'hackernews', label: 'HackerNews' },
                { value: 'ransomware', label: 'Ransomware' },
                { value: 'xposedornot', label: 'XposedOrNot' },
                { value: 'intelx', label: 'Intelligence X' },
              ]}
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
            />
            <Select
              label="LLM Decision"
              options={[
                { value: 'All', label: 'All' },
                { value: 'ALERT', label: 'ALERT' },
                { value: 'ESCALATE', label: 'ESCALATE' },
                { value: 'SUPPRESS', label: 'SUPPRESS' },
                { value: 'Not processed', label: 'Not processed' },
              ]}
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
            />
            <Select
              label="Severity"
              options={[
                { value: 'All', label: 'All' },
                { value: 'CRITICAL', label: 'CRITICAL' },
                { value: 'HIGH', label: 'HIGH' },
                { value: 'MEDIUM', label: 'MEDIUM' },
                { value: 'LOW', label: 'LOW' },
              ]}
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            />
            <Select
              label="Limit"
              options={[
                { value: '10', label: '10' },
                { value: '25', label: '25' },
                { value: '50', label: '50' },
                { value: '100', label: '100' },
              ]}
              value={String(limit)}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
            <div className="flex items-end">
              <Button className="w-full" onClick={() => queryClient.invalidateQueries({ queryKey: ['hits'] })}>
                Apply Filters
              </Button>
            </div>
          </div>
        </Card>

        {hitsStats && (
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <p className="text-sm text-text-muted">Total Hits</p>
              <p className="text-2xl font-bold text-text-primary">{formatNumber(hitsStats.total_hits)}</p>
            </Card>
            <Card>
              <p className="text-sm text-text-muted">Pending</p>
              <p className="text-2xl font-bold text-amber-neon">{hitsStats.by_status?.pending ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-text-muted">Reviewed</p>
              <p className="text-2xl font-bold text-green-neon">{hitsStats.by_status?.reviewed ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-text-muted">False Positive</p>
              <p className="text-2xl font-bold text-text-muted">{hitsStats.by_status?.false_positive ?? 0}</p>
            </Card>
          </div>
        )}

        {filteredHits?.length ? (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-muted">
                Showing {filteredHits.length} of {hitsData?.total ?? 0} hits
              </p>
              <Button variant="secondary" size="sm" onClick={handleExport}>
                <Download className="w-4 h-4 mr-1.5" />
                Export CSV
              </Button>
            </div>
            <div className="space-y-3">
              {filteredHits.map((hit) => (
                <HitCard
                  key={hit.id}
                  hit={hit}
                  onStatusChange={(hitId, status) =>
                    updateStatusMutation.mutate({ hitId, status })
                  }
                />
              ))}
            </div>
          </>
        ) : (
          <p className="text-text-muted">
            {isLoading ? 'Loading hits...' : 'No hits found matching filters'}
          </p>
        )}
      </div>
    </PageLayout>
  )
}
