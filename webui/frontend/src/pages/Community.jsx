import { useState, useEffect } from 'react'
import { Play, Square, RotateCw, Settings, Terminal, CheckCircle, XCircle, Users, Globe, RefreshCw } from 'lucide-react'
import * as communityApi from '../services/community'
import LoadingScreen from '../components/LoadingScreen'
import EmptyState from '../components/EmptyState'

function NodeCard({ node, onAction, onViewConfig, onViewLogs }) {
  const [loading, setLoading] = useState(false)

  const handleAction = async (action) => {
    setLoading(true)
    try {
      await onAction(node.node_id, action)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          {node.is_running ? (
            <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500 mr-2" />
          )}
          <h3 className="text-lg font-semibold text-white">{node.node_name}</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          node.is_running
            ? 'bg-green-500 bg-opacity-20 text-green-400'
            : 'bg-red-500 bg-opacity-20 text-red-400'
        }`}>
          {node.is_running ? 'Running' : 'Stopped'}
        </span>
      </div>

      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between">
          <span className="text-gray-400">Node ID:</span>
          <span className="text-white">{node.node_id}</span>
        </div>
        {node.pid && (
          <div className="flex justify-between">
            <span className="text-gray-400">PID:</span>
            <span className="text-white">{node.pid}</span>
          </div>
        )}
        {node.uptime && (
          <div className="flex justify-between">
            <span className="text-gray-400">Uptime:</span>
            <span className="text-white">{node.uptime}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-400">Config:</span>
          <span className="text-white text-xs">{node.config_path}</span>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => handleAction('start')}
          disabled={loading || node.is_running}
          className="flex items-center justify-center px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded text-sm"
        >
          <Play className="w-4 h-4 mr-1" />
          Start
        </button>
        <button
          onClick={() => handleAction('stop')}
          disabled={loading || !node.is_running}
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
          onClick={() => onViewConfig(node.node_id)}
          className="flex items-center justify-center px-3 py-2 bg-dark-200 hover:bg-dark-300 text-white rounded text-sm"
        >
          <Settings className="w-4 h-4 mr-1" />
          Config
        </button>
        <button
          onClick={() => onViewLogs(node.node_id)}
          className="flex items-center justify-center px-3 py-2 bg-dark-200 hover:bg-dark-300 text-white rounded text-sm"
        >
          <Terminal className="w-4 h-4 mr-1" />
          Logs
        </button>
      </div>
    </div>
  )
}

function ConfigModal({ nodeId, config, onClose, onSave }) {
  const [editedConfig, setEditedConfig] = useState(config)
  const [saving, setSaving] = useState(false)
  const isBaseConfig = nodeId === 'base'

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(nodeId, editedConfig)
      onClose()
    } catch (error) {
      alert(`Failed to save configuration: ${error.response?.data?.detail || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const addTarget = () => {
    const target = prompt('Enter target IP address:')
    if (target) {
      const probability = prompt('Enter probability (optional, leave empty for equal weight):')
      const newTargets = [...editedConfig.Targets]
      if (probability && probability.trim() !== '') {
        newTargets.push({ [target]: parseInt(probability) })
      } else {
        newTargets.push(target)
      }
      setEditedConfig({ ...editedConfig, Targets: newTargets })
    }
  }

  const removeTarget = (index) => {
    const newTargets = editedConfig.Targets.filter((_, i) => i !== index)
    setEditedConfig({ ...editedConfig, Targets: newTargets })
  }

  const addAction = () => {
    const action = prompt('Enter action (browse, ping, PortScan, HTTPEnum, HTTPSpider, SMBEnum):')
    if (action) {
      const probability = prompt('Enter probability (optional, leave empty for equal weight):')
      const newActions = [...(editedConfig.Actions || [])]
      if (probability && probability.trim() !== '') {
        newActions.push({ [action]: parseInt(probability) })
      } else {
        newActions.push(action)
      }
      setEditedConfig({ ...editedConfig, Actions: newActions })
    }
  }

  const removeAction = (index) => {
    const newActions = editedConfig.Actions.filter((_, i) => i !== index)
    setEditedConfig({ ...editedConfig, Actions: newActions })
  }

  const formatTarget = (target) => {
    if (typeof target === 'string') return target
    const key = Object.keys(target)[0]
    return `${key} (${target[key]}%)`
  }

  const formatAction = (action) => {
    if (typeof action === 'string') return action
    const key = Object.keys(action)[0]
    return `${key} (${action[key]}%)`
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-200">
          <h3 className="text-lg font-semibold text-white">
            {isBaseConfig ? 'Base Community Configuration' : `Community Configuration - Node ${nodeId}`}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* Enable/Disable */}
          <div className="space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={editedConfig.Enable}
                onChange={(e) => setEditedConfig({ ...editedConfig, Enable: e.target.checked })}
                className="rounded"
              />
              <span className="text-white">Enable Community Service</span>
            </label>
          </div>

          {/* Targets */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-white font-semibold">Targets</h4>
              <button
                onClick={addTarget}
                className="px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white rounded text-sm"
              >
                Add Target
              </button>
            </div>
            <div className="space-y-2">
              {editedConfig.Targets?.map((target, index) => (
                <div key={index} className="flex items-center justify-between bg-dark-200 p-2 rounded">
                  <span className="text-white">{formatTarget(target)}</span>
                  <button
                    onClick={() => removeTarget(index)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-white font-semibold">Actions</h4>
              <button
                onClick={addAction}
                className="px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white rounded text-sm"
              >
                Add Action
              </button>
            </div>
            <div className="space-y-2">
              {editedConfig.Actions?.map((action, index) => (
                <div key={index} className="flex items-center justify-between bg-dark-200 p-2 rounded">
                  <span className="text-white">{formatAction(action)}</span>
                  <button
                    onClick={() => removeAction(index)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Sleep Configuration */}
          <div className="space-y-2">
            <h4 className="text-white font-semibold">Sleep Configuration</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Min (seconds)</label>
                <input
                  type="number"
                  value={editedConfig.Sleep?.Min || 30}
                  onChange={(e) => setEditedConfig({
                    ...editedConfig,
                    Sleep: { ...editedConfig.Sleep, Min: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded text-white"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Max (seconds)</label>
                <input
                  type="number"
                  value={editedConfig.Sleep?.Max || 120}
                  onChange={(e) => setEditedConfig({
                    ...editedConfig,
                    Sleep: { ...editedConfig.Sleep, Max: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded text-white"
                />
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 p-4 border-t border-dark-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-dark-200 hover:bg-dark-300 text-white rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 text-white rounded"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  )
}

function LogModal({ nodeId, logs, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-200">
          <h3 className="text-lg font-semibold text-white">Community Logs - Node {nodeId}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
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

function BulkUpdateResultsModal({ results, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-200">
          <h3 className="text-lg font-semibold text-white">Bulk Update Results</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          <div className="mb-4">
            <p className="text-white font-semibold mb-2">{results.message}</p>
            <div className="flex gap-4 text-sm">
              <span className="text-green-400">Success: {results.success_count}</span>
              <span className="text-red-400">Failed: {results.fail_count}</span>
              <span className="text-gray-400">Total: {results.total_nodes}</span>
            </div>
          </div>
          <div className="space-y-2">
            {results.results?.map((result, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-3 rounded ${
                  result.success ? 'bg-green-500 bg-opacity-10' : 'bg-red-500 bg-opacity-10'
                }`}
              >
                <span className="text-white">
                  {result.node_name} ({result.node_id})
                </span>
                {result.success ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400" />
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 p-4 border-t border-dark-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Community() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedConfig, setSelectedConfig] = useState(null)
  const [selectedLogs, setSelectedLogs] = useState(null)
  const [bulkUpdateResults, setBulkUpdateResults] = useState(null)
  const [baseConfigMode, setBaseConfigMode] = useState(false)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const data = await communityApi.getCommunityStatus()
      setStatus(data)
    } catch (error) {
      console.error('Failed to fetch Community status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleNodeAction = async (nodeId, action) => {
    try {
      await communityApi.controlNodeService(nodeId, action)
      await fetchStatus()
    } catch (error) {
      alert(`Failed to ${action} node ${nodeId}: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleViewConfig = async (nodeId) => {
    try {
      const config = await communityApi.getNodeConfig(nodeId)
      setSelectedConfig({ nodeId, config })
    } catch (error) {
      alert(`Failed to fetch configuration: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleSaveConfig = async (nodeId, config) => {
    await communityApi.updateNodeConfig(nodeId, config)
    await fetchStatus()
  }

  const handleViewLogs = async (nodeId) => {
    try {
      const response = await communityApi.getNodeLogs(nodeId, 200)
      setSelectedLogs({ nodeId, logs: response.logs })
    } catch (error) {
      alert(`Failed to fetch logs: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleViewBaseConfig = async () => {
    try {
      const config = await communityApi.getBaseConfig()
      setSelectedConfig({ nodeId: 'base', config })
      setBaseConfigMode(true)
    } catch (error) {
      alert(`Failed to fetch base configuration: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleSaveBaseConfig = async (nodeId, config) => {
    await communityApi.updateBaseConfig(config)
    alert('Base configuration updated successfully')
  }

  const handleBulkUpdate = async () => {
    try {
      const config = await communityApi.getBaseConfig()
      if (confirm(`Apply base configuration to all ${status.total_nodes} nodes?`)) {
        const results = await communityApi.updateAllNodesConfig(config)
        setBulkUpdateResults(results)
        await fetchStatus()
      }
    } catch (error) {
      alert(`Failed to update all nodes: ${error.response?.data?.detail || error.message}`)
    }
  }

  if (loading) {
    return <LoadingScreen message="Loading Community services..." />
  }

  if (!status?.session_active) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Community Service Management</h1>
          <p className="text-gray-400 mt-1">Manage Community services across CORE nodes</p>
        </div>
        <EmptyState
          icon={XCircle}
          title="No Active CORE Session"
          subtitle="Start a CORE session to manage Community services"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Community Service Management</h1>
          <p className="text-gray-400 mt-1">Manage Community services across CORE nodes</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleViewBaseConfig}
            className="flex items-center px-4 py-2 bg-dark-200 hover:bg-dark-300 text-white rounded"
          >
            <Globe className="w-4 h-4 mr-2" />
            Base Config
          </button>
          <button
            onClick={handleBulkUpdate}
            disabled={!status?.session_active || status?.total_nodes === 0}
            className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Update All Nodes
          </button>
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Nodes</p>
              <p className="text-2xl font-bold text-white">{status.total_nodes}</p>
            </div>
            <Users className="w-8 h-8 text-primary-400" />
          </div>
        </div>
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Running</p>
              <p className="text-2xl font-bold text-green-400">{status.running_nodes}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
        </div>
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Stopped</p>
              <p className="text-2xl font-bold text-red-400">{status.total_nodes - status.running_nodes}</p>
            </div>
            <XCircle className="w-8 h-8 text-red-400" />
          </div>
        </div>
      </div>

      {/* Node Cards */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Community Nodes</h2>
        {status.nodes.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No Community nodes found in the current session"
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {status.nodes.map(node => (
              <NodeCard
                key={node.node_id}
                node={node}
                onAction={handleNodeAction}
                onViewConfig={handleViewConfig}
                onViewLogs={handleViewLogs}
              />
            ))}
          </div>
        )}
      </div>

      {/* Config Modal */}
      {selectedConfig && (
        <ConfigModal
          nodeId={selectedConfig.nodeId}
          config={selectedConfig.config}
          onClose={() => {
            setSelectedConfig(null)
            setBaseConfigMode(false)
          }}
          onSave={baseConfigMode ? handleSaveBaseConfig : handleSaveConfig}
        />
      )}

      {/* Log Modal */}
      {selectedLogs && (
        <LogModal
          nodeId={selectedLogs.nodeId}
          logs={selectedLogs.logs}
          onClose={() => setSelectedLogs(null)}
        />
      )}

      {/* Bulk Update Results Modal */}
      {bulkUpdateResults && (
        <BulkUpdateResultsModal
          results={bulkUpdateResults}
          onClose={() => setBulkUpdateResults(null)}
        />
      )}
    </div>
  )
}
