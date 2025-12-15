import { useState, useEffect } from 'react'
import api from '../services/api'
import { Play, Square, RotateCw, Terminal, CheckCircle, XCircle, Package } from 'lucide-react'
import LoadingScreen from '../components/LoadingScreen'
import EmptyState from '../components/EmptyState'

function ServiceCard({ name, status, onAction, onViewLogs }) {
  const [loading, setLoading] = useState(false)

  const handleAction = async (action) => {
    setLoading(true)
    try {
      await onAction(name, action)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          {status?.active ? (
            <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500 mr-2" />
          )}
          <h3 className="text-lg font-semibold text-white">{name}</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          status?.active
            ? 'bg-green-500 bg-opacity-20 text-green-400'
            : 'bg-red-500 bg-opacity-20 text-red-400'
        }`}>
          {status?.status || 'Unknown'}
        </span>
      </div>

      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between">
          <span className="text-gray-400">Enabled:</span>
          <span className="text-white">{status?.enabled ? 'Yes' : 'No'}</span>
        </div>
        {status?.pid && (
          <div className="flex justify-between">
            <span className="text-gray-400">PID:</span>
            <span className="text-white">{status.pid}</span>
          </div>
        )}
        {status?.uptime && (
          <div className="flex justify-between">
            <span className="text-gray-400">Uptime:</span>
            <span className="text-white text-xs">{status.uptime}</span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => handleAction('start')}
          disabled={loading || status?.active}
          className="flex items-center justify-center px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-sm"
        >
          <Play className="w-4 h-4 mr-1" />
          Start
        </button>
        <button
          onClick={() => handleAction('stop')}
          disabled={loading || !status?.active}
          className="flex items-center justify-center px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-sm"
        >
          <Square className="w-4 h-4 mr-1" />
          Stop
        </button>
        <button
          onClick={() => handleAction('restart')}
          disabled={loading}
          className="flex items-center justify-center px-3 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-sm"
        >
          <RotateCw className="w-4 h-4 mr-1" />
          Restart
        </button>
        <button
          onClick={() => onViewLogs(name)}
          className="flex items-center justify-center px-3 py-2 bg-dark-200 hover:bg-dark-300 text-white rounded text-sm ml-auto"
        >
          <Terminal className="w-4 h-4 mr-1" />
          Logs
        </button>
      </div>
    </div>
  )
}

function LogModal({ service, logs, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-200">
          <h3 className="text-lg font-semibold text-white">{service} - Logs</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
            {logs.join('\n')}
          </pre>
        </div>
      </div>
    </div>
  )
}

export default function Services() {
  const [systemdServices, setSystemdServices] = useState({})
  const [dockerContainers, setDockerContainers] = useState([])
  const [selectedLogs, setSelectedLogs] = useState(null)
  const [loading, setLoading] = useState(true)

  const services = [
    'core-daemon.service',
  ]

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      // Fetch systemd services
      const servicePromises = services.map(service =>
        api.get(`/api/services/systemd/${service}`).catch(() => null)
      )
      const serviceResults = await Promise.all(servicePromises)

      const servicesData = {}
      serviceResults.forEach((result, index) => {
        if (result) {
          servicesData[services[index]] = result.data
        }
      })
      setSystemdServices(servicesData)

      // Fetch Docker containers
      const containersResponse = await api.get('/api/services/docker/containers?all=true')
      setDockerContainers(containersResponse.data.containers || [])
    } catch (error) {
      console.error('Failed to fetch services:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleServiceAction = async (service, action) => {
    try {
      await api.post(`/api/services/systemd/${service}/action`, { action })
      await fetchData()
    } catch (error) {
      alert(`Failed to ${action} ${service}: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleContainerAction = async (container, action) => {
    try {
      await api.post(`/api/services/docker/containers/${container}/${action}`)
      await fetchData()
    } catch (error) {
      alert(`Failed to ${action} ${container}: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleViewLogs = async (service) => {
    try {
      const response = await api.get(`/api/services/systemd/${service}/logs?lines=200`)
      setSelectedLogs({ service, logs: response.data.logs })
    } catch (error) {
      alert(`Failed to fetch logs: ${error.response?.data?.detail || error.message}`)
    }
  }

  if (loading) {
    return <LoadingScreen message="Loading services..." />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Service Management</h1>
        <p className="text-gray-400 mt-1">Control systemd services and Docker containers</p>
      </div>

      {/* Systemd Services */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Systemd Services</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {services.map(service => (
            <ServiceCard
              key={service}
              name={service}
              status={systemdServices[service]}
              onAction={handleServiceAction}
              onViewLogs={handleViewLogs}
            />
          ))}
        </div>
      </div>

      {/* Docker Containers */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Docker Containers</h2>
        {dockerContainers.length === 0 ? (
          <EmptyState
            icon={Package}
            title="No Docker containers found"
          />
        ) : (
          <div className="bg-dark-100 border border-dark-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-dark-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Image</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Ports</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-200">
                {dockerContainers.map(container => (
                  <tr key={container.id}>
                    <td className="px-6 py-4 text-sm text-white">{container.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-400">{container.image}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        container.status === 'running'
                          ? 'bg-green-500 bg-opacity-20 text-green-400'
                          : 'bg-red-500 bg-opacity-20 text-red-400'
                      }`}>
                        {container.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400">
                      {Object.keys(container.ports || {}).join(', ') || 'None'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => handleContainerAction(container.name, 'start')}
                          disabled={container.status === 'running'}
                          className="px-2 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-xs"
                        >
                          Start
                        </button>
                        <button
                          onClick={() => handleContainerAction(container.name, 'stop')}
                          disabled={container.status !== 'running'}
                          className="px-2 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-xs"
                        >
                          Stop
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Log Modal */}
      {selectedLogs && (
        <LogModal
          service={selectedLogs.service}
          logs={selectedLogs.logs}
          onClose={() => setSelectedLogs(null)}
        />
      )}
    </div>
  )
}
