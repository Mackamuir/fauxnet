import { useState, useEffect, useRef } from 'react'
import { CheckCircle, AlertCircle, RefreshCw, Clock } from 'lucide-react'
import { getScrapeStatus } from '../services/vhosts'

/**
 * ProgressTracker component - displays real-time progress of scraping operations
 *
 * @param {string} operationId - The operation ID to track
 * @param {function} onComplete - Callback when operation completes successfully
 * @param {function} onError - Callback when operation fails
 * @param {string} method - Tracking method: 'polling' (default) or 'sse'
 */
export default function ProgressTracker({ operationId, onComplete, onError, method = 'polling' }) {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const callbackCalledRef = useRef(false)

  // Polling method
  useEffect(() => {
    if (!operationId || method !== 'polling') return

    // Reset callback flag when operationId changes
    callbackCalledRef.current = false
    let hasCompleted = false

    const pollInterval = setInterval(async () => {
      // Don't poll if already completed
      if (hasCompleted) {
        clearInterval(pollInterval)
        return
      }

      try {
        const data = await getScrapeStatus(operationId)
        setProgress(data)

        if (data.status === 'completed' && !callbackCalledRef.current) {
          hasCompleted = true
          callbackCalledRef.current = true
          clearInterval(pollInterval)
          onComplete?.(data)
        } else if (data.status === 'error' && !callbackCalledRef.current) {
          hasCompleted = true
          callbackCalledRef.current = true
          setError(data.error)
          clearInterval(pollInterval)
          onError?.(data.error)
        }
      } catch (err) {
        if (!callbackCalledRef.current) {
          console.error('Polling error:', err)
          hasCompleted = true
          callbackCalledRef.current = true
          setError(err.response?.data?.detail || err.message || 'Failed to fetch progress')
          clearInterval(pollInterval)
          onError?.(err.message)
        }
      }
    }, 1000) // Poll every second

    return () => {
      clearInterval(pollInterval)
    }
  }, [operationId, method, onComplete, onError])

  // SSE method (Note: EventSource doesn't support custom headers easily, so we use polling by default)
  // For SSE with auth, you'd need a library like eventsource or fetch with streaming
  useEffect(() => {
    if (!operationId || method !== 'sse') return

    // Get auth token
    const token = localStorage.getItem('token')
    if (!token) {
      setError('Authentication token not found')
      return
    }

    const url = `/api/vhosts/scrape/progress/${operationId}`

    // Use fetch with streaming instead of EventSource to support auth headers
    const controller = new AbortController()

    const connectSSE = async () => {
      try {
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { value, done } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonData = line.slice(6)
              try {
                const data = JSON.parse(jsonData)
                setProgress(data)

                if (data.status === 'completed') {
                  reader.cancel()
                  onComplete?.(data)
                } else if (data.status === 'error') {
                  setError(data.error)
                  reader.cancel()
                  onError?.(data.error)
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e)
              }
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('SSE error:', err)
          setError('Connection lost')
          onError?.('Connection lost')
        }
      }
    }

    connectSSE()

    return () => {
      controller.abort()
    }
  }, [operationId, method, onComplete, onError])

  // Calculate elapsed time
  useEffect(() => {
    if (!progress?.started_at) return

    const interval = setInterval(() => {
      const startTime = new Date(progress.started_at)
      const now = new Date()
      const elapsed = Math.floor((now - startTime) / 1000)
      setElapsedTime(elapsed)
    }, 1000)

    return () => clearInterval(interval)
  }, [progress?.started_at])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getPhasePercentage = () => {
    if (!progress) return 0
    return progress.total_phases > 0
      ? (progress.current_phase / progress.total_phases) * 100
      : 0
  }

  const getSubPhasePercentage = () => {
    if (!progress || progress.current_phase_total === 0) return 0
    return (progress.current_phase_progress / progress.current_phase_total) * 100
  }

  if (error) {
    return (
      <div className="bg-red-500 bg-opacity-10 border border-red-500 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-red-400 mr-3 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-red-400 font-medium">Scraping Failed</p>
            <p className="text-red-300 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!progress) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-6 h-6 text-primary-500 animate-spin mr-2" />
        <span className="text-gray-400">Connecting to progress tracker...</span>
      </div>
    )
  }

  const isCompleted = progress.status === 'completed'
  const isRunning = progress.status === 'running'

  return (
    <div className="space-y-4">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {isRunning && <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />}
          {isCompleted && <CheckCircle className="w-5 h-5 text-green-500" />}
          <div>
            <p className="text-white font-medium">
              {isCompleted ? 'Scraping Completed!' : 'Scraping in Progress...'}
            </p>
            <p className="text-gray-400 text-sm">
              Phase {progress.current_phase} of {progress.total_phases}: {progress.current_phase_name}
            </p>
          </div>
        </div>
        <div className="flex items-center text-gray-400 text-sm">
          <Clock className="w-4 h-4 mr-1" />
          {formatTime(elapsedTime)}
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div>
        <div className="flex justify-between text-sm text-gray-400 mb-1">
          <span>Overall Progress</span>
          <span>{Math.round(getPhasePercentage())}%</span>
        </div>
        <div className="w-full h-3 bg-dark-50 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-600 to-primary-500 transition-all duration-300 ease-out"
            style={{ width: `${getPhasePercentage()}%` }}
          />
        </div>
      </div>

      {/* Sub-phase Progress Bar (if available) */}
      {progress.current_phase_total > 0 && (
        <div>
          <div className="flex justify-between text-sm text-gray-400 mb-1">
            <span>Current Phase</span>
            <span>
              {progress.current_phase_progress} / {progress.current_phase_total}
            </span>
          </div>
          <div className="w-full h-2 bg-dark-50 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-blue-500 transition-all duration-300 ease-out"
              style={{ width: `${getSubPhasePercentage()}%` }}
            />
          </div>
        </div>
      )}

      {/* Recent Messages */}
      {progress.messages && progress.messages.length > 0 && (
        <div className="bg-dark-50 border border-dark-200 rounded-lg p-3">
          <h4 className="text-sm font-medium text-gray-400 mb-2">Recent Activity</h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {progress.messages.slice().reverse().map((msg, idx) => (
              <div key={idx} className="text-xs text-gray-300 font-mono flex items-start">
                <span className="text-gray-500 mr-2 whitespace-nowrap">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
                <span className="flex-1">{msg.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Success Message */}
      {isCompleted && (
        <div className="bg-green-500 bg-opacity-10 border border-green-500 rounded-lg p-3">
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 text-green-400 mr-2" />
            <p className="text-green-400 font-medium">
              Scraping completed successfully in {formatTime(elapsedTime)}!
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
