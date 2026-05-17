import { apiClient } from './client'
import type { Brand } from '@/types'

export const brandsApi = {
  list: (activeOnly = false) =>
    apiClient.get<Brand[]>('/brands', { params: { active_only: activeOnly } }).then((r) => r.data),
  get: (id: string) => apiClient.get<Brand>(`/brands/${id}`).then((r) => r.data),
  create: (data: Partial<Brand>) => apiClient.post<Brand>('/brands', data).then((r) => r.data),
  update: (id: string, data: Partial<Brand>) =>
    apiClient.put<Brand>(`/brands/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/brands/${id}`).then((r) => r.data),
  toggle: (id: string) => apiClient.patch(`/brands/${id}/toggle`).then((r) => r.data),
}
