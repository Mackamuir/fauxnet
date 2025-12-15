/**
 * DNS Configuration API Client
 */

import api from './api';

/**
 * Get DNS configuration status
 */
export const getDNSStatus = async () => {
  const response = await api.get('/api/dns/status');
  return response.data;
};

/**
 * Get DNS configuration settings
 */
export const getDNSConfig = async () => {
  const response = await api.get('/api/dns/config');
  return response.data;
};

/**
 * Update DNS configuration settings
 */
export const updateDNSConfig = async (config) => {
  const response = await api.put('/api/dns/config', config);
  return response.data;
};

/**
 * Get all hosts files
 */
export const getHostsFiles = async () => {
  const response = await api.get('/api/dns/hosts');
  return response.data;
};

/**
 * Get a specific hosts file
 */
export const getHostsFile = async (fileType) => {
  const response = await api.get(`/api/dns/hosts/${fileType}`);
  return response.data;
};

/**
 * Update a hosts file
 */
export const updateHostsFile = async (fileType, content) => {
  const response = await api.put(`/api/dns/hosts/${fileType}`, { content });
  return response.data;
};

/**
 * Get DNS delegations configuration
 */
export const getDelegations = async () => {
  const response = await api.get('/api/dns/delegations');
  return response.data;
};

/**
 * Update DNS delegations configuration
 */
export const updateDelegations = async (delegations) => {
  const response = await api.put('/api/dns/delegations', { delegations });
  return response.data;
};

/**
 * Get list of generated zone files
 */
export const getZones = async () => {
  const response = await api.get('/api/dns/zones');
  return response.data;
};

/**
 * Get content of a specific zone file
 */
export const getZoneContent = async (zoneName) => {
  const response = await api.get(`/api/dns/zones/${zoneName}/content`);
  return response.data;
};

/**
 * Generate DNS configuration
 */
export const generateDNSConfig = async (options = {}) => {
  const response = await api.post('/api/dns/generate', options);
  return response.data;
};

/**
 * Get generated named.conf content
 */
export const getNamedConf = async () => {
  const response = await api.get('/api/dns/named-conf');
  return response.data;
};

/**
 * Get generated hosts.named content
 */
export const getDNSHosts = async () => {
  const response = await api.get('/api/dns/dns-hosts');
  return response.data;
};

/**
 * Add a custom DNS entry
 */
export const addCustomDNSEntry = async (ipAddress, fqdn) => {
  const response = await api.post('/api/dns/custom-hosts', {
    ip_address: ipAddress,
    fqdn: fqdn
  });
  return response.data;
};

/**
 * Remove a custom DNS entry
 */
export const removeCustomDNSEntry = async (fqdn) => {
  const response = await api.delete(`/api/dns/custom-hosts/${fqdn}`);
  return response.data;
};

/**
 * Add a mail host entry
 */
export const addMailHostEntry = async (ipAddress, fqdn) => {
  const response = await api.post('/api/dns/mail-hosts', {
    ip_address: ipAddress,
    fqdn: fqdn
  });
  return response.data;
};

/**
 * Remove a mail host entry
 */
export const removeMailHostEntry = async (fqdn) => {
  const response = await api.delete(`/api/dns/mail-hosts/${fqdn}`);
  return response.data;
};
