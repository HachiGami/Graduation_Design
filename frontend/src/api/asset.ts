import request from './request'
import type { Asset } from '@/types'

export const getAssets = (params?: { asset_type?: string, model?: string, status?: string }) => {
  return request.get<any, Asset[]>('/assets', { params })
}

export const getAsset = (id: string) => {
  return request.get<any, Asset>(`/assets/${id}`)
}

export const createAsset = (data: Asset) => {
  return request.post<any, Asset>('/assets', data)
}

export const updateAsset = (id: string, data: Partial<Asset>) => {
  return request.put<any, Asset>(`/assets/${id}`, data)
}

export const deleteAsset = (id: string) => {
  return request.delete(`/assets/${id}`)
}

export const allocateAsset = (activityId: string, assetId: string, rate?: number) => {
  return request.post('/assets/allocate', null, {
    params: { activity_id: activityId, asset_id: assetId, rate }
  })
}

export const releaseAsset = (activityId: string, assetId: string) => {
  return request.post('/assets/release', null, {
    params: { activity_id: activityId, asset_id: assetId }
  })
}
