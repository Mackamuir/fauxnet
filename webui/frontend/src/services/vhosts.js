import api from './api'

// List all virtual hosts
// By default, does NOT include size_bytes and file_count for much faster performance
// Set includeStats=true to get size and file count (slower for large datasets)
export const listVhosts = async (includeStats = false) => {
  const response = await api.get('/api/vhosts/list', {
    params: { include_stats: includeStats }
  })
  return response.data
}

// Get statistics
export const getStatistics = async () => {
  const response = await api.get('/api/vhosts/statistics')
  return response.data
}

// Get specific vhost details
export const getVhost = async (vhostName) => {
  const response = await api.get(`/api/vhosts/${vhostName}`)
  return response.data
}

// Delete vhost
export const deleteVhost = async (vhostName) => {
  const response = await api.delete(`/api/vhosts/${vhostName}`)
  return response.data
}

// Get scrape sites list
export const getScrapeSites = async () => {
  const response = await api.get('/api/vhosts/scrape/sites')
  return response.data
}

// Update scrape sites list
export const updateScrapeSites = async (sites) => {
  const response = await api.put('/api/vhosts/scrape/sites', { sites })
  return response.data
}

// Start scraping process with options (returns operation_id for tracking)
export const startScrape = async (sites, options = null) => {
  const response = await api.post('/api/vhosts/scrape/start', {
    sites,
    options: options || {
      depth: 1,
      page_requisites: true
    }
  })
  return response.data
}

// Get scraping status (single request, for polling)
export const getScrapeStatus = async (operationId) => {
  const response = await api.get(`/api/vhosts/scrape/status/${operationId}`)
  return response.data
}

// Download CA certificate
export const downloadCACertificate = async () => {
  const response = await api.get('/api/vhosts/ca/certificate', {
    responseType: 'blob'
  })
  return response.data
}

// Download CA key
export const downloadCAKey = async () => {
  const response = await api.get('/api/vhosts/ca/key', {
    responseType: 'blob'
  })
  return response.data
}

// Get nginx config for a vhost
export const getNginxConfig = async (vhostName) => {
  const response = await api.get(`/api/vhosts/${vhostName}/nginx/config`)
  return response.data
}

// Update nginx config for a vhost
export const updateNginxConfig = async (vhostName, content) => {
  const response = await api.put(`/api/vhosts/${vhostName}/nginx/config`, { content })
  return response.data
}

// Get file content from a vhost
export const getFileContent = async (vhostName, filePath) => {
  const response = await api.get(`/api/vhosts/${vhostName}/files/${filePath}`)
  return response.data
}

// Update file content in a vhost
export const updateFileContent = async (vhostName, filePath, content) => {
  const response = await api.put(`/api/vhosts/${vhostName}/files/${filePath}`, { content })
  return response.data
}

// Upload file to a vhost
export const uploadFile = async (vhostName, file, targetPath = '') => {
  const formData = new FormData()
  formData.append('file', file)
  // Always append target_path (empty string if not specified)
  formData.append('target_path', targetPath)
  const response = await api.post(`/api/vhosts/${vhostName}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

// Get available custom vhost templates
export const getCustomVhostTemplates = async () => {
  const response = await api.get('/api/vhosts/custom/templates')
  return response.data
}

// Create custom vhost
export const createCustomVhost = async (vhostName, templateType, backendC2Server = null, ipAddress = '1.0.0.0') => {
  const response = await api.post('/api/vhosts/custom/create', {
    vhost_name: vhostName,
    template_type: templateType,
    backend_c2_server: backendC2Server,
    ip_address: ipAddress
  })
  return response.data
}

// Get vhost logs
export const getVhostLogs = async (vhostName, logType = 'access', lines = 100) => {
  const response = await api.get(`/api/vhosts/${vhostName}/logs/${logType}`, {
    params: { lines }
  })
  return response.data
}

// Get phase status for all scraping phases
export const getPhaseStatus = async () => {
  const response = await api.get('/api/vhosts/scrape/phases/status')
  return response.data
}

// Run specific scraping phases
export const runSpecificPhases = async (phases, sites = null, options = null) => {
  const response = await api.post('/api/vhosts/scrape/run-phases', {
    phases,
    sites,
    options: options || null
  })
  return response.data
}

// Get vhost index status
export const getIndexStatus = async () => {
  const response = await api.get('/api/vhosts/index/status')
  return response.data
}

// Manually refresh vhost index
export const refreshIndex = async (includeStats = true) => {
  const response = await api.post('/api/vhosts/index/refresh', null, {
    params: { include_stats: includeStats }
  })
  return response.data
}
