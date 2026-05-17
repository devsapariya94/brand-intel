import { apiClient } from './client'
import type { MonitorStatus, MonitorRun, CircuitBreakerState, MonitorTriggerResult, MonitorSingleTriggerResult } from '@/types'

interface MonitorStatusResponse {
  monitors: MonitorStatus[]
  circuit_breaker: Record<string, CircuitBreakerState>
}

export const monitorsApi = {
  getStatus: () =>
    apiClient.get<MonitorStatusResponse>('/monitors/status').then((r) => r.data),
  triggerAll: (brandId?: string) =>
    apiClient.post<MonitorTriggerResult>('/monitors/trigger', brandId ? { brand_id: brandId } : {}).then((r) => r.data),
  trigger: (monitorType: string, brandId: string) =>
    apiClient.post<MonitorSingleTriggerResult>(`/monitors/${monitorType}/trigger`, { brand_id: brandId }).then((r) => r.data),
  getRuns: (params?: { limit?: number; status?: string; monitor_type?: string; brand_id?: string }) =>
    apiClient.get<MonitorRun[]>('/monitors/runs', { params }).then((r) => r.data),
  getHealth: (monitorType: string) =>
    apiClient.get(`/monitors/${monitorType}/health`).then((r) => r.data),
  resetCircuitBreaker: (monitorType: string) =>
    apiClient.post('/admin/circuit-breaker/reset', { monitor_type: monitorType }).then((r) => r.data),
}
