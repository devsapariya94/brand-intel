import { apiClient } from './client'
import type { DLQItem } from '@/types'

export const adminApi = {
  getDLQ: (limit = 50) =>
    apiClient.get<DLQItem[]>('/admin/dlq', { params: { limit } }).then((r) => r.data),
  retryDLQ: (id: string) =>
    apiClient.post(`/admin/dlq/${id}/retry`).then((r) => r.data),
  deleteDLQ: (id: string) =>
    apiClient.delete(`/admin/dlq/${id}`).then((r) => r.data),
  resetCircuitBreaker: (monitorType: string) =>
    apiClient.post('/admin/circuit-breaker/reset', { monitor_type: monitorType }).then((r) => r.data),
  triggerCleanup: () =>
    apiClient.post('/admin/cleanup').then((r) => r.data),
}
