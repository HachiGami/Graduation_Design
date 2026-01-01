import request from './request'
import type { ResourceUsage } from '@/types'

export const getResourceUsages = (params?: { activity_id?: string; resource_id?: string; domain?: string; process_id?: string }) => {
  return request.get<any, ResourceUsage[]>('/resource-usage', { params })
}

export const getResourceUsage = (id: string) => {
  return request.get<any, ResourceUsage>(`/resource-usage/${id}`)
}

export const createResourceUsage = (data: ResourceUsage) => {
  return request.post<any, ResourceUsage>('/resource-usage', data)
}

export const updateResourceUsage = (id: string, data: Partial<ResourceUsage>) => {
  return request.put<any, ResourceUsage>(`/resource-usage/${id}`, data)
}

export const deleteResourceUsage = (id: string) => {
  return request.delete(`/resource-usage/${id}`)
}

