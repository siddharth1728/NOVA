import { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState({ backend: 'Unknown', database: 'Unknown' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/health')
        if (response.ok) {
          const data = await response.json()
          setHealth({
            backend: 'Connected',
            database: data.database === 'connected' ? 'Connected' : 'Unavailable'
          })
        } else {
          setHealth({ backend: 'Unavailable', database: 'Unknown' })
        }
      } catch (error) {
        setHealth({ backend: 'Unavailable', database: 'Unknown' })
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
  }, [])

  const isHealthy = health.backend === 'Connected' && health.database === 'Connected'
  const hasFailed = health.backend === 'Unavailable' || health.database === 'Unavailable'

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 max-w-md w-full">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">KaryaSetu</h1>
        <h2 className="text-sm font-medium text-gray-500 mb-6 uppercase tracking-wider">SIH26122</h2>
        
        <h3 className="text-lg font-semibold text-gray-700 mb-4 border-b pb-2">System Status</h3>
        
        <div className="space-y-4 mb-8">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Backend</span>
            <span className={`font-medium ${health.backend === 'Connected' ? 'text-green-600' : 'text-red-500'}`}>
              {loading ? 'Checking...' : health.backend}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Database</span>
            <span className={`font-medium ${health.database === 'Connected' ? 'text-green-600' : health.database === 'Unknown' ? 'text-gray-400' : 'text-red-500'}`}>
              {loading ? 'Checking...' : health.database}
            </span>
          </div>
        </div>

        <div className={`p-4 rounded-lg flex items-center justify-center font-medium ${isHealthy ? 'bg-green-50 text-green-700' : hasFailed ? 'bg-red-50 text-red-700' : 'bg-gray-50 text-gray-700'}`}>
          {isHealthy && '✓ System Operational'}
          {hasFailed && '✕ Connection Failed'}
          {!isHealthy && !hasFailed && 'Checking system health...'}
        </div>
      </div>
    </div>
  )
}

export default App
