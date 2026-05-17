import { apiClient } from './client'
import type { EnrichmentConfig, EnrichmentStats, LlmCallStats, LlmCall } from '@/types'

export const enrichmentApi = {
  getConfig: () =>
    apiClient.get<EnrichmentConfig>('/enrichment/config').then((r) => r.data),
  updateConfig: (config: Partial<EnrichmentConfig>) =>
    apiClient.put('/enrichment/config', config).then((r) => r.data),
  getStats: () =>
    apiClient.get<EnrichmentStats>('/enrichment/stats').then((r) => r.data),
  getLlmCalls: (limit = 50) =>
    apiClient.get<LlmCall[]>('/enrichment/llm-calls', { params: { limit } }).then((r) => r.data),
  getLlmCallStats: () =>
    apiClient.get<LlmCallStats>('/enrichment/llm-calls/stats').then((r) => r.data),
  processHit: (hitId: string) =>
    apiClient.post(`/enrichment/process/${hitId}`).then((r) => r.data),
}
