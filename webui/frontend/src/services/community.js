import api from './api'

/**
 * Community service API functions
 */

// Get overall Community service status
export const getCommunityStatus = async () => {
  const response = await api.get('/api/community/status')
  return response.data
}

// Get status of Community service on a specific node
export const getNodeStatus = async (nodeId) => {
  const response = await api.get(`/api/community/nodes/${nodeId}/status`)
  return response.data
}

// Control Community service on a node (start, stop, restart)
export const controlNodeService = async (nodeId, action) => {
  const response = await api.post(`/api/community/nodes/${nodeId}/action`, {
    node_id: nodeId,
    action: action
  })
  return response.data
}

// Get Community configuration from a node
export const getNodeConfig = async (nodeId) => {
  const response = await api.get(`/api/community/nodes/${nodeId}/config`)
  return response.data
}

// Update Community configuration on a node
export const updateNodeConfig = async (nodeId, config) => {
  const response = await api.put(`/api/community/nodes/${nodeId}/config`, {
    config: config
  })
  return response.data
}

// Get logs from Community service on a node
export const getNodeLogs = async (nodeId, lines = 100) => {
  const response = await api.get(`/api/community/nodes/${nodeId}/logs`, {
    params: { lines }
  })
  return response.data
}

// Get base Community configuration
export const getBaseConfig = async () => {
  const response = await api.get('/api/community/config/base')
  return response.data
}

// Update base Community configuration
export const updateBaseConfig = async (config) => {
  const response = await api.put('/api/community/config/base', {
    config: config
  })
  return response.data
}

// Update configuration on all nodes
export const updateAllNodesConfig = async (config) => {
  const response = await api.put('/api/community/config/all-nodes', {
    config: config
  })
  return response.data
}
