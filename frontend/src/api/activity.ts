import request from './request'
import type { Activity, ActivityDetails, EquipmentRequirement, MaterialRequirement, PersonnelRequirement } from '@/types'

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

export const addActivityPersonnelRequirement = (activityId: string, data: PersonnelRequirement) => {
  return request.post<any, Activity>(`/activities/${activityId}/personnel`, data)
}

export const removeActivityPersonnelRequirement = (activityId: string, role: string) => {
  return request.delete<any, Activity>(`/activities/${activityId}/personnel/${encodeURIComponent(role)}`)
}

export const addActivityEquipmentRequirement = (activityId: string, data: EquipmentRequirement) => {
  return request.post<any, Activity>(`/activities/${activityId}/equipment`, data)
}

export const removeActivityEquipmentRequirement = (activityId: string, model: string) => {
  return request.delete<any, Activity>(`/activities/${activityId}/equipment/${encodeURIComponent(model)}`)
}

export const addActivityMaterialRequirement = (
  activityId: string,
  data: Pick<MaterialRequirement, 'material_model' | 'hourly_consumption_rate' | 'unit'>
) => {
  return request.post<any, Activity>(`/activities/${activityId}/materials`, data)
}

export const removeActivityMaterialRequirement = (activityId: string, materialModel: string) => {
  return request.delete<any, Activity>(`/activities/${activityId}/materials/${encodeURIComponent(materialModel)}`)
}





