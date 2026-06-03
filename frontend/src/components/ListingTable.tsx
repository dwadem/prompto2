import clsx from 'clsx'
import type { Listing } from '../types'

interface ListingTableProps {
  listings: Listing[]
  onRowClick: (l: Listing) => void
  selectedId: number | null
}

function conditionBadge(condition: Listing['finishing_condition']) {
  const cfg = {
    ready: { label: 'READY', cls: 'bg-green-100 text-green-800' },
    finishing: { label: 'FINISHING', cls: 'bg-yellow-100 text-yellow-800' },
    renovation: { label: 'RENOVATION', cls: 'bg-orange-100 text-orange-800' },
    unknown: { label: 'UNKNOWN', cls: 'bg-gray-100 text-gray-600' },
  }
  const { label, cls } = cfg[condition] ?? cfg.unknown
  return (
    <span className={clsx('text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide', cls)}>
      {label}
    </span>
  )
}

function discountCell(pct: number) {
  const cls =
    pct > 5
      ? 'text-green-700 font-semibold'
      : pct < 0
      ? 'text-red-600 font-semibold'
      : 'text-yellow-700 font-semibold'
  return <span className={cls}>{pct.toFixed(1)}%</span>
}

function yieldCell(pct: number) {
  const cls =
    pct > 5
      ? 'text-green-700 font-semibold'
      : pct >= 3
      ? 'text-amber-600 font-semibold'
      : 'text-red-600 font-semibold'
  return <span className={cls}>{pct.toFixed(1)}%</span>
}

function scoreBar(score: number) {
  const pct = Math.max(0, Math.min(1, score)) * 100
  const barColor =
    pct >= 60
      ? 'bg-green-500'
      : pct >= 35
      ? 'bg-amber-400'
      : 'bg-red-400'
  return (
    <div className="flex items-center gap-1.5 min-w-[80px]">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5 overflow-hidden">
        <div
          className={clsx('h-full rounded-full', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-700 tabular-nums w-8 text-right">
        {score.toFixed(2)}
      </span>
    </div>
  )
}

const HEADERS = [
  '#',
  'Title',
  'District / Nbhd',
  'Condition',
  'Price PLN',
  'm²',
  'Price/m²',
  'Reno cost',
  'All-in/m²',
  'Discount %',
  'Est. rent/mo',
  'Net yield %',
  'Score',
]

export function ListingTable({ listings, onRowClick, selectedId }: ListingTableProps) {
  return (
    <div
      className="overflow-auto h-full"
      style={{ maxHeight: 'calc(100vh - 200px)' }}
    >
      <table className="min-w-full text-sm border-collapse">
        <thead className="sticky top-0 z-10 bg-gray-50 border-b border-gray-300">
          <tr>
            {HEADERS.map((h) => (
              <th
                key={h}
                className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap select-none"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {listings.length === 0 ? (
            <tr>
              <td colSpan={HEADERS.length} className="text-center py-12 text-gray-400">
                No listings match the current filters.
              </td>
            </tr>
          ) : (
            listings.map((l, idx) => {
              const isSelected = l.id === selectedId
              return (
                <tr
                  key={l.id}
                  onClick={() => onRowClick(l)}
                  className={clsx(
                    'cursor-pointer transition-colors',
                    isSelected
                      ? 'bg-blue-50 border-l-2 border-l-blue-500'
                      : 'hover:bg-gray-50'
                  )}
                >
                  {/* # */}
                  <td className="px-3 py-2 text-gray-400 tabular-nums text-xs">{idx + 1}</td>

                  {/* Title */}
                  <td className="px-3 py-2 max-w-[200px]">
                    <span
                      className="block truncate font-medium text-gray-900"
                      title={l.title}
                    >
                      {l.title}
                    </span>
                  </td>

                  {/* District / Nbhd */}
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{l.district}</div>
                    <div className="text-xs text-gray-400">{l.neighbourhood}</div>
                  </td>

                  {/* Condition */}
                  <td className="px-3 py-2">{conditionBadge(l.finishing_condition)}</td>

                  {/* Price PLN */}
                  <td className="px-3 py-2 tabular-nums text-gray-900 whitespace-nowrap">
                    {l.price_pln.toLocaleString('pl-PL')} PLN
                  </td>

                  {/* m² */}
                  <td className="px-3 py-2 tabular-nums whitespace-nowrap text-gray-700">
                    {l.area_m2.toFixed(1)} m²
                  </td>

                  {/* Price/m² */}
                  <td className="px-3 py-2 tabular-nums whitespace-nowrap text-gray-700">
                    {Math.round(l.price_per_m2).toLocaleString('pl-PL')} PLN/m²
                  </td>

                  {/* Reno cost */}
                  <td className="px-3 py-2 tabular-nums whitespace-nowrap text-gray-700">
                    {l.reno_cost.toLocaleString('pl-PL')} PLN
                  </td>

                  {/* All-in/m² */}
                  <td className="px-3 py-2 tabular-nums whitespace-nowrap text-gray-700">
                    {Math.round(l.all_in_price_per_m2).toLocaleString('pl-PL')} PLN/m²
                  </td>

                  {/* Discount % */}
                  <td className="px-3 py-2 tabular-nums">{discountCell(l.discount_pct)}</td>

                  {/* Est. rent/mo */}
                  <td className="px-3 py-2 tabular-nums whitespace-nowrap text-gray-700">
                    {l.est_monthly_rent.toLocaleString('pl-PL')} PLN
                  </td>

                  {/* Net yield % */}
                  <td className="px-3 py-2 tabular-nums">{yieldCell(l.net_yield_pct)}</td>

                  {/* Score */}
                  <td className="px-3 py-2">{scoreBar(l.deal_score)}</td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}
