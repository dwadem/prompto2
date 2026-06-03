import type { DistrictOverview } from '../types'

interface OverviewTableProps {
  data: DistrictOverview[]
}

function yieldClass(pct: number) {
  if (pct > 5) return 'text-green-700 font-semibold'
  if (pct >= 3) return 'text-amber-600 font-semibold'
  return 'text-red-600 font-semibold'
}

function ConditionBreakdownBadges({ byCondition }: { byCondition: DistrictOverview['by_condition'] }) {
  const conditionMap: Record<string, { icon: string; cls: string }> = {
    ready: { icon: '✓', cls: 'bg-green-100 text-green-800' },
    finishing: { icon: '◑', cls: 'bg-yellow-100 text-yellow-800' },
    renovation: { icon: '⚒', cls: 'bg-orange-100 text-orange-800' },
    unknown: { icon: '?', cls: 'bg-gray-100 text-gray-600' },
  }

  return (
    <div className="flex flex-wrap gap-1">
      {byCondition.map(({ condition, count }) => {
        const cfg = conditionMap[condition] ?? conditionMap.unknown
        return (
          <span
            key={condition}
            className={`inline-flex items-center text-[11px] font-medium px-1.5 py-0.5 rounded ${cfg.cls}`}
            title={`${condition}: ${count} listings`}
          >
            {cfg.icon}{count}
          </span>
        )
      })}
    </div>
  )
}

export function OverviewTable({ data }: OverviewTableProps) {
  if (data.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400 text-sm">No overview data available.</div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {[
              'District',
              'Avg price/m²',
              'Avg rent/m²',
              'Avg net yield',
              'Listings',
              'Condition breakdown',
            ].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {data.map((row) => (
            <tr key={row.district} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-semibold text-gray-900">{row.district}</td>
              <td className="px-4 py-3 tabular-nums text-gray-700">
                {Math.round(row.mean_price_per_m2).toLocaleString('pl-PL')} PLN/m²
              </td>
              <td className="px-4 py-3 tabular-nums text-gray-700">
                {row.mean_rent_per_m2.toFixed(1)} PLN/m²
              </td>
              <td className={`px-4 py-3 tabular-nums ${yieldClass(row.avg_net_yield)}`}>
                {row.avg_net_yield.toFixed(1)}%
              </td>
              <td className="px-4 py-3 tabular-nums text-gray-700">{row.listing_count}</td>
              <td className="px-4 py-3">
                <ConditionBreakdownBadges byCondition={row.by_condition} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
