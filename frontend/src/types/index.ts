export interface Listing {
  id: number
  url: string
  title: string
  transaction_type: string
  district: string
  neighbourhood: string
  price_pln: number
  area_m2: number
  rooms: number
  floor: number | null
  year_built: number | null
  finishing_condition: 'ready' | 'finishing' | 'renovation' | 'unknown'
  lat: number | null
  lng: number | null
  scraped_at: string
  price_per_m2: number
  reno_cost: number
  all_in_cost: number
  all_in_price_per_m2: number
  discount_pct: number
  est_monthly_rent: number
  gross_yield_pct: number
  net_yield_pct: number
  deal_score: number
}

export interface NeighbourhoodStats {
  median_sale_price_per_m2: number
  mean_rent_per_m2: number
  sale_count: number
  rent_count: number
}

export interface ListingDetail extends Listing {
  neighbourhood_stats: NeighbourhoodStats
}

export interface ConditionBreakdown {
  condition: string
  count: number
  mean_price_per_m2: number
}

export interface DistrictOverview {
  district: string
  mean_price_per_m2: number
  mean_rent_per_m2: number
  avg_net_yield: number
  listing_count: number
  by_condition: ConditionBreakdown[]
}

export interface Filters {
  district: string
  finishing_condition: string[]
  max_price: number | null
  max_all_in_cost: number | null
  min_area: number | null
  min_rooms: number | null
  min_net_yield: number | null
  min_discount: number | null
  sort_by: string
  sort_dir: 'asc' | 'desc'
}
