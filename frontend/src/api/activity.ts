import request from './request'
import type { Activity } from '@/types'

export const getActivities = () => {
  return request.get<any, Activity[]>('/activities')
}

export const getActivity = (id: string) => {
  return request.get<any, Activity>(`/activities/${id}`)
}

export const createActivity = (data: Activity) => {
  return request.post<any, Activity>('/activities', data)
}

export const updateActivity = (id: string, data: Partial<Activity>) => {
  return request.put<any, Activity>(`/activities/${id}`, data)
}

export const deleteActivity = (id: string) => {
  return request.delete(`/activities/${id}`)
}





