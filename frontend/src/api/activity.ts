import request from './request'
import type { Activity, ActivityDetails } from '@/types'

export const getActivities = (params: { domain: string, process_id?: string }) => {
  return request.get<any, Activity[]>('/activities', { params })
}

export const getActivity = (id: string) => {
  return request.get<any, Activity>(`/activities/${id}`)
}

export const getActivityDetails = (id: string) => {
  return request.get<any, ActivityDetails>(`/activities/${id}/details`)
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

export const batchUpdateStatus = (domain: string, processId: string, newStatus: string) => {
  return request.post('/activities/batch-status', null, {
    params: { domain, process_id: processId, new_status: newStatus }
  })
}






