import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    const { error } = this.state
    if (error) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
          <div className="max-w-lg w-full bg-white rounded-xl shadow-sm border border-red-200 p-8 text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-lg font-semibold text-gray-900 mb-2">
              Application Error
            </h1>
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3 mb-4 text-left font-mono break-all">
              {error.message}
            </p>
            <p className="text-sm text-gray-500">
              If you deployed on Railway, make sure{' '}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono">
                VITE_API_URL
              </code>{' '}
              is set to your backend service URL in the frontend service Variables, then
              redeploy.
            </p>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
