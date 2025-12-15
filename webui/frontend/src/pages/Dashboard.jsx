import { useState, useEffect } from 'react'
import api from '../services/api'
import { Server, Cpu, HardDrive, Activity, Network } from 'lucide-react'
import LoadingScreen from '../components/LoadingScreen'

function StatCard({ title, value, icon: Icon, color = 'primary' }) {
  return (
    <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-white text-2xl font-bold mt-2">{value}</p>
        </div>
        <div className={`p-3 rounded-lg bg-${color}-600 bg-opacity-20`}>
          <Icon className={`w-6 h-6 text-${color}-500`} />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [coreSession, setCoreSession] = useState(null)
  const [greyboxService, setGreyboxService] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [sysInfo, coreInfo, serviceInfo] = await Promise.all([
        api.get('/api/system/info'),
        api.get('/api/core/session'),
        api.get('/api/services/systemd/greybox.service')
      ])

      setSystemInfo(sysInfo.data)
      setCoreSession(coreInfo.data)
      setGreyboxService(serviceInfo.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <LoadingScreen message="Loading dashboard..." />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">System overview and status</p>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="CPU Usage"
          value={`${systemInfo?.cpu_percent?.toFixed(1)}%`}
          icon={Cpu}
          color="primary"
        />
        <StatCard
          title="Memory Usage"
          value={`${systemInfo?.memory_percent?.toFixed(1)}%`}
          icon={Activity}
          color="green"
        />
        <StatCard
          title="Disk Usage"
          value={`${systemInfo?.disk_percent?.toFixed(1)}%`}
          icon={HardDrive}
          color="yellow"
        />
        <StatCard
          title="CORE Nodes"
          value={coreSession?.nodes || 0}
          icon={Network}
          color="purple"
        />
      </div>

      {/* Services Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CORE Network */}
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">CORE Network</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              coreSession?.state === 'RUNTIME'
                ? 'bg-green-500 bg-opacity-20 text-green-400'
                : 'bg-gray-500 bg-opacity-20 text-gray-400'
            }`}>
              {coreSession?.state || 'No Session'}
            </span>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Session ID:</span>
              <span className="text-white">{coreSession?.session_id || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Nodes:</span>
              <span className="text-white">{coreSession?.nodes || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Topology:</span>
              <span className="text-white">{coreSession?.file || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Greybox Service */}
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Greybox Service</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              greyboxService?.active
                ? 'bg-green-500 bg-opacity-20 text-green-400'
                : 'bg-red-500 bg-opacity-20 text-red-400'
            }`}>
              {greyboxService?.status || 'Unknown'}
            </span>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Status:</span>
              <span className="text-white">{greyboxService?.active ? 'Running' : 'Stopped'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Enabled:</span>
              <span className="text-white">{greyboxService?.enabled ? 'Yes' : 'No'}</span>
            </div>
            {greyboxService?.pid && (
              <div className="flex justify-between">
                <span className="text-gray-400">PID:</span>
                <span className="text-white">{greyboxService.pid}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">System Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Hostname:</span>
            <span className="text-white">{systemInfo?.hostname}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Platform:</span>
            <span className="text-white">{systemInfo?.platform}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">CPU Cores:</span>
            <span className="text-white">{systemInfo?.cpu_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Total Memory:</span>
            <span className="text-white">
              {(systemInfo?.memory_total / 1024 / 1024 / 1024).toFixed(2)} GB
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
