import { apiClient } from './client'
import type { HealthStatus, Metrics } from '@/types'

export const healthApi = {
  get: () => apiClient.get<HealthStatus>('/health').then((r) => r.data),
  getDetailed: () => apiClient.get<HealthStatus>('/health/detailed').then((r) => r.data),
  getMetrics: () => apiClient.get<Metrics>('/health/metrics').then((r) => r.data),
}
