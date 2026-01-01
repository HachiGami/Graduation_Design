import request from './request'
import type { Dependency, GraphData } from '@/types'

export const getDependencies = (params: { domain: string, process_id?: string, activity_id?: string }) => {
  return request.get<any, Dependency[]>('/dependencies', { params })
}

export const getDependency = (id: string) => {
  return request.get<any, Dependency>(`/dependencies/${id}`)
}

export const createDependency = (data: Dependency) => {
  return request.post<any, Dependency>('/dependencies', data)
}

export const updateDependency = (id: string, data: Partial<Dependency>) => {
  return request.put<any, Dependency>(`/dependencies/${id}`, data)
}

export const deleteDependency = (id: string) => {
  return request.delete(`/dependencies/${id}`)
}

export const getGraphData = (params?: { scope?: string; domain?: string; process_id?: string; include_cross?: boolean }) => {
  return request.get<any, GraphData>('/dependencies/graph/data', { params })
}





