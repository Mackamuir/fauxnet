import { useState, useEffect } from 'react'
import { Globe, Lock, FileText, Plus, Trash2, RefreshCw, Settings, AlertCircle, CheckCircle, Download, Edit3, Upload, Key, FileCode, Search, FileSearch, ChevronDown } from 'lucide-react'
import {
  listVhosts,
  getStatistics,
  deleteVhost,
  getScrapeSites,
  updateScrapeSites,
  startScrape,
  downloadCACertificate,
  downloadCAKey,
  getNginxConfig,
  updateNginxConfig,
  getFileContent,
  updateFileContent,
  uploadFile,
  getVhost,
  createCustomVhost,
  getCustomVhostTemplates,
  getVhostLogs,
  getPhaseStatus,
  runSpecificPhases
} from '../services/vhosts'
import ProgressTracker from '../components/ProgressTracker'
import LoadingScreen from '../components/LoadingScreen'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'

export default function VirtualHosts() {
  const [vhosts, setVhosts] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [showStats, setShowStats] = useState(false) // Toggle for including size/file stats

  // Search filters for each section
  const [scrapedSearch, setScrapedSearch] = useState('')
  const [customSearch, setCustomSearch] = useState('')
  const [discoveredSearch, setDiscoveredSearch] = useState('')

  // Scraping modal state
  const [showScrapeModal, setShowScrapeModal] = useState(false)
  const [scrapeSites, setScrapeSites] = useState('')
  const [scraping, setScraping] = useState(false)
  const [scrapeOperationId, setScrapeOperationId] = useState(null)
  const [scrapeError, setScrapeError] = useState(null)
  const [scrapeDepth, setScrapeDepth] = useState(1)
  const [scrapePageRequisites, setScrapePageRequisites] = useState(true)

  // Advanced scraping options state
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false)
  const [advancedMode, setAdvancedMode] = useState(false)
  const [selectedPhases, setSelectedPhases] = useState([1, 2, 3, 4, 5, 6, 7])
  const [phaseStatus, setPhaseStatus] = useState([])

  // Phase definitions
  const PHASES = [
    { number: 1, name: "Generate CA", description: "Generate Certificate Authority", dependencies: [] },
    { number: 2, name: "Download websites", description: "Download website content using wget", dependencies: [1] },
    { number: 3, name: "Generate certificates", description: "Generate SSL certificates for vhosts", dependencies: [1, 2] },
    { number: 4, name: "Generate hosts", description: "Generate hosts file entries", dependencies: [2] },
    { number: 5, name: "Generate nginx configs", description: "Generate nginx configurations", dependencies: [2, 3, 4] },
    { number: 6, name: "Generate landing page", description: "Generate fauxnet.info landing page", dependencies: [3, 4, 5] },
    { number: 7, name: "Generate summary", description: "Generate sites summary file", dependencies: [2] }
  ]

  // Sites management modal
  const [showSitesModal, setShowSitesModal] = useState(false)
  const [configuredSites, setConfiguredSites] = useState([])
  const [editingSites, setEditingSites] = useState('')

  // Nginx config editor modal
  const [showNginxModal, setShowNginxModal] = useState(false)
  const [editingVhost, setEditingVhost] = useState(null)
  const [nginxConfig, setNginxConfig] = useState('')
  const [savingNginx, setSavingNginx] = useState(false)

  // File browser modal
  const [showFileBrowserModal, setShowFileBrowserModal] = useState(false)
  const [selectedVhost, setSelectedVhost] = useState(null)
  const [vhostFiles, setVhostFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [savingFile, setSavingFile] = useState(false)

  // File upload modal
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadingFile, setUploadingFile] = useState(null)
  const [uploadTargetPath, setUploadTargetPath] = useState('')
  const [uploading, setUploading] = useState(false)

  // Custom vhost creation modal
  const [showCustomVhostModal, setShowCustomVhostModal] = useState(false)
  const [customVhostName, setCustomVhostName] = useState('')
  const [customVhostTemplate, setCustomVhostTemplate] = useState('')
  const [customVhostC2Server, setCustomVhostC2Server] = useState('')
  const [customVhostIpAddress, setCustomVhostIpAddress] = useState('1.0.0.0')
  const [creatingCustomVhost, setCreatingCustomVhost] = useState(false)
  const [availableTemplates, setAvailableTemplates] = useState([])
  const [loadingTemplates, setLoadingTemplates] = useState(false)

  // Logs modal state
  const [showLogsModal, setShowLogsModal] = useState(false)
  const [logsVhost, setLogsVhost] = useState(null)
  const [logsActiveTab, setLogsActiveTab] = useState('access')
  const [accessLogs, setAccessLogs] = useState('')
  const [errorLogs, setErrorLogs] = useState('')
  const [loadingLogs, setLoadingLogs] = useState(false)

  // Load data on mount and when showStats changes
  useEffect(() => {
    loadData()
  }, [showStats])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [vhostsData, statsData] = await Promise.all([
        listVhosts(showStats), // Pass showStats to control whether to include size/file count
        getStatistics()
      ])
      setVhosts(vhostsData)
      setStatistics(statsData)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load virtual hosts')
      console.error('Error loading vhosts:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadData()
    setRefreshing(false)
  }

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true)
      const data = await getCustomVhostTemplates()
      setAvailableTemplates(data.templates)
      // Set default template to first one if available
      if (data.templates.length > 0 && !customVhostTemplate) {
        setCustomVhostTemplate(data.templates[0].name)
      }
    } catch (err) {
      console.error('Error loading templates:', err)
      alert('Failed to load templates: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoadingTemplates(false)
    }
  }

  // Load templates when modal opens
  useEffect(() => {
    if (showCustomVhostModal) {
      loadTemplates()
    }
  }, [showCustomVhostModal])

  const handleDelete = async (vhostName) => {
    if (!confirm(`Are you sure you want to delete "${vhostName}"? This action cannot be undone.`)) {
      return
    }

    try {
      await deleteVhost(vhostName)
      await loadData()
    } catch (err) {
      alert(`Failed to delete vhost: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleOpenScrapeModal = () => {
    setShowScrapeModal(true)
    setScrapeOperationId(null)
    setScrapeError(null)
    setScrapeSites('')
    setScraping(false)
  }

  // Load phase status when modal opens
  useEffect(() => {
    if (showScrapeModal) {
      loadPhaseStatus()
    }
  }, [showScrapeModal])

  const loadPhaseStatus = async () => {
    try {
      const data = await getPhaseStatus()
      setPhaseStatus(data.phases)
    } catch (error) {
      console.error('Failed to load phase status:', error)
    }
  }

  const handlePhaseToggle = (phaseNumber, checked) => {
    if (checked) {
      setSelectedPhases([...selectedPhases, phaseNumber].sort((a, b) => a - b))
    } else {
      setSelectedPhases(selectedPhases.filter(p => p !== phaseNumber))
    }
  }

  const handleRunScrape = async () => {
    const sites = scrapeSites
      .split('\n')
      .map(s => s.trim())
      .filter(s => s && !s.startsWith('#'))

    if (advancedMode) {
      // Phase-by-phase mode
      if (selectedPhases.length === 0) {
        setScrapeError('Please select at least one phase to run')
        return
      }

      // Check if phase 2 is selected and sites are provided
      if (selectedPhases.includes(2) && sites.length === 0) {
        setScrapeError('Phase 2 (Download websites) requires site URLs')
        return
      }

      try {
        setScraping(true)
        setScrapeError(null)
        const options = {
          depth: scrapeDepth,
          page_requisites: scrapePageRequisites
        }
        const result = await runSpecificPhases(
          selectedPhases,
          selectedPhases.includes(2) ? sites : null,
          options
        )
        setScrapeOperationId(result.operation_id)
      } catch (err) {
        setScrapeError(err.response?.data?.detail || err.message || 'Failed to start phase execution')
        setScraping(false)
      }
    } else {
      // Original full scrape mode
      if (sites.length === 0) {
        alert('Please enter at least one site to scrape')
        return
      }

      try {
        setScraping(true)
        setScrapeError(null)
        const options = {
          depth: scrapeDepth,
          page_requisites: scrapePageRequisites
        }
        const result = await startScrape(sites, options)
        setScrapeOperationId(result.operation_id)
      } catch (err) {
        setScrapeError(err.response?.data?.detail || err.message || 'Failed to start scraping')
        setScraping(false)
      }
    }
  }

  const handleScrapeComplete = async (data) => {
    console.log('Scraping completed:', data)
    setScraping(false)
    // Refresh vhosts list only once
    await loadData()
    // Close modal after a short delay to let user see success message
    setTimeout(() => {
      setShowScrapeModal(false)
      setScrapeOperationId(null)
    }, 2000)
  }

  const handleScrapeError = (error) => {
    console.error('Scraping error:', error)
    setScrapeError(error)
    setScraping(false)
    // Don't close modal on error so user can see the error message
  }

  const handleOpenSitesModal = async () => {
    try {
      const data = await getScrapeSites()
      setConfiguredSites(data.sites || [])
      setEditingSites(data.sites?.join('\n') || '')
      setShowSitesModal(true)
    } catch (err) {
      alert(`Failed to load configured sites: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleSaveSites = async () => {
    const sites = editingSites
      .split('\n')
      .map(s => s.trim())
      .filter(s => s && !s.startsWith('#'))

    try {
      await updateScrapeSites(sites)
      setConfiguredSites(sites)
      alert('Scrape sites updated successfully')
      setShowSitesModal(false)
    } catch (err) {
      alert(`Failed to update sites: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleDownloadCA = async () => {
    try {
      const blob = await downloadCACertificate()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'fauxnet_ca.cer'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      alert(`Failed to download CA certificate: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleDownloadCAKey = async () => {
    try {
      const blob = await downloadCAKey()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'fauxnet_ca.key'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      alert(`Failed to download CA key: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleEditNginx = async (vhostName) => {
    try {
      const data = await getNginxConfig(vhostName)
      setEditingVhost(vhostName)
      setNginxConfig(data.content)
      setShowNginxModal(true)
    } catch (err) {
      alert(`Failed to load nginx config: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleSaveNginx = async () => {
    try {
      setSavingNginx(true)
      await updateNginxConfig(editingVhost, nginxConfig)
      alert('Nginx configuration updated successfully')
      setShowNginxModal(false)
      await loadData()
    } catch (err) {
      alert(`Failed to save nginx config: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSavingNginx(false)
    }
  }

  const handleBrowseFiles = async (vhostName) => {
    try {
      const data = await getVhost(vhostName)
      setSelectedVhost(vhostName)
      setVhostFiles(data.files || [])
      setSelectedFile(null)
      setFileContent('')
      setShowFileBrowserModal(true)
    } catch (err) {
      alert(`Failed to load vhost files: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleSelectFile = async (file) => {
    try {
      const data = await getFileContent(selectedVhost, file.path)
      setSelectedFile(file)
      setFileContent(data.content)
    } catch (err) {
      alert(`Failed to load file content: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleSaveFile = async () => {
    if (!selectedFile) return

    try {
      setSavingFile(true)
      await updateFileContent(selectedVhost, selectedFile.path, fileContent)
      alert('File saved successfully')
    } catch (err) {
      alert(`Failed to save file: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSavingFile(false)
    }
  }

  const handleOpenUploadModal = (vhostName) => {
    setSelectedVhost(vhostName)
    setUploadingFile(null)
    setUploadTargetPath('')
    setShowUploadModal(true)
  }

  const handleUploadFile = async () => {
    if (!uploadingFile) {
      alert('Please select a file to upload')
      return
    }

    try {
      setUploading(true)
      const result = await uploadFile(selectedVhost, uploadingFile, uploadTargetPath)
      const location = result.path || uploadingFile.name
      alert(`File uploaded successfully to: ${location}`)
      setShowUploadModal(false)
      await loadData()
    } catch (err) {
      alert(`Failed to upload file: ${err.response?.data?.detail || err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleCreateCustomVhost = async () => {
    if (!customVhostName) {
      alert('Please enter a vhost name')
      return
    }

    if (!customVhostTemplate) {
      alert('Please select a template')
      return
    }

    if (customVhostTemplate === 'c2_redirector' && !customVhostC2Server) {
      alert('Please enter a backend C2 server URL for the redirector')
      return
    }

    try {
      setCreatingCustomVhost(true)
      await createCustomVhost(customVhostName, customVhostTemplate, customVhostC2Server || null, customVhostIpAddress || '1.0.0.0')
      alert(`Custom vhost '${customVhostName}' created successfully`)
      setShowCustomVhostModal(false)
      setCustomVhostName('')
      setCustomVhostTemplate('')
      setCustomVhostC2Server('')
      setCustomVhostIpAddress('1.0.0.0')
      await loadData()
    } catch (err) {
      alert(`Failed to create custom vhost: ${err.response?.data?.detail || err.message}`)
    } finally {
      setCreatingCustomVhost(false)
    }
  }

  const handleViewLogs = async (vhostName) => {
    setLogsVhost(vhostName)
    setShowLogsModal(true)
    setLogsActiveTab('access')
    setAccessLogs('')
    setErrorLogs('')

    // Load both logs
    await loadVhostLogs(vhostName)
  }

  const loadVhostLogs = async (vhostName) => {
    setLoadingLogs(true)
    try {
      const [accessData, errorData] = await Promise.all([
        getVhostLogs(vhostName, 'access', 100),
        getVhostLogs(vhostName, 'error', 100)
      ])
      setAccessLogs(accessData.content || 'No access logs available')
      setErrorLogs(errorData.content || 'No error logs available')
    } catch (err) {
      console.error('Error loading logs:', err)
      setAccessLogs(`Error loading access logs: ${err.response?.data?.detail || err.message}`)
      setErrorLogs(`Error loading error logs: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoadingLogs(false)
    }
  }

  const formatBytes = (bytes) => {
    if (bytes === null || bytes === undefined) return '-'
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return 'N/A'
    }
  }

  // Filter and categorize vhosts
  const scrapedVhosts = vhosts.filter(v => v.type === 'scraped' && v.name.toLowerCase().includes(scrapedSearch.toLowerCase()))
  const customVhosts = vhosts.filter(v => v.type === 'custom' && v.name.toLowerCase().includes(customSearch.toLowerCase()))
  const discoveredVhosts = vhosts.filter(v => v.type === 'discovered' && v.name.toLowerCase().includes(discoveredSearch.toLowerCase()))

  // Render a vhost table section
  const renderVhostSection = (title, vhosts, searchValue, setSearchValue, icon, color, emptyMessage) => (
    <div className="mb-8">
      <div className={`flex items-center justify-between mb-4 pb-3 border-b-2 border-${color}-500`}>
        <div className="flex items-center space-x-3">
          {icon}
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <span className={`px-2 py-1 rounded text-xs font-medium bg-${color}-500 bg-opacity-20 text-${color}-400`}>
            {vhosts.length}
          </span>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 w-64"
          />
        </div>
      </div>

      <div className="bg-dark-100 border border-dark-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-50 border-b border-dark-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Files</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">SSL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Nginx</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Modified</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-200">
              {vhosts.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center">
                    <Globe className="w-10 h-10 text-gray-600 mx-auto mb-2" />
                    <p className="text-gray-400">{emptyMessage}</p>
                  </td>
                </tr>
              ) : (
                vhosts.map((vhost) => (
                  <tr key={vhost.name} className="hover:bg-dark-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Globe className="w-4 h-4 text-gray-500 mr-2" />
                        <span className="text-white font-medium">{vhost.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-300">
                      {vhost.file_count !== null && vhost.file_count !== undefined ? vhost.file_count.toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-300">{formatBytes(vhost.size_bytes)}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {vhost.has_cert ? (
                        <span className="flex items-center text-green-400">
                          <CheckCircle className="w-4 h-4 mr-1" />Yes
                        </span>
                      ) : (
                        <span className="text-gray-500">No</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {vhost.has_nginx_config ? (
                        <span className="flex items-center text-green-400">
                          <CheckCircle className="w-4 h-4 mr-1" />Yes
                        </span>
                      ) : (
                        <span className="text-gray-500">No</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">{formatDate(vhost.modified)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {vhost.has_nginx_config && (
                          <button onClick={() => handleEditNginx(vhost.name)} className="text-blue-400 hover:text-blue-300 p-2" title="Edit Nginx Config">
                            <FileCode className="w-4 h-4" />
                          </button>
                        )}
                        <button onClick={() => handleViewLogs(vhost.name)} className="text-purple-400 hover:text-purple-300 p-2" title="View Logs">
                          <FileSearch className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleBrowseFiles(vhost.name)} className="text-yellow-400 hover:text-yellow-300 p-2" title="Browse Files">
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleOpenUploadModal(vhost.name)} className="text-green-400 hover:text-green-300 p-2" title="Upload File">
                          <Upload className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(vhost.name)} className="text-red-400 hover:text-red-300 p-2" title="Delete">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  if (loading) {
    return <LoadingScreen message="Loading virtual hosts..." />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Virtual Hosts</h1>
          <p className="text-gray-400 mt-1">Manage virtual hosts and web content</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleDownloadCA}
            className="flex items-center px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
            title="Download CA Certificate"
          >
            <Key className="w-4 h-4 mr-2" />
            CA Cert
          </button>
          <button
            onClick={handleDownloadCAKey}
            className="flex items-center px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
            title="Download CA Private Key"
          >
            <Lock className="w-4 h-4 mr-2" />
            CA Key
          </button>
          <button
            onClick={handleOpenSitesModal}
            className="flex items-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
          >
            <Settings className="w-4 h-4 mr-2" />
            Manage Sites
          </button>

          {/* Stats Toggle */}
          <div className="flex items-center px-4 py-2 bg-dark-100 border border-dark-200 rounded">
            <input
              type="checkbox"
              id="showStats"
              checked={showStats}
              onChange={(e) => setShowStats(e.target.checked)}
              className="mr-2 w-4 h-4"
              title="Show size and file count (slower for large datasets)"
            />
            <label htmlFor="showStats" className="text-sm text-gray-300 cursor-pointer select-none" title="Show size and file count (slower for large datasets)">
              Show Stats
            </label>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCustomVhostModal(true)}
            className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Custom VHost
          </button>
          <button
            onClick={handleOpenScrapeModal}
            className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
          >
            <Plus className="w-4 h-4 mr-2" />
            Scrape Sites
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && <ErrorMessage message={error} />}

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total VHosts</p>
                <p className="text-2xl font-bold text-white">{statistics.total_vhosts}</p>
              </div>
              <Globe className="w-8 h-8 text-primary-500" />
            </div>
          </div>

          <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Size</p>
                <p className="text-2xl font-bold text-white">{formatBytes(statistics.total_size_bytes)}</p>
              </div>
              <Download className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Files</p>
                <p className="text-2xl font-bold text-white">{statistics.total_files.toLocaleString()}</p>
              </div>
              <FileText className="w-8 h-8 text-yellow-500" />
            </div>
          </div>

          <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">With SSL</p>
                <p className="text-2xl font-bold text-white">{statistics.vhosts_with_certs}</p>
              </div>
              <Lock className="w-8 h-8 text-green-500" />
            </div>
          </div>

          <div className="bg-dark-100 border border-dark-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Configured</p>
                <p className="text-2xl font-bold text-white">{statistics.vhosts_with_nginx_config}</p>
              </div>
              <Settings className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Virtual Hosts Sections */}
      {vhosts.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No virtual hosts found"
          subtitle='Click "Scrape Sites" or "Create Custom Vhost" to get started'
        />
      ) : (
        <>
          {/* Scraped Sites Section */}
          {renderVhostSection(
            'Scraped Sites',
            scrapedVhosts,
            scrapedSearch,
            setScrapedSearch,
            <Download className="w-6 h-6 text-primary-500" />,
            'primary',
            'No scraped sites yet. Use "Scrape Sites" to download websites.'
          )}

          {/* Custom Sites Section */}
          {renderVhostSection(
            'Custom Sites',
            customVhosts,
            customSearch,
            setCustomSearch,
            <Plus className="w-6 h-6 text-green-500" />,
            'green',
            'No custom sites yet. Use "Create Custom Vhost" to add one.'
          )}

          {/* Discovered Sites Section */}
          {renderVhostSection(
            'Discovered Sites',
            discoveredVhosts,
            discoveredSearch,
            setDiscoveredSearch,
            <Globe className="w-6 h-6 text-blue-500" />,
            'blue',
            'No discovered sites yet. Wget may discover additional sites when span hosts is enabled during scraping.'
          )}
        </>
      )}

      {/* Scrape Sites Modal */}
      {showScrapeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Scrape Websites</h2>

              {!scrapeOperationId ? (
                // Initial form - before scraping starts
                <>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Enter URLs (one per line)
                      </label>
                      <textarea
                        value={scrapeSites}
                        onChange={(e) => setScrapeSites(e.target.value)}
                        className="w-full h-48 px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="https://example.com&#10;https://another-site.com&#10;# Comments start with #"
                        disabled={scraping}
                      />
                    </div>

                    <div className="border-t border-dark-200 pt-4">
                      <h3 className="text-sm font-medium text-gray-300 mb-3">Scraping Options</h3>
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">
                            Depth (1 = landing page only, 2+ = follow links)
                          </label>
                          <input
                            type="number"
                            min="1"
                            max="5"
                            value={scrapeDepth}
                            onChange={(e) => setScrapeDepth(parseInt(e.target.value))}
                            className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                            disabled={scraping}
                          />
                        </div>
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            id="pageRequisites"
                            checked={scrapePageRequisites}
                            onChange={(e) => setScrapePageRequisites(e.target.checked)}
                            className="mr-2"
                            disabled={scraping}
                          />
                          <label htmlFor="pageRequisites" className="text-sm text-gray-400">
                            Download page requisites (CSS, JS, images from same domain)
                          </label>
                        </div>
                        <div className="text-xs text-gray-500 mt-2 p-2 bg-dark-50 rounded">
                          <strong>Note:</strong> Each domain is scraped as a separate vhost. If you need CDN resources, add the CDN domain to the scrape list.
                        </div>
                      </div>
                    </div>

                    {/* Advanced Options Section */}
                    <div className="border-t border-dark-200 pt-4 mt-4">
                      <button
                        onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                        className="flex items-center text-sm font-medium text-gray-300 hover:text-white mb-3"
                      >
                        <ChevronDown
                          className={`w-4 h-4 mr-2 transition-transform ${
                            showAdvancedOptions ? 'rotate-180' : ''
                          }`}
                        />
                        Advanced Options
                      </button>

                      {showAdvancedOptions && (
                        <div className="bg-dark-50 border border-dark-200 rounded-lg p-4 space-y-4">
                          {/* Phase Status Visualization */}
                          <div className="mb-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-gray-400">Phase Completion Status</span>
                              <button
                                onClick={loadPhaseStatus}
                                className="text-xs text-primary-400 hover:text-primary-300"
                              >
                                <RefreshCw className="w-3 h-3 inline mr-1" />
                                Refresh
                              </button>
                            </div>
                            <div className="flex gap-1">
                              {[1, 2, 3, 4, 5, 6, 7].map(num => {
                                const phase = phaseStatus.find(p => p.phase_number === num)
                                return (
                                  <div
                                    key={num}
                                    className={`flex-1 h-2 rounded ${
                                      phase?.completed ? 'bg-green-500' : 'bg-dark-300'
                                    }`}
                                    title={`Phase ${num}: ${phase?.name || 'Unknown'} - ${
                                      phase?.completed ? 'Completed' : 'Not completed'
                                    }`}
                                  />
                                )
                              })}
                            </div>
                          </div>

                          {/* Enable Advanced Mode Toggle */}
                          <label className="flex items-center text-sm">
                            <input
                              type="checkbox"
                              checked={advancedMode}
                              onChange={(e) => setAdvancedMode(e.target.checked)}
                              className="mr-2"
                              disabled={scraping}
                            />
                            <span className="text-gray-300">Enable phase-by-phase execution</span>
                          </label>

                          {advancedMode && (
                            <>
                              <div className="text-xs text-gray-400 italic">
                                Select specific phases to run. Dependencies will be validated automatically.
                              </div>

                              {/* Phase Selection Checkboxes */}
                              <div className="space-y-2 max-h-64 overflow-y-auto">
                                {PHASES.map(phase => {
                                  const phaseInfo = phaseStatus.find(p => p.phase_number === phase.number)
                                  const isSelected = selectedPhases.includes(phase.number)

                                  return (
                                    <label
                                      key={phase.number}
                                      className="flex items-start text-sm p-2 rounded hover:bg-dark-100 cursor-pointer"
                                    >
                                      <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={(e) => handlePhaseToggle(phase.number, e.target.checked)}
                                        className="mr-3 mt-0.5"
                                        disabled={scraping}
                                      />
                                      <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                          <span className="text-white font-medium">
                                            Phase {phase.number}: {phase.name}
                                          </span>
                                          {phaseInfo?.completed && (
                                            <CheckCircle className="w-3 h-3 text-green-400" />
                                          )}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-0.5">
                                          {phase.description}
                                        </div>
                                        {phase.dependencies.length > 0 && (
                                          <div className="text-xs text-gray-600 mt-1">
                                            Requires: Phase {phase.dependencies.join(', ')}
                                          </div>
                                        )}
                                      </div>
                                    </label>
                                  )
                                })}
                              </div>

                              {/* Warnings */}
                              {selectedPhases.includes(2) && (
                                <div className="bg-yellow-500 bg-opacity-10 border border-yellow-500 rounded p-2 text-xs text-yellow-300">
                                  <AlertCircle className="w-3 h-3 inline mr-1" />
                                  Phase 2 (Download websites) requires site URLs to be entered above
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {scrapeError && (
                      <div className="bg-red-500 bg-opacity-10 border border-red-500 rounded-lg p-4">
                        <div className="flex items-start">
                          <AlertCircle className="w-5 h-5 text-red-400 mr-2 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-red-400 font-medium">Failed to start scraping</p>
                            <p className="text-red-300 text-sm mt-1">{scrapeError}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      onClick={() => setShowScrapeModal(false)}
                      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                      disabled={scraping}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRunScrape}
                      disabled={
                        scraping ||
                        (advancedMode
                          ? selectedPhases.length === 0 || (selectedPhases.includes(2) && !scrapeSites.trim())
                          : !scrapeSites.trim())
                      }
                      className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded disabled:opacity-50"
                    >
                      {scraping ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Download className="w-4 h-4 mr-2" />
                          Start Scraping
                        </>
                      )}
                    </button>
                  </div>
                </>
              ) : (
                // Progress tracking - after scraping starts
                <>
                  <div className="bg-dark-50 border border-dark-200 rounded-lg p-4 mb-4">
                    <ProgressTracker
                      operationId={scrapeOperationId}
                      onComplete={handleScrapeComplete}
                      onError={handleScrapeError}
                      method="polling"
                    />
                  </div>

                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={() => setShowScrapeModal(false)}
                      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                      disabled={scraping}
                    >
                      Close
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Manage Sites Modal */}
      {showSitesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-2xl w-full">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Manage Scrape Sites</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Configured Sites (one per line)
                  </label>
                  <textarea
                    value={editingSites}
                    onChange={(e) => setEditingSites(e.target.value)}
                    className="w-full h-64 px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="https://example.com&#10;https://another-site.com&#10;# Comments start with #"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowSitesModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveSites}
                  className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Save Sites
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Nginx Config Editor Modal */}
      {showNginxModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Edit Nginx Configuration - {editingVhost}</h2>

              <div className="space-y-4">
                <div>
                  <textarea
                    value={nginxConfig}
                    onChange={(e) => setNginxConfig(e.target.value)}
                    className="w-full h-96 px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    disabled={savingNginx}
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowNginxModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                  disabled={savingNginx}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveNginx}
                  disabled={savingNginx}
                  className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded disabled:opacity-50"
                >
                  {savingNginx ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Save Config
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* File Browser Modal */}
      {showFileBrowserModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col">
            <div className="p-6 border-b border-dark-200">
              <h2 className="text-xl font-bold text-white">Browse Files - {selectedVhost}</h2>
            </div>

            <div className="flex flex-1 overflow-hidden">
              {/* File List */}
              <div className="w-1/3 border-r border-dark-200 overflow-y-auto p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-2">Files</h3>
                <div className="space-y-1">
                  {vhostFiles.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => handleSelectFile(file)}
                      className={`w-full text-left px-3 py-2 rounded text-sm ${
                        selectedFile?.path === file.path
                          ? 'bg-primary-600 text-white'
                          : 'text-gray-300 hover:bg-dark-50'
                      }`}
                    >
                      <div className="flex items-center">
                        <FileText className="w-4 h-4 mr-2" />
                        <span className="truncate">{file.path}</span>
                      </div>
                      <div className="text-xs text-gray-500 ml-6">
                        {formatBytes(file.size)}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* File Editor */}
              <div className="flex-1 flex flex-col p-4">
                {selectedFile ? (
                  <>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-400">{selectedFile.path}</h3>
                      <button
                        onClick={handleSaveFile}
                        disabled={savingFile}
                        className="flex items-center px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded disabled:opacity-50"
                      >
                        {savingFile ? (
                          <>
                            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Save
                          </>
                        )}
                      </button>
                    </div>
                    <textarea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      className="flex-1 px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={savingFile}
                    />
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <FileText className="w-12 h-12 mx-auto mb-2" />
                      <p>Select a file to edit</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-dark-200 flex justify-end">
              <button
                onClick={() => setShowFileBrowserModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* File Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-lg w-full">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Upload File - {selectedVhost}</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select File
                  </label>
                  <input
                    type="file"
                    onChange={(e) => setUploadingFile(e.target.files[0])}
                    className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    disabled={uploading}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Target Directory Path (optional)
                  </label>
                  <input
                    type="text"
                    value={uploadTargetPath}
                    onChange={(e) => setUploadTargetPath(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="e.g., images, css/vendor, js/lib"
                    disabled={uploading}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Leave empty to upload to root directory. Directories will be created automatically if they don't exist.
                  </p>
                </div>

                <div className="bg-blue-500 bg-opacity-10 border border-blue-500 rounded p-3">
                  <div className="flex items-start">
                    <AlertCircle className="w-4 h-4 text-blue-400 mr-2 mt-0.5 flex-shrink-0" />
                    <div className="text-xs text-blue-300">
                      <p className="font-medium mb-1">Examples:</p>
                      <ul className="list-disc list-inside space-y-0.5">
                        <li><code className="bg-dark-50 px-1 rounded">images</code> - Upload to images/ folder</li>
                        <li><code className="bg-dark-50 px-1 rounded">css/vendor</code> - Upload to css/vendor/ folder</li>
                        <li><code className="bg-dark-50 px-1 rounded">assets/fonts</code> - Upload to assets/fonts/ folder</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUploadFile}
                  disabled={uploading || !uploadingFile}
                  className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Upload
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Custom VHost Creation Modal */}
      {showCustomVhostModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-2xl w-full">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Create Custom Virtual Host</h2>

              <div className="space-y-4">
                {/* VHost Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Virtual Host Name
                  </label>
                  <input
                    type="text"
                    value={customVhostName}
                    onChange={(e) => setCustomVhostName(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="example.custom.com"
                    disabled={creatingCustomVhost}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Enter a valid hostname (e.g., mysite.local, custom.example.com)
                  </p>
                </div>

                {/* IP Address */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    IP Address
                  </label>
                  <input
                    type="text"
                    value={customVhostIpAddress}
                    onChange={(e) => setCustomVhostIpAddress(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="1.0.0.0"
                    disabled={creatingCustomVhost}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    IP address for the hosts file entry (defaults to 1.0.0.0)
                  </p>
                </div>

                {/* Template Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Template Type
                  </label>
                  {loadingTemplates ? (
                    <div className="text-gray-400 text-sm">Loading templates...</div>
                  ) : (
                    <>
                      <select
                        value={customVhostTemplate}
                        onChange={(e) => setCustomVhostTemplate(e.target.value)}
                        className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        disabled={creatingCustomVhost || loadingTemplates}
                      >
                        <option value="">Select a template...</option>
                        {availableTemplates.map((template) => (
                          <option key={template.name} value={template.name}>
                            {template.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            {template.source === 'custom' ? ' (Custom)' : ''}
                          </option>
                        ))}
                      </select>
                      {customVhostTemplate && availableTemplates.find(t => t.name === customVhostTemplate) && (
                        <div className="mt-2 p-3 bg-dark-50 border border-dark-200 rounded">
                          <p className="text-xs text-gray-400">
                            {availableTemplates.find(t => t.name === customVhostTemplate).description}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Templates are loaded from /opt/fauxnet/custom_vhost_templates
                  </p>
                </div>

                {/* Backend C2 Server (only for c2_redirector) */}
                {customVhostTemplate === 'c2_redirector' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Backend C2 Server URL
                    </label>
                    <input
                      type="text"
                      value={customVhostC2Server}
                      onChange={(e) => setCustomVhostC2Server(e.target.value)}
                      className="w-full px-3 py-2 bg-dark-50 border border-dark-200 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="https://backend-c2.example.com"
                      disabled={creatingCustomVhost}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter the URL of the backend C2 server to proxy traffic to
                    </p>
                  </div>
                )}

                {/* Info Box */}
                <div className="bg-blue-500 bg-opacity-10 border border-blue-500 rounded p-3">
                  <div className="flex items-start">
                    <AlertCircle className="w-5 h-5 text-blue-400 mr-2 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-blue-300">
                      <p className="font-medium mb-1">What happens when you create a custom vhost:</p>
                      <ul className="list-disc list-inside space-y-1 text-xs">
                        <li>Creates directory structure in /opt/fauxnet/vhosts_www and vhosts_config</li>
                        <li>Generates SSL certificate for the hostname</li>
                        <li>Creates nginx configuration based on your selected template</li>
                        <li>Creates hosts file entry with your specified IP address</li>
                        <li>Templates are loaded from /opt/fauxnet/custom_vhost_templates (or built-in if none found)</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowCustomVhostModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                  disabled={creatingCustomVhost}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCustomVhost}
                  disabled={creatingCustomVhost}
                  className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
                >
                  {creatingCustomVhost ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Create VHost
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Logs Viewer Modal */}
      {showLogsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-100 border border-dark-200 rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col">
            <div className="p-6 border-b border-dark-200">
              <h2 className="text-xl font-bold text-white">Logs - {logsVhost}</h2>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-dark-200">
              <button
                onClick={() => setLogsActiveTab('access')}
                className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                  logsActiveTab === 'access'
                    ? 'bg-primary-600 text-white border-b-2 border-primary-500'
                    : 'text-gray-400 hover:text-white hover:bg-dark-50'
                }`}
              >
                Access Logs
              </button>
              <button
                onClick={() => setLogsActiveTab('error')}
                className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                  logsActiveTab === 'error'
                    ? 'bg-primary-600 text-white border-b-2 border-primary-500'
                    : 'text-gray-400 hover:text-white hover:bg-dark-50'
                }`}
              >
                Error Logs
              </button>
            </div>

            {/* Logs Content */}
            <div className="flex-1 overflow-hidden p-6">
              {loadingLogs ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex items-center space-x-2 text-gray-400">
                    <RefreshCw className="w-6 h-6 animate-spin" />
                    <span>Loading logs...</span>
                  </div>
                </div>
              ) : (
                <div className="h-full overflow-y-auto">
                  <pre className="bg-dark-50 border border-dark-200 rounded p-4 text-white font-mono text-xs whitespace-pre-wrap break-words">
                    {logsActiveTab === 'access' ? accessLogs : errorLogs}
                  </pre>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 border-t border-dark-200 flex justify-between">
              <button
                onClick={() => loadVhostLogs(logsVhost)}
                disabled={loadingLogs}
                className="flex items-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loadingLogs ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={() => setShowLogsModal(false)}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
