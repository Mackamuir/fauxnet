import { useState, useEffect } from 'react'
import {
  Server,
  Database,
  FileText,
  RefreshCw,
  Play,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Settings,
  Globe,
  Network,
  Edit3,
  Plus,
  Trash2,
  ChevronRight,
  Eye,
  Search
} from 'lucide-react'
import {
  getDNSStatus,
  getDNSConfig,
  getHostsFiles,
  getHostsFile,
  updateHostsFile,
  getDelegations,
  updateDelegations,
  getZones,
  getZoneContent,
  generateDNSConfig,
  getNamedConf,
  getDNSHosts,
  addCustomDNSEntry,
  removeCustomDNSEntry,
  addMailHostEntry,
  removeMailHostEntry
} from '../services/dns'
import LoadingScreen from '../components/LoadingScreen'
import ErrorMessage from '../components/ErrorMessage'

export default function DNS() {
  const [activeTab, setActiveTab] = useState('overview')
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load data on mount
  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [statusData, configData] = await Promise.all([
        getDNSStatus(),
        getDNSConfig()
      ])
      setStatus(statusData)
      setConfig(configData)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load DNS configuration')
      console.error('Error loading DNS data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    await loadData()
  }

  if (loading) {
    return <LoadingScreen message="Loading DNS configuration..." />
  }

  if (error) {
    return <ErrorMessage title="Failed to load DNS configuration" message={error} />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">DNS Configuration</h1>
          <p className="text-gray-400 mt-1">Generate and manage bind9 DNS configuration</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`bg-dark-100 rounded-lg p-4 ${
          status?.needs_regeneration
            ? 'border-2 border-yellow-500'
            : 'border border-dark-200'
        }`}>
          <div className="flex items-center gap-3">
            {status?.needs_regeneration ? (
              <AlertTriangle className="w-8 h-8 text-yellow-500" />
            ) : status?.configured ? (
              <CheckCircle className="w-8 h-8 text-green-500" />
            ) : (
              <AlertCircle className="w-8 h-8 text-yellow-500" />
            )}
            <div>
              <p className="text-sm text-gray-400">Configuration Status</p>
              <p className="text-lg font-semibold text-white">
                {status?.needs_regeneration
                  ? 'Needs Regeneration'
                  : status?.configured
                    ? 'Configured'
                    : 'Not Configured'
                }
              </p>
              {status?.needs_regeneration && (
                <p className="text-xs text-yellow-400 mt-1">
                  Config files modified
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Globe className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-400">Web Hosts</p>
              <p className="text-lg font-semibold text-white">{status?.web_hosts_count || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Server className="w-8 h-8 text-purple-500" />
            <div>
              <p className="text-sm text-gray-400">Mail Hosts</p>
              <p className="text-lg font-semibold text-white">{status?.mail_hosts_count || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-gray-400">DNS Zones</p>
              <p className="text-lg font-semibold text-white">{status?.zone_count || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-dark-100 border border-dark-200 rounded-lg">
        <div className="border-b border-dark-200">
          <nav className="flex gap-8 px-6">
            {[
              { id: 'overview', label: 'Overview', icon: Settings },
              { id: 'hosts', label: 'Hosts Files', icon: FileText },
              { id: 'delegations', label: 'Delegations', icon: Network },
              { id: 'zones', label: 'Zones', icon: Database },
              { id: 'generate', label: 'Generate', icon: Play }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-dark-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && <OverviewTab status={status} config={config} />}
          {activeTab === 'hosts' && <HostsTab onRefresh={handleRefresh} />}
          {activeTab === 'delegations' && <DelegationsTab onRefresh={handleRefresh} />}
          {activeTab === 'zones' && <ZonesTab />}
          {activeTab === 'generate' && <GenerateTab onGenerated={handleRefresh} />}
        </div>
      </div>
    </div>
  )
}

// Overview Tab
function OverviewTab({ status, config }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Configuration Paths</h2>
        <div className="space-y-2 text-sm font-mono bg-dark-200 p-4 rounded-lg border border-dark-300">
          <div className="flex justify-between">
            <span className="text-gray-400">Vhosts Config Directory:</span>
            <span className={status?.web_hosts_exists ? 'text-green-400' : 'text-red-400'}>
              {config?.vhosts_config_dir}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Mail Hosts:</span>
            <span className={status?.mail_hosts_exists ? 'text-green-400' : 'text-gray-500'}>
              {config?.mail_hosts_path || 'Not configured'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Delegations:</span>
            <span className={status?.delegations_exists ? 'text-green-400' : 'text-gray-500'}>
              {config?.delegations_path}
            </span>
          </div>
          <div className="flex justify-between border-t border-dark-300 pt-2 mt-2">
            <span className="text-gray-400">named.conf:</span>
            <span className={status?.named_conf_exists ? 'text-green-400' : 'text-gray-500'}>
              {config?.output_named_conf_path}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Zone Folder:</span>
            <span className="text-white">{config?.output_zone_folder}</span>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Status Summary</h2>
        <div className="grid grid-cols-2 gap-4">
          <StatusItem
            label="Configuration Generated"
            value={status?.configured}
            icon={status?.configured ? CheckCircle : AlertCircle}
            color={status?.configured ? 'green' : 'yellow'}
          />
          <StatusItem
            label="Web Hosts File"
            value={status?.web_hosts_exists}
            icon={status?.web_hosts_exists ? CheckCircle : AlertCircle}
            color={status?.web_hosts_exists ? 'green' : 'red'}
          />
          <StatusItem
            label="Mail Hosts File"
            value={status?.mail_hosts_exists}
            icon={status?.mail_hosts_exists ? CheckCircle : AlertCircle}
            color={status?.mail_hosts_exists ? 'green' : 'gray'}
          />
          <StatusItem
            label="Delegations File"
            value={status?.delegations_exists}
            icon={status?.delegations_exists ? CheckCircle : AlertCircle}
            color={status?.delegations_exists ? 'green' : 'yellow'}
          />
        </div>
      </div>
    </div>
  )
}

function StatusItem({ label, value, icon: Icon, color }) {
  const colors = {
    green: 'text-green-400 bg-green-500 bg-opacity-20 border border-green-500 border-opacity-30',
    yellow: 'text-yellow-400 bg-yellow-500 bg-opacity-20 border border-yellow-500 border-opacity-30',
    red: 'text-red-400 bg-red-500 bg-opacity-20 border border-red-500 border-opacity-30',
    gray: 'text-gray-400 bg-dark-200 border border-dark-300'
  }

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg ${colors[color]}`}>
      <Icon className="w-5 h-5" />
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs opacity-75">{value ? 'Available' : 'Not found'}</p>
      </div>
    </div>
  )
}

// Hosts Tab
function HostsTab({ onRefresh }) {
  const [hostsFiles, setHostsFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState(null)
  const [editContent, setEditContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showAddCustom, setShowAddCustom] = useState(false)
  const [newIp, setNewIp] = useState('')
  const [newFqdn, setNewFqdn] = useState('')
  const [adding, setAdding] = useState(false)
  const [showAddMail, setShowAddMail] = useState(false)
  const [newMailIp, setNewMailIp] = useState('')
  const [newMailFqdn, setNewMailFqdn] = useState('')
  const [addingMail, setAddingMail] = useState(false)

  useEffect(() => {
    loadHostsFiles()
  }, [])

  const loadHostsFiles = async () => {
    try {
      setLoading(true)
      const data = await getHostsFiles()
      setHostsFiles(data)
    } catch (err) {
      console.error('Error loading hosts files:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = async (fileType) => {
    try {
      const data = await getHostsFile(fileType)
      const content = data.entries.map(e => `${e.ip_address} ${e.fqdn}`).join('\n')
      setEditContent(content)
      setSelectedFile(fileType)
      setEditing(true)
    } catch (err) {
      alert(`Failed to load file: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await updateHostsFile(selectedFile, editContent)
      await loadHostsFiles()
      await onRefresh()
      setEditing(false)
      setSelectedFile(null)
    } catch (err) {
      alert(`Failed to save file: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleAddCustomEntry = async () => {
    if (!newIp || !newFqdn) {
      alert('Please provide both IP address and FQDN')
      return
    }

    try {
      setAdding(true)
      await addCustomDNSEntry(newIp, newFqdn)
      await loadHostsFiles()
      await onRefresh()
      setShowAddCustom(false)
      setNewIp('')
      setNewFqdn('')
    } catch (err) {
      alert(`Failed to add entry: ${err.response?.data?.detail || err.message}`)
    } finally {
      setAdding(false)
    }
  }

  const handleRemoveCustomEntry = async (fqdn) => {
    if (!confirm(`Remove DNS entry for ${fqdn}?`)) {
      return
    }

    try {
      await removeCustomDNSEntry(fqdn)
      await loadHostsFiles()
      await onRefresh()
    } catch (err) {
      alert(`Failed to remove entry: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleAddMailEntry = async () => {
    if (!newMailIp || !newMailFqdn) {
      alert('Please provide both IP address and FQDN')
      return
    }

    try {
      setAddingMail(true)
      await addMailHostEntry(newMailIp, newMailFqdn)
      await loadHostsFiles()
      await onRefresh()
      setShowAddMail(false)
      setNewMailIp('')
      setNewMailFqdn('')
    } catch (err) {
      alert(`Failed to add mail host: ${err.response?.data?.detail || err.message}`)
    } finally {
      setAddingMail(false)
    }
  }

  const handleRemoveMailEntry = async (fqdn) => {
    if (!confirm(`Remove mail host entry for ${fqdn}?`)) {
      return
    }

    try {
      await removeMailHostEntry(fqdn)
      await loadHostsFiles()
      await onRefresh()
    } catch (err) {
      alert(`Failed to remove mail host: ${err.response?.data?.detail || err.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex items-center space-x-2 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin text-primary-500" />
          <span>Loading hosts files...</span>
        </div>
      </div>
    )
  }

  if (editing) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Editing {selectedFile} hosts file</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 border border-dark-300 rounded-lg hover:bg-dark-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full h-96 font-mono text-sm p-4 border border-dark-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="IP_ADDRESS FQDN (one per line)"
        />
        <p className="text-sm text-gray-400">
          Format: Each line should contain an IP address followed by a fully qualified domain name (FQDN).
          Lines starting with # are treated as comments.
        </p>
      </div>
    )
  }

  const customHostsFile = hostsFiles.find(f => f.name === 'custom')
  const mailHostsFile = hostsFiles.find(f => f.name === 'mail')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Hosts Files</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddCustom(!showAddCustom)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Plus className="w-4 h-4" />
            Add Custom Entry
          </button>
          <button
            onClick={() => setShowAddMail(!showAddMail)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            <Plus className="w-4 h-4" />
            Add Mail Host
          </button>
          <button
            onClick={loadHostsFiles}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-dark-300 rounded-lg hover:bg-dark-200"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {showAddCustom && (
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3">Add Custom DNS Entry</h4>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">IP Address</label>
              <input
                type="text"
                value={newIp}
                onChange={(e) => setNewIp(e.target.value)}
                placeholder="192.168.1.10"
                className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">FQDN</label>
              <input
                type="text"
                value={newFqdn}
                onChange={(e) => setNewFqdn(e.target.value)}
                placeholder="server.example.com"
                className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded-lg text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleAddCustomEntry}
              disabled={adding}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
            >
              {adding ? 'Adding...' : 'Add Entry'}
            </button>
            <button
              onClick={() => {
                setShowAddCustom(false)
                setNewIp('')
                setNewFqdn('')
              }}
              className="px-4 py-2 border border-dark-300 rounded-lg hover:bg-dark-200 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {showAddMail && (
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3">Add Mail Host Entry</h4>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">IP Address</label>
              <input
                type="text"
                value={newMailIp}
                onChange={(e) => setNewMailIp(e.target.value)}
                placeholder="192.168.1.20"
                className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">FQDN</label>
              <input
                type="text"
                value={newMailFqdn}
                onChange={(e) => setNewMailFqdn(e.target.value)}
                placeholder="mail.example.com"
                className="w-full px-3 py-2 bg-dark-200 border border-dark-300 rounded-lg text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleAddMailEntry}
              disabled={addingMail}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
            >
              {addingMail ? 'Adding...' : 'Add Mail Host'}
            </button>
            <button
              onClick={() => {
                setShowAddMail(false)
                setNewMailIp('')
                setNewMailFqdn('')
              }}
              className="px-4 py-2 border border-dark-300 rounded-lg hover:bg-dark-200 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {customHostsFile && customHostsFile.entries.length > 0 && (
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3">Custom DNS Entries</h4>
          <div className="space-y-2">
            {customHostsFile.entries.map((entry, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-dark-200 rounded">
                <span className="font-mono text-sm">
                  <span className="text-blue-400">{entry.ip_address}</span>
                  {' → '}
                  <span className="text-white">{entry.fqdn}</span>
                </span>
                <button
                  onClick={() => handleRemoveCustomEntry(entry.fqdn)}
                  className="p-1 text-red-400 hover:bg-red-500 hover:bg-opacity-20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {mailHostsFile && mailHostsFile.entries.length > 0 && (
        <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3">Mail Host Entries</h4>
          <div className="space-y-2">
            {mailHostsFile.entries.map((entry, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-dark-200 rounded">
                <span className="font-mono text-sm">
                  <span className="text-purple-400">{entry.ip_address}</span>
                  {' → '}
                  <span className="text-white">{entry.fqdn}</span>
                </span>
                <button
                  onClick={() => handleRemoveMailEntry(entry.fqdn)}
                  className="p-1 text-red-400 hover:bg-red-500 hover:bg-opacity-20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {hostsFiles.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No hosts files found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {hostsFiles.filter(f => f.name !== 'custom' && f.name !== 'mail').map(file => (
            <div key={file.name} className="border border-dark-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <h4 className="font-semibold">{file.name}</h4>
                    <span className="text-sm text-gray-400">({file.line_count} entries)</span>
                  </div>
                  <p className="text-sm text-gray-400 font-mono mt-1">{file.path}</p>
                </div>
                <button
                  onClick={() => handleEdit(file.name)}
                  className="flex items-center gap-2 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Delegations Tab
function DelegationsTab({ onRefresh }) {
  const [delegations, setDelegations] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editData, setEditData] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadDelegations()
  }, [])

  const loadDelegations = async () => {
    try {
      setLoading(true)
      const data = await getDelegations()
      setDelegations(data)
    } catch (err) {
      console.error('Error loading delegations:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = () => {
    setEditData(JSON.parse(JSON.stringify(delegations)))
    setEditing(true)
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await updateDelegations(editData)
      await loadDelegations()
      await onRefresh()
      setEditing(false)
    } catch (err) {
      alert(`Failed to save delegations: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const addForwardDelegation = () => {
    setEditData({
      ...editData,
      forward: [...editData.forward, { domain_or_network: '', nameservers: [] }]
    })
  }

  const addReverseDelegation = () => {
    setEditData({
      ...editData,
      reverse: [...editData.reverse, { domain_or_network: '', nameservers: [] }]
    })
  }

  const addNameserver = () => {
    setEditData({
      ...editData,
      nameservers: [...editData.nameservers, { hostname: '', ip_address: '' }]
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex items-center space-x-2 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin text-primary-500" />
          <span>Loading delegations...</span>
        </div>
      </div>
    )
  }

  if (editing) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Editing Delegations</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 border border-dark-300 rounded-lg hover:bg-dark-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>

        {/* Forward Delegations */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold">Forward Delegations (Domains)</h4>
            <button
              onClick={addForwardDelegation}
              className="flex items-center gap-1 text-sm text-primary-400 hover:text-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
          <div className="space-y-2">
            {editData.forward.map((del, idx) => (
              <DelegationEditor
                key={idx}
                delegation={del}
                onChange={(updated) => {
                  const newForward = [...editData.forward]
                  newForward[idx] = updated
                  setEditData({ ...editData, forward: newForward })
                }}
                onRemove={() => {
                  setEditData({
                    ...editData,
                    forward: editData.forward.filter((_, i) => i !== idx)
                  })
                }}
                placeholder="example.com"
              />
            ))}
          </div>
        </div>

        {/* Reverse Delegations */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold">Reverse Delegations (Networks)</h4>
            <button
              onClick={addReverseDelegation}
              className="flex items-center gap-1 text-sm text-primary-400 hover:text-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
          <div className="space-y-2">
            {editData.reverse.map((del, idx) => (
              <DelegationEditor
                key={idx}
                delegation={del}
                onChange={(updated) => {
                  const newReverse = [...editData.reverse]
                  newReverse[idx] = updated
                  setEditData({ ...editData, reverse: newReverse })
                }}
                onRemove={() => {
                  setEditData({
                    ...editData,
                    reverse: editData.reverse.filter((_, i) => i !== idx)
                  })
                }}
                placeholder="192.168.1"
              />
            ))}
          </div>
        </div>

        {/* Nameservers */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold">Nameserver IP Addresses</h4>
            <button
              onClick={addNameserver}
              className="flex items-center gap-1 text-sm text-primary-400 hover:text-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
          <div className="space-y-2">
            {editData.nameservers.map((ns, idx) => (
              <NameserverEditor
                key={idx}
                nameserver={ns}
                onChange={(updated) => {
                  const newNS = [...editData.nameservers]
                  newNS[idx] = updated
                  setEditData({ ...editData, nameservers: newNS })
                }}
                onRemove={() => {
                  setEditData({
                    ...editData,
                    nameservers: editData.nameservers.filter((_, i) => i !== idx)
                  })
                }}
              />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">DNS Delegations</h3>
        <div className="flex gap-2">
          <button
            onClick={loadDelegations}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-dark-300 rounded-lg hover:bg-dark-200"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={handleEdit}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Edit3 className="w-4 h-4" />
            Edit
          </button>
        </div>
      </div>

      <DelegationsDisplay delegations={delegations} />
    </div>
  )
}

function DelegationsDisplay({ delegations }) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="font-semibold mb-2">Forward Delegations ({delegations.forward.length})</h4>
        {delegations.forward.length === 0 ? (
          <p className="text-sm text-gray-400">No forward delegations configured</p>
        ) : (
          <div className="space-y-1">
            {delegations.forward.map((del, idx) => (
              <div key={idx} className="text-sm bg-dark-200 p-2 rounded border border-dark-200">
                <span className="font-mono text-primary-400">{del.domain_or_network}</span>
                {' → '}
                <span className="font-mono text-gray-300">{del.nameservers.join(', ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h4 className="font-semibold mb-2">Reverse Delegations ({delegations.reverse.length})</h4>
        {delegations.reverse.length === 0 ? (
          <p className="text-sm text-gray-400">No reverse delegations configured</p>
        ) : (
          <div className="space-y-1">
            {delegations.reverse.map((del, idx) => (
              <div key={idx} className="text-sm bg-dark-200 p-2 rounded border border-dark-200">
                <span className="font-mono text-purple-600">{del.domain_or_network}</span>
                {' → '}
                <span className="font-mono text-gray-300">{del.nameservers.join(', ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h4 className="font-semibold mb-2">Nameserver IPs ({delegations.nameservers.length})</h4>
        {delegations.nameservers.length === 0 ? (
          <p className="text-sm text-gray-400">No nameserver IPs configured</p>
        ) : (
          <div className="space-y-1">
            {delegations.nameservers.map((ns, idx) => (
              <div key={idx} className="text-sm bg-dark-200 p-2 rounded border border-dark-200">
                <span className="font-mono text-green-600">{ns.hostname}</span>
                {' → '}
                <span className="font-mono text-gray-300">{ns.ip_address}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DelegationEditor({ delegation, onChange, onRemove, placeholder }) {
  return (
    <div className="flex gap-2 items-start">
      <input
        type="text"
        value={delegation.domain_or_network}
        onChange={(e) => onChange({ ...delegation, domain_or_network: e.target.value })}
        placeholder={placeholder}
        className="flex-1 px-3 py-2 border border-dark-300 rounded-lg text-sm font-mono"
      />
      <input
        type="text"
        value={delegation.nameservers.join(' ')}
        onChange={(e) => onChange({ ...delegation, nameservers: e.target.value.split(/\s+/).filter(Boolean) })}
        placeholder="ns1.example.com ns2.example.com"
        className="flex-1 px-3 py-2 border border-dark-300 rounded-lg text-sm font-mono"
      />
      <button
        onClick={onRemove}
        className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}

function NameserverEditor({ nameserver, onChange, onRemove }) {
  return (
    <div className="flex gap-2 items-start">
      <input
        type="text"
        value={nameserver.hostname}
        onChange={(e) => onChange({ ...nameserver, hostname: e.target.value })}
        placeholder="ns1.example.com"
        className="flex-1 px-3 py-2 border border-dark-300 rounded-lg text-sm font-mono"
      />
      <input
        type="text"
        value={nameserver.ip_address}
        onChange={(e) => onChange({ ...nameserver, ip_address: e.target.value })}
        placeholder="192.168.1.1"
        className="flex-1 px-3 py-2 border border-dark-300 rounded-lg text-sm font-mono"
      />
      <button
        onClick={onRemove}
        className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}

// Zones Tab
function ZonesTab() {
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedZone, setSelectedZone] = useState(null)
  const [zoneContent, setZoneContent] = useState('')
  const [viewingZone, setViewingZone] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadZones()
  }, [])

  const loadZones = async () => {
    try {
      setLoading(true)
      const data = await getZones()
      setZones(data)
    } catch (err) {
      console.error('Error loading zones:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleViewZone = async (zone) => {
    try {
      const data = await getZoneContent(zone.name)
      setZoneContent(data.content)
      setSelectedZone(zone)
      setViewingZone(true)
    } catch (err) {
      alert(`Failed to load zone: ${err.response?.data?.detail || err.message}`)
    }
  }

  // Filter zones by search term
  const filteredZones = zones.filter(zone =>
    zone.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Categorize zones
  const rootZones = filteredZones.filter(z => z.type === 'root')
  const forwardZones = filteredZones.filter(z => z.type === 'forward')
  const reverseZones = filteredZones.filter(z => z.type === 'reverse')

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex items-center space-x-2 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin text-primary-500" />
          <span>Loading DNS zones...</span>
        </div>
      </div>
    )
  }

  if (viewingZone) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">{selectedZone.name}.zone</h3>
            <p className="text-sm text-gray-400">
              Type: {selectedZone.type} | Records: {selectedZone.record_count} | Size: {(selectedZone.size_bytes / 1024).toFixed(2)} KB
            </p>
          </div>
          <button
            onClick={() => setViewingZone(false)}
            className="px-4 py-2 border border-dark-300 rounded-lg hover:bg-dark-200"
          >
            Close
          </button>
        </div>
        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-96 overflow-y-auto">
          {zoneContent}
        </pre>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Generated DNS Zones</h3>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search zones..."
              className="pl-10 pr-4 py-2 bg-dark-200 border border-dark-300 rounded-lg text-sm w-64 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={loadZones}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-dark-300 rounded-lg hover:bg-dark-200"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {zones.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Database className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No zones found</p>
          <p className="text-sm mt-1">Generate DNS configuration to create zones</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Root Zones */}
          {rootZones.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-5 h-5 text-green-500" />
                <h4 className="font-semibold text-white">Root Zones ({rootZones.length})</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {rootZones.map(zone => (
                  <ZoneCard key={zone.name} zone={zone} onClick={() => handleViewZone(zone)} />
                ))}
              </div>
            </div>
          )}

          {/* Forward Zones */}
          {forwardZones.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-5 h-5 text-blue-500" />
                <h4 className="font-semibold text-white">Forward Zones ({forwardZones.length})</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {forwardZones.map(zone => (
                  <ZoneCard key={zone.name} zone={zone} onClick={() => handleViewZone(zone)} />
                ))}
              </div>
            </div>
          )}

          {/* Reverse Zones */}
          {reverseZones.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-5 h-5 text-purple-500" />
                <h4 className="font-semibold text-white">Reverse Zones ({reverseZones.length})</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {reverseZones.map(zone => (
                  <ZoneCard key={zone.name} zone={zone} onClick={() => handleViewZone(zone)} />
                ))}
              </div>
            </div>
          )}

          {/* No results from search */}
          {filteredZones.length === 0 && searchTerm && (
            <div className="text-center py-12 text-gray-400">
              <Search className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No zones found matching "{searchTerm}"</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Zone Card Component
function ZoneCard({ zone, onClick }) {
  const typeColors = {
    root: 'text-green-500',
    forward: 'text-blue-500',
    reverse: 'text-purple-500'
  }

  return (
    <div
      className="border border-dark-200 rounded-lg p-4 hover:border-primary-500 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Database className={`w-4 h-4 flex-shrink-0 ${typeColors[zone.type] || 'text-gray-500'}`} />
            <h4 className="font-semibold font-mono text-sm truncate">{zone.name}</h4>
          </div>
          <div className="flex flex-col gap-1 text-xs text-gray-400">
            <div className="flex items-center gap-2">
              <span className="capitalize">{zone.type}</span>
              <span>•</span>
              <span>{zone.record_count} records</span>
            </div>
            <span>{(zone.size_bytes / 1024).toFixed(1)} KB</span>
          </div>
        </div>
        <Eye className="w-4 h-4 text-gray-400 flex-shrink-0 ml-2" />
      </div>
    </div>
  )
}

// Generate Tab
function GenerateTab({ onGenerated }) {
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [forceOverwrite, setForceOverwrite] = useState(false)
  const [quietMode, setQuietMode] = useState(false)

  const handleGenerate = async () => {
    if (!confirm('Generate DNS configuration? This will generate bind9 configuration natively in Python and may take some time.')) {
      return
    }

    try {
      setGenerating(true)
      setResult(null)
      const data = await generateDNSConfig({
        force_overwrite: forceOverwrite,
        quiet_mode: quietMode
      })
      setResult(data)
      if (data.success) {
        await onGenerated()
      }
    } catch (err) {
      setResult({
        success: false,
        zones_created: 0,
        hosts_processed: 0,
        hosts_skipped: 0,
        errors: [err.response?.data?.detail || err.message]
      })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Generate DNS Configuration</h3>
        <p className="text-gray-400 mb-4">
          This will generate bind9 DNS configuration natively in Python, including
          named.conf, zone files, and DNS hosts file.
        </p>

        <div className="space-y-3 mb-6">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={forceOverwrite}
              onChange={(e) => setForceOverwrite(e.target.checked)}
              className="rounded border-dark-300"
            />
            <span className="text-sm">Force overwrite existing configuration</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={quietMode}
              onChange={(e) => setQuietMode(e.target.checked)}
              className="rounded border-dark-300"
            />
            <span className="text-sm">Quiet mode (suppress warnings)</span>
          </label>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Generate Configuration
            </>
          )}
        </button>
      </div>

      {result && (
        <div className={`border rounded-lg p-4 ${result.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-start gap-3">
            {result.success ? (
              <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className={`font-semibold mb-2 ${result.success ? 'text-green-900' : 'text-red-900'}`}>
                {result.message || (result.success ? 'Generation Successful' : 'Generation Failed')}
              </h4>

              <div className="grid grid-cols-3 gap-4 mb-3">
                <div>
                  <p className="text-sm font-medium">Zones Created</p>
                  <p className="text-2xl font-bold">{result.zones_created}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Hosts Processed</p>
                  <p className="text-2xl font-bold">{result.hosts_processed}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Hosts Skipped</p>
                  <p className="text-2xl font-bold">{result.hosts_skipped}</p>
                </div>
              </div>

              {result.warnings && result.warnings.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm font-medium mb-1">Warnings:</p>
                  <ul className="text-sm space-y-1">
                    {result.warnings.slice(0, 10).map((warning, idx) => (
                      <li key={idx} className="text-yellow-800">• {warning}</li>
                    ))}
                    {result.warnings.length > 10 && (
                      <li className="text-yellow-600">... and {result.warnings.length - 10} more</li>
                    )}
                  </ul>
                </div>
              )}

              {result.errors && result.errors.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm font-medium mb-1">Errors:</p>
                  <ul className="text-sm space-y-1">
                    {result.errors.map((error, idx) => (
                      <li key={idx} className="text-red-800">• {error}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.output_files && result.output_files.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-1">Output Files:</p>
                  <ul className="text-sm font-mono space-y-1">
                    {result.output_files.map((file, idx) => (
                      <li key={idx} className="text-green-800">✓ {file}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
