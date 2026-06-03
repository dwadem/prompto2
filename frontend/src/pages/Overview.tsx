import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { fetchOverview } from '../api'
import { OverviewTable } from '../components/OverviewTable'

export default function Overview() {
  const {
    data: overview = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['overview'],
    queryFn: fetchOverview,
    staleTime: 5 * 60_000,
  })

  const chartData = overview.map((d) => ({
    district: d.district,
    'Price/m²': Math.round(d.mean_price_per_m2),
    'Annual rent/m²': Math.round(d.mean_rent_per_m2 * 12),
  }))

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Rzeszów District Overview</h1>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3 text-gray-500">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Loading overview…</span>
          </div>
        </div>
      ) : isError ? (
        <div className="text-center py-16">
          <p className="text-red-600 font-medium">Failed to load overview</p>
          <p className="text-sm text-gray-500 mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      ) : (
        <>
          <OverviewTable data={overview} />

          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              Price vs Annualised Rent by District
            </h2>
            <div style={{ width: 600, height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 8, right: 24, left: 16, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="district"
                    tick={{ fontSize: 11, fill: '#6b7280' }}
                    angle={-30}
                    textAnchor="end"
                    height={56}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#6b7280' }}
                    tickFormatter={(v: number | string) => `${(Number(v) / 1000).toFixed(0)}k`}
                    unit=""
                  />
                  <Tooltip
                    formatter={(value: number | string, name: string | number) => [
                      `${Number(value).toLocaleString('pl-PL')} PLN/m²`,
                      String(name),
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Price/m²" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Annual rent/m²" fill="#10b981" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
