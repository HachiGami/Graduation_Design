import request from './request'
import type { Resource } from '@/types'

export const getResources = () => {
  return request.get<any, Resource[]>('/resources')
}

export const getResource = (id: string) => {
  return request.get<any, Resource>(`/resources/${id}`)
}

export const createResource = (data: Resource) => {
  return request.post<any, Resource>('/resources', data)
}

export const updateResource = (id: string, data: Partial<Resource>) => {
  return request.put<any, Resource>(`/resources/${id}`, data)
}

export const deleteResource = (id: string) => {
  return request.delete(`/resources/${id}`)
}





