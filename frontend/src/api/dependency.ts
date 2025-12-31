import request from './request'
import type { Dependency, GraphData } from '@/types'

export const getDependencies = () => {
  return request.get<any, Dependency[]>('/dependencies')
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

export const getGraphData = () => {
  return request.get<any, GraphData>('/dependencies/graph/data')
}





