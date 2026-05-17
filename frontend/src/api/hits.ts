import { apiClient } from './client'
import type { Hit, HitsResponse, HitsStats } from '@/types'

export const hitsApi = {
  list: (params?: { brand_id?: string; status?: string; source?: string; limit?: number; page?: number }) =>
    apiClient.get<HitsResponse>('/hits', { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Hit>(`/hits/${id}`).then((r) => r.data),
  updateStatus: (id: string, status: string, notes?: string) =>
    apiClient.patch(`/hits/${id}/status`, { status, notes }).then((r) => r.data),
  getStats: (params?: { brand_id?: string; days?: number }) =>
    apiClient.get<HitsStats>('/hits/stats', { params }).then((r) => r.data),
}
