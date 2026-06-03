import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchListings, fetchListing, fetchDistricts } from '../api'
import { FilterSidebar } from '../components/FilterSidebar'
import { ListingTable } from '../components/ListingTable'
import { DetailDrawer } from '../components/DetailDrawer'
import type { Filters, Listing, ListingDetail } from '../types'

const DEFAULT_FILTERS: Filters = {
  district: '',
  finishing_condition: [],
  max_price: null,
  max_all_in_cost: null,
  min_area: null,
  min_rooms: null,
  min_net_yield: null,
  min_discount: null,
  sort_by: 'deal_score',
  sort_dir: 'desc',
}

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const {
    data: listings = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => fetchListings(filters),
  })

  const { data: districts = [] } = useQuery({
    queryKey: ['districts'],
    queryFn: fetchDistricts,
    staleTime: 5 * 60_000,
  })

  const { data: selectedDetail } = useQuery<ListingDetail>({
    queryKey: ['listing', selectedId],
    queryFn: () => fetchListing(selectedId!),
    enabled: selectedId != null,
  })

  function handleRowClick(listing: Listing) {
    setSelectedId(listing.id === selectedId ? null : listing.id)
  }

  function handleCloseDrawer() {
    setSelectedId(null)
  }

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Sidebar */}
      <FilterSidebar
        filters={filters}
        onChange={setFilters}
        districts={districts}
      />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Status bar */}
        <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between flex-shrink-0">
          <span className="text-sm text-gray-600">
            {isLoading ? (
              <span className="text-gray-400">Loading listings…</span>
            ) : isError ? (
              <span className="text-red-500">Error loading data</span>
            ) : (
              <span>
                <span className="font-semibold text-gray-900">{listings.length}</span> listings found
              </span>
            )}
          </span>
        </div>

        {/* Content area */}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-gray-500">
              <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm">Loading listings…</span>
            </div>
          </div>
        ) : isError ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-red-600 font-medium">Failed to load listings</p>
              <p className="text-sm text-gray-500 mt-1">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden relative">
            <ListingTable
              listings={listings}
              onRowClick={handleRowClick}
              selectedId={selectedId}
            />
          </div>
        )}
      </div>

      {/* Detail drawer */}
      <DetailDrawer
        listing={selectedDetail ?? null}
        onClose={handleCloseDrawer}
      />
    </div>
  )
}
