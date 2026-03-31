import request from './request'
import type { Personnel } from '@/types'

export const getPersonnelList = () => {
  return request.get<any, Personnel[]>('/personnel')
}

export const getPersonnelById = (id: string) => {
  return request.get<any, Personnel>(`/personnel/${id}`)
}

export const createPersonnel = (data: Personnel) => {
  return request.post<any, Personnel>('/personnel', data)
}

export const updatePersonnel = (id: string, data: Partial<Personnel>) => {
  return request.put<any, Personnel>(`/personnel/${id}`, data)
}

export const deletePersonnel = (id: string) => {
  return request.delete(`/personnel/${id}`)
}






