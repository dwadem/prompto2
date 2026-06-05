import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { triggerScrape } from './api'
import Dashboard from './pages/Dashboard'
import Overview from './pages/Overview'

function ScrapeButton() {
  const queryClient = useQueryClient()
  const [flashMsg, setFlashMsg] = useState<string | null>(null)

  const { mutate, isPending } = useMutation({
    mutationFn: triggerScrape,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['listings'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      queryClient.invalidateQueries({ queryKey: ['districts'] })
      setFlashMsg(
        data.listings_upserted > 0
          ? `${data.listings_upserted} listings updated`
          : 'Done — 0 listings (server IP may be blocked by Cloudflare)'
      )
    },
    onError: (err: Error) => {
      setFlashMsg(`Scrape failed: ${err.message}`)
    },
  })

  // Clear the flash message after 6 seconds.
  useEffect(() => {
    if (!flashMsg) return
    const t = setTimeout(() => setFlashMsg(null), 6000)
    return () => clearTimeout(t)
  }, [flashMsg])

  return (
    <div className="flex items-center gap-2">
      {flashMsg && (
        <span className="text-xs text-gray-600 max-w-[240px] truncate" title={flashMsg}>
          {flashMsg}
        </span>
      )}
      <button
        onClick={() => mutate()}
        disabled={isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium border transition-colors disabled:opacity-60 disabled:cursor-not-allowed border-blue-300 text-blue-700 hover:bg-blue-50 active:bg-blue-100"
        title="Scrape Otodom for fresh Rzeszów listings"
      >
        {isPending ? (
          <>
            <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            Scraping…
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582M20 20v-5h-.581M5.635 15A9 9 0 1018.364 8.636" />
            </svg>
            Scrape Otodom
          </>
        )}
      </button>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Navigation bar */}
        <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
          <div className="max-w-screen-2xl mx-auto px-4 h-14 flex items-center justify-between">
            {/* Left: branding */}
            <div className="flex items-center gap-3">
              <span className="font-bold text-lg text-gray-900">
                🏠 Rzeszów Yield Analyser
              </span>
              <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2.5 py-0.5 font-medium">
                📍 Rzeszów only
              </span>
            </div>

            {/* Right: scrape button + nav links */}
            <div className="flex items-center gap-3">
              <ScrapeButton />
              <div className="flex items-center gap-1">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/overview"
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  Overview
                </NavLink>
              </div>
            </div>
          </div>
        </nav>

        {/* Page content */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/overview" element={<Overview />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
