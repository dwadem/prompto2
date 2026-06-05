import axios from 'axios'
import type { Listing, ListingDetail, DistrictOverview, Filters } from './types'

// VITE_API_URL is embedded at build time.
// On Railway: set VITE_API_URL in the frontend service's Variables to the backend service URL.
// Locally: Vite dev proxy rewrites /api → http://localhost:8000.
const api = axios.create({
  baseURL: (import.meta.env.VITE_API_URL ?? '') + '/api',
})

// If VITE_API_URL is unset, API calls hit the frontend domain and the SPA server
// returns index.html (200, text/html). Catch that case and surface a clear error
// instead of letting callers receive an HTML string and crash.
api.interceptors.response.use((response) => {
  const ct = (response.headers['content-type'] as string | undefined) ?? ''
  if (ct.startsWith('text/html')) {
    return Promise.reject(
      new Error(
        'Backend unreachable — set VITE_API_URL in Railway to your backend service URL and redeploy.'
      )
    )
  }
  return response
})

export async function fetchListings(filters: Partial<Filters>): Promise<Listing[]> {
  const params = new URLSearchParams()

  if (filters.district) params.set('district', filters.district)
  if (filters.finishing_condition && filters.finishing_condition.length > 0) {
    filters.finishing_condition.forEach((c) => params.append('finishing_condition', c))
  }
  if (filters.max_price != null) params.set('max_price', String(filters.max_price))
  if (filters.max_all_in_cost != null) params.set('max_all_in_cost', String(filters.max_all_in_cost))
  if (filters.min_area != null) params.set('min_area', String(filters.min_area))
  if (filters.min_rooms != null) params.set('min_rooms', String(filters.min_rooms))
  if (filters.min_net_yield != null) params.set('min_net_yield', String(filters.min_net_yield))
  if (filters.min_discount != null) params.set('min_discount', String(filters.min_discount))
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  if (filters.sort_dir) params.set('sort_dir', filters.sort_dir)

  const response = await api.get<Listing[]>('/listings', { params })
  return response.data
}

export async function fetchListing(id: number): Promise<ListingDetail> {
  const response = await api.get<ListingDetail>(`/listings/${id}`)
  return response.data
}

export async function fetchOverview(): Promise<DistrictOverview[]> {
  const response = await api.get<DistrictOverview[]>('/overview')
  return response.data
}

export async function fetchDistricts(): Promise<string[]> {
  const response = await api.get<string[]>('/districts')
  return response.data
}
