import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import type { ListingDetail } from '../types'

interface DetailDrawerProps {
  listing: ListingDetail | null
  onClose: () => void
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500 font-medium mb-0.5">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </div>
  )
}

function conditionBadgeClass(condition: ListingDetail['finishing_condition']) {
  const map: Record<string, string> = {
    ready: 'bg-green-100 text-green-800',
    finishing: 'bg-yellow-100 text-yellow-800',
    renovation: 'bg-orange-100 text-orange-800',
    unknown: 'bg-gray-100 text-gray-600',
  }
  return map[condition] ?? map.unknown
}

function yieldClass(pct: number) {
  if (pct > 5) return 'text-green-700 font-bold'
  if (pct >= 3) return 'text-amber-600 font-bold'
  return 'text-red-600 font-bold'
}

export function DetailDrawer({ listing, onClose }: DetailDrawerProps) {
  if (!listing) return null

  const stats = listing.neighbourhood_stats

  const chartData = [
    {
      name: 'This flat (all-in)',
      value: Math.round(listing.all_in_price_per_m2),
    },
    {
      name: 'Nbhd median',
      value: Math.round(stats.median_sale_price_per_m2),
    },
  ]

  const chartColors = ['#3b82f6', '#10b981']

  const scraped = new Date(listing.scraped_at).toLocaleDateString('pl-PL')

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <aside className="fixed right-0 top-14 bottom-0 w-[480px] bg-white shadow-xl z-50 flex flex-col overflow-hidden border-l border-gray-200">
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-gray-200 flex-shrink-0">
          <div className="flex-1 min-w-0 pr-3">
            <h2 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">
              {listing.title}
            </h2>
            <div className="flex items-center gap-2 mt-1.5">
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${conditionBadgeClass(
                  listing.finishing_condition
                )}`}
              >
                {listing.finishing_condition}
              </span>
              <a
                href={listing.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-0.5"
              >
                View on otodom
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {/* Key metrics grid */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Key Metrics
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <MetricCard
                label="Price"
                value={`${listing.price_pln.toLocaleString('pl-PL')} PLN`}
              />
              <MetricCard
                label="All-in cost"
                value={`${listing.all_in_cost.toLocaleString('pl-PL')} PLN`}
              />
              {/* Net yield with colour */}
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 font-medium mb-0.5">Net yield</p>
                <p className={`text-sm ${yieldClass(listing.net_yield_pct)}`}>
                  {listing.net_yield_pct.toFixed(1)}%
                </p>
              </div>
              <MetricCard
                label="Discount"
                value={`${listing.discount_pct.toFixed(1)}%`}
              />
              <MetricCard
                label="Deal score"
                value={listing.deal_score.toFixed(3)}
              />
              <MetricCard
                label="Est. monthly rent"
                value={`${listing.est_monthly_rent.toLocaleString('pl-PL')} PLN`}
              />
            </div>
          </section>

          {/* Renovation breakdown */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Cost Breakdown
            </h3>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Condition', 'Price PLN', 'Reno cost', 'All-in cost', 'All-in/m²'].map((h) => (
                      <th
                        key={h}
                        className="px-3 py-2 text-left text-xs font-semibold text-gray-500"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-gray-100">
                    <td className="px-3 py-2">
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${conditionBadgeClass(
                          listing.finishing_condition
                        )}`}
                      >
                        {listing.finishing_condition}
                      </span>
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {listing.price_pln.toLocaleString('pl-PL')} PLN
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {listing.reno_cost.toLocaleString('pl-PL')} PLN
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {listing.all_in_cost.toLocaleString('pl-PL')} PLN
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {Math.round(listing.all_in_price_per_m2).toLocaleString('pl-PL')} PLN/m²
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Neighbourhood context */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Neighbourhood Context
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <MetricCard
                label="Median sale price/m²"
                value={`${Math.round(stats.median_sale_price_per_m2).toLocaleString('pl-PL')} PLN/m²`}
              />
              <MetricCard
                label="Mean rent/m²"
                value={`${stats.mean_rent_per_m2.toFixed(1)} PLN/m²`}
              />
              <MetricCard
                label="Sale comps"
                value={String(stats.sale_count)}
              />
              <MetricCard
                label="Rent comps"
                value={String(stats.rent_count)}
              />
            </div>
          </section>

          {/* Price vs neighbourhood bar chart */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Price vs Neighbourhood Median
            </h3>
            <div style={{ width: 400, height: 220 }}>
              <BarChart
                width={400}
                height={220}
                data={chartData}
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6b7280' }} />
                <YAxis
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  tickFormatter={(v: number | string) => `${(Number(v) / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(value: number | string) => [
                    `${Number(value).toLocaleString('pl-PL')} PLN/m²`,
                    'Price/m²',
                  ]}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={chartColors[index]} />
                  ))}
                </Bar>
              </BarChart>
            </div>
          </section>

          {/* Details */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Details
            </h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              {[
                ['Rooms', `${listing.rooms}`],
                ['Floor', listing.floor != null ? String(listing.floor) : '—'],
                ['Year built', listing.year_built != null ? String(listing.year_built) : '—'],
                ['District', listing.district],
                ['Neighbourhood', listing.neighbourhood],
                ['Scraped at', scraped],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-gray-500">{label}</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </aside>
    </>
  )
}
