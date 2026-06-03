import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Overview from './pages/Overview'

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

            {/* Right: nav links */}
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
