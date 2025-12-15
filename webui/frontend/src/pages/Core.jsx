import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { Play, Trash2, Network, FileText, Loader2 } from 'lucide-react'
import LoadingScreen from '../components/LoadingScreen'
import EmptyState from '../components/EmptyState'

export default function Core() {
  const [session, setSession] = useState(null)
  const [topologies, setTopologies] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingTopology, setLoadingTopology] = useState(false)
  const [loadProgress, setLoadProgress] = useState(null)
  const [daemonLogs, setDaemonLogs] = useState([])
  const eventSourceRef = useRef(null)
  const logContainerRef = useRef(null)

  useEffect(() => {
    fetchData()

    // Check if there's an active loading task in localStorage
    const activeTaskId = localStorage.getItem('core_loading_task_id')
    if (activeTaskId) {
      reconnectToLoadingTask(activeTaskId)
    }

    const interval = setInterval(fetchData, 5000)
    return () => {
      clearInterval(interval)
      // Clean up EventSource on unmount (but don't clear localStorage)
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // Auto-scroll logs to bottom when new messages arrive
  useEffect(() => {
    if (logContainerRef.current && loadProgress?.logs?.length > 0) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [loadProgress?.logs?.length])

  const reconnectToLoadingTask = async (taskId) => {
    try {
      // Show reconnecting state
      setLoadingTopology(true)
      setLoadProgress({ status: 'reconnecting', progress: 0, message: 'Reconnecting to loading task...' })

      // First check if task still exists
      const progressResponse = await api.get(`/api/core/load/progress/${taskId}`)
      const progress = progressResponse.data

      // If task is still in progress, reconnect
      if (progress.status !== 'completed' && progress.status !== 'error') {
        setLoadProgress(progress)
        connectToSSE(taskId)
      } else if (progress.status === 'completed') {
        // Task completed while we were away, show completion and clean up
        setLoadProgress(progress)
        localStorage.removeItem('core_loading_task_id')
        setTimeout(() => {
          setLoadingTopology(false)
          setLoadProgress(null)
          fetchData()
        }, 2000)
      } else {
        // Task errored, clean up
        localStorage.removeItem('core_loading_task_id')
        setLoadingTopology(false)
        setLoadProgress(null)
      }
    } catch (error) {
      // Task not found or error, clean up
      console.error('Failed to reconnect to loading task:', error)
      localStorage.removeItem('core_loading_task_id')
      setLoadingTopology(false)
      setLoadProgress(null)
    }
  }

  const connectToSSE = (taskId) => {
    // Close existing EventSource if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    // Create EventSource for SSE
    const token = localStorage.getItem('token')
    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/core/load/stream/${taskId}?token=${token}`
    )
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      const progress = JSON.parse(event.data)
      setLoadProgress(progress)

      // If completed or errored, close connection and refresh
      if (progress.status === 'completed') {
        eventSource.close()
        eventSourceRef.current = null
        setLoadingTopology(false)
        localStorage.removeItem('core_loading_task_id')
        setTimeout(() => {
          setLoadProgress(null)
          fetchData()
        }, 2000) // Show success message for 2 seconds
      } else if (progress.status === 'error') {
        eventSource.close()
        eventSourceRef.current = null
        setLoadingTopology(false)
        localStorage.removeItem('core_loading_task_id')
        alert(`Failed to load topology: ${progress.error}`)
        setLoadProgress(null)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      eventSource.close()
      eventSourceRef.current = null
      setLoadingTopology(false)
      localStorage.removeItem('core_loading_task_id')
      setLoadProgress(null)
      alert('Connection to server lost. Please check if topology loaded successfully.')
    }
  }

  const fetchData = async () => {
    try {
      const [sessionResponse, topologiesResponse, logsResponse] = await Promise.all([
        api.get('/api/core/session'),
        api.get('/api/core/topologies'),
        api.get('/api/core/daemon/logs?lines=6')
      ])

      setSession(sessionResponse.data)
      setTopologies(topologiesResponse.data.topologies || [])
      setDaemonLogs(logsResponse.data.logs || [])
    } catch (error) {
      console.error('Failed to fetch CORE data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadTopology = async (file) => {
    if (!confirm(`Load topology from ${file}?`)) return

    try {
      setLoadingTopology(true)
      setLoadProgress({ status: 'starting', progress: 0, message: 'Starting...' })

      // Start topology loading
      const response = await api.post('/api/core/load', null, { params: { xml_file: file } })
      const taskId = response.data.task_id

      // Persist task ID so we can reconnect after navigation
      localStorage.setItem('core_loading_task_id', taskId)

      // Connect to SSE stream
      connectToSSE(taskId)

    } catch (error) {
      setLoadingTopology(false)
      setLoadProgress(null)
      alert(`Failed to start topology loading: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleDeleteSession = async (sessionId) => {
    if (!confirm(`Delete session ${sessionId}?`)) return

    try {
      await api.delete(`/api/core/sessions/${sessionId}`)
      alert('Session deleted successfully')
      await fetchData()
    } catch (error) {
      alert(`Failed to delete session: ${error.response?.data?.detail || error.message}`)
    }
  }

  if (loading) {
    return <LoadingScreen message="Loading CORE network..." />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">CORE Network Emulator</h1>
        <p className="text-gray-400 mt-1">Manage network topology sessions</p>
      </div>

      {/* Current Session */}
      <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Current Session</h2>
          {session?.session_id && !loadingTopology && (
            <button
              onClick={() => handleDeleteSession(session.session_id)}
              className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Session
            </button>
          )}
        </div>

        {loadingTopology && loadProgress ? (
          <div className="py-8">
            <div className="max-w-xl mx-auto">
              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">Loading Topology</span>
                  <span className="text-sm text-gray-400">{loadProgress.progress}%</span>
                </div>
                <div className="w-full bg-dark-50 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all duration-300 ${
                      loadProgress.status === 'error' ? 'bg-red-500' : 'bg-primary-600'
                    }`}
                    style={{ width: `${loadProgress.progress}%` }}
                  ></div>
                </div>
              </div>

              {/* Status Message */}
              <div className="flex items-center justify-center space-x-3 py-4">
                {loadProgress.status !== 'error' && loadProgress.status !== 'completed' && (
                  <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
                )}
                <div className="text-center">
                  <p className={`font-medium ${
                    loadProgress.status === 'error' ? 'text-red-400' :
                    loadProgress.status === 'completed' ? 'text-green-400' :
                    'text-white'
                  }`}>
                    {loadProgress.message}
                  </p>
                  {loadProgress.status === 'completed' && loadProgress.session_id && (
                    <p className="text-sm text-gray-400 mt-1">Session ID: {loadProgress.session_id}</p>
                  )}
                </div>
              </div>

              {/* Status Steps */}
              <div className="mt-6 space-y-2">
                <div className={`flex items-center space-x-2 ${loadProgress.progress >= 10 ? 'text-primary-400' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${loadProgress.progress >= 10 ? 'bg-primary-500' : 'bg-gray-600'}`}></div>
                  <span className="text-sm">Validating topology file</span>
                </div>
                <div className={`flex items-center space-x-2 ${loadProgress.progress >= 30 ? 'text-primary-400' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${loadProgress.progress >= 30 ? 'bg-primary-500' : 'bg-gray-600'}`}></div>
                  <span className="text-sm">Loading topology into CORE</span>
                </div>
                <div className={`flex items-center space-x-2 ${loadProgress.progress >= 40 ? 'text-primary-400' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${loadProgress.progress >= 40 ? 'bg-primary-500' : 'bg-gray-600'}`}></div>
                  <span className="text-sm">Creating network nodes and links</span>
                </div>
                <div className={`flex items-center space-x-2 ${loadProgress.progress >= 80 ? 'text-primary-400' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${loadProgress.progress >= 80 ? 'bg-primary-500' : 'bg-gray-600'}`}></div>
                  <span className="text-sm">Extracting session information</span>
                </div>
                <div className={`flex items-center space-x-2 ${loadProgress.progress >= 100 ? 'text-primary-400' : 'text-gray-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${loadProgress.progress >= 100 ? 'bg-primary-500' : 'bg-gray-600'}`}></div>
                  <span className="text-sm">Verifying session</span>
                </div>
              </div>

              {/* CORE Daemon Logs */}
              {daemonLogs.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-400">CORE Daemon Logs</span>
                    <span className="text-xs text-gray-500">Latest {daemonLogs.length} entries</span>
                  </div>
                  <div
                    ref={logContainerRef}
                    className="bg-dark-50 rounded-lg p-3 max-h-32 overflow-y-auto font-mono text-xs"
                  >
                    {daemonLogs.map((log, index) => (
                      <div
                        key={index}
                        className={`py-0.5 ${
                          log.priority <= '3' ? 'text-red-400' :
                          log.priority === '4' ? 'text-yellow-400' :
                          'text-gray-300'
                        }`}
                      >
                        {log.timestamp && (
                          <span className="text-gray-600 mr-2">
                            {new Date(parseInt(log.timestamp) / 1000).toLocaleTimeString()}
                          </span>
                        )}
                        {log.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : session?.session_id ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-dark-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <Network className="w-5 h-5 text-primary-500 mr-2" />
                <span className="text-gray-400 text-sm">Session ID</span>
              </div>
              <p className="text-2xl font-bold text-white">{session.session_id}</p>
            </div>

            <div className="bg-dark-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  session.state === 'RUNTIME' ? 'bg-green-500' : 'bg-gray-500'
                }`} />
                <span className="text-gray-400 text-sm">State</span>
              </div>
              <p className="text-2xl font-bold text-white">{session.state}</p>
            </div>

            <div className="bg-dark-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <Network className="w-5 h-5 text-purple-500 mr-2" />
                <span className="text-gray-400 text-sm">Nodes</span>
              </div>
              <p className="text-2xl font-bold text-white">{session.nodes}</p>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={Network}
            title="No active CORE session"
            subtitle="Load a topology to start a new session"
          />
        )}

        {session?.file && (
          <div className="mt-4 pt-4 border-t border-dark-200">
            <div className="flex items-center text-sm">
              <FileText className="w-4 h-4 text-gray-400 mr-2" />
              <span className="text-gray-400">Topology File:</span>
              <span className="text-white ml-2">{session.file}</span>
            </div>
          </div>
        )}
      </div>

      {/* Available Topologies */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Available Topologies</h2>
        {topologies.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No topology files found"
            subtitle="Place CORE XML topology files in /opt/fauxnet/topologies/"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {topologies.map((topology) => {
              const fileName = topology.split('/').pop()
              const isActive = session?.file === topology

              return (
                <div
                  key={topology}
                  className={`bg-dark-100 border rounded-lg p-4 ${
                    isActive ? 'border-primary-500' : 'border-dark-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center flex-1 min-w-0">
                      <FileText className="w-5 h-5 text-primary-500 mr-2 flex-shrink-0" />
                      <span className="text-white font-medium truncate">{fileName}</span>
                    </div>
                    {isActive && (
                      <span className="ml-2 px-2 py-1 bg-primary-600 bg-opacity-20 text-primary-400 text-xs rounded-full flex-shrink-0">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mb-3 truncate">{topology}</p>
                  <button
                    onClick={() => handleLoadTopology(topology)}
                    disabled={isActive || loadingTopology}
                    className="w-full flex items-center justify-center px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-sm"
                  >
                    {loadingTopology ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        {isActive ? 'Currently Loaded' : 'Load Topology'}
                      </>
                    )}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="bg-blue-500 bg-opacity-10 border border-blue-500 rounded-lg p-4">
        <p className="text-blue-400 text-sm">
          <strong>Note:</strong> Loading a topology will create a new CORE session.
          Make sure to delete any existing session before loading a new topology to avoid conflicts.
        </p>
      </div>
    </div>
  )
}
