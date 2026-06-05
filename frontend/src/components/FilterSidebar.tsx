import type { Filters } from '../types'

interface FilterSidebarProps {
  filters: Filters
  onChange: (f: Filters) => void
  districts: string[]
}

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

const SORT_OPTIONS = [
  { value: 'deal_score', label: 'Deal Score' },
  { value: 'net_yield_pct', label: 'Net Yield %' },
  { value: 'discount_pct', label: 'Discount %' },
  { value: 'all_in_price_per_m2', label: 'All-in Price/m²' },
  { value: 'price_pln', label: 'Price PLN' },
]

const CONDITIONS = [
  { value: 'ready', label: 'Ready', dot: 'bg-green-500' },
  { value: 'finishing', label: 'Finishing', dot: 'bg-yellow-400' },
  { value: 'renovation', label: 'Renovation', dot: 'bg-orange-500' },
]

function SectionDivider({ title }: { title: string }) {
  return (
    <div className="pt-4 pb-1">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</p>
    </div>
  )
}

function NumberInput({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string
  label: string
  value: number | null
  onChange: (v: number | null) => void
  placeholder?: string
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs text-gray-600 mb-1">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type="number"
        className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
        placeholder={placeholder ?? ''}
        value={value ?? ''}
        onChange={(e) => {
          const raw = e.target.value
          onChange(raw === '' ? null : Number(raw))
        }}
      />
    </div>
  )
}

export function FilterSidebar({ filters, onChange, districts }: FilterSidebarProps) {
  function set<K extends keyof Filters>(key: K, value: Filters[K]) {
    onChange({ ...filters, [key]: value })
  }

  function toggleCondition(cond: string) {
    const existing = filters.finishing_condition
    if (existing.includes(cond)) {
      set('finishing_condition', existing.filter((c) => c !== cond))
    } else {
      set('finishing_condition', [...existing, cond])
    }
  }

  return (
    <aside className="w-[280px] min-w-[280px] bg-white border-r border-gray-200 h-[calc(100vh-56px)] overflow-y-auto flex-shrink-0">
      <div className="px-4 py-3">
        {/* Reset */}
        <button
          onClick={() => onChange({ ...DEFAULT_FILTERS })}
          className="w-full text-sm text-blue-600 hover:text-blue-800 font-medium py-1.5 px-3 rounded-md border border-blue-200 hover:bg-blue-50 transition-colors"
        >
          Reset filters
        </button>

        {/* District */}
        <SectionDivider title="District" />
        <label htmlFor="district" className="sr-only">
          District
        </label>
        <select
          id="district"
          name="district"
          className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          value={filters.district}
          onChange={(e) => set('district', e.target.value)}
        >
          <option value="">All districts</option>
          {districts.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        {/* Finishing Condition */}
        <SectionDivider title="Finishing Condition" />
        <div className="space-y-2">
          {CONDITIONS.map(({ value, label, dot }) => (
            <label key={value} className="flex items-center gap-2 cursor-pointer select-none">
              <input
                id={`condition-${value}`}
                name={`condition-${value}`}
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-400"
                checked={filters.finishing_condition.includes(value)}
                onChange={() => toggleCondition(value)}
              />
              <span className={`w-2.5 h-2.5 rounded-full ${dot} flex-shrink-0`} />
              <span className="text-sm text-gray-700">{label}</span>
            </label>
          ))}
        </div>

        {/* Price */}
        <SectionDivider title="Price" />
        <NumberInput
          id="max-price"
          label="Max price (PLN)"
          value={filters.max_price}
          onChange={(v) => set('max_price', v)}
          placeholder="e.g. 500000"
        />

        {/* All-in Cost */}
        <SectionDivider title="All-in Cost" />
        <NumberInput
          id="max-all-in"
          label="Max all-in (PLN)"
          value={filters.max_all_in_cost}
          onChange={(v) => set('max_all_in_cost', v)}
          placeholder="e.g. 600000"
        />

        {/* Size */}
        <SectionDivider title="Size" />
        <div className="space-y-2">
          <NumberInput
            id="min-area"
            label="Min area (m²)"
            value={filters.min_area}
            onChange={(v) => set('min_area', v)}
            placeholder="e.g. 40"
          />
          <NumberInput
            id="min-rooms"
            label="Min rooms"
            value={filters.min_rooms}
            onChange={(v) => set('min_rooms', v)}
            placeholder="e.g. 2"
          />
        </div>

        {/* Yield / Discount */}
        <SectionDivider title="Yield / Discount" />
        <div className="space-y-2">
          <NumberInput
            id="min-net-yield"
            label="Min net yield (%)"
            value={filters.min_net_yield}
            onChange={(v) => set('min_net_yield', v)}
            placeholder="e.g. 5"
          />
          <NumberInput
            id="min-discount"
            label="Min discount (%)"
            value={filters.min_discount}
            onChange={(v) => set('min_discount', v)}
            placeholder="e.g. 3"
          />
        </div>

        {/* Sort */}
        <SectionDivider title="Sort" />
        <div className="space-y-2">
          <div>
            <label htmlFor="sort-by" className="block text-xs text-gray-600 mb-1">
              Sort by
            </label>
            <select
              id="sort-by"
              name="sort-by"
              className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              value={filters.sort_by}
              onChange={(e) => set('sort_by', e.target.value)}
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex rounded-md border border-gray-300 overflow-hidden">
            <button
              className={`flex-1 text-sm py-1.5 transition-colors ${
                filters.sort_dir === 'desc'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              onClick={() => set('sort_dir', 'desc')}
            >
              ↓ Desc
            </button>
            <button
              className={`flex-1 text-sm py-1.5 border-l border-gray-300 transition-colors ${
                filters.sort_dir === 'asc'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              onClick={() => set('sort_dir', 'asc')}
            >
              ↑ Asc
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
