/**
 * Denni Coworker Frontend API Client
 * Connects to the dynamic-agents FastAPI backend.
 */

const API_BASE = '/v1';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // fallback to status text
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // Health & Ready
  async getHealth() {
    const res = await fetch('/health');
    return handleResponse(res);
  },

  async getReady() {
    const res = await fetch('/ready');
    return handleResponse(res);
  },

  // Runs
  async listRuns(limit = 20) {
    const res = await fetch(`${API_BASE}/runs?limit=${limit}`);
    return handleResponse(res);
  },

  async respondToConversation(messages) {
    const res = await fetch(`${API_BASE}/conversation/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    });
    return handleResponse(res);
  },

  async createRun({ text, files = [], company_id = null, case_id = null, metadata = {} }) {
    const res = await fetch(`${API_BASE}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, files, company_id, case_id, metadata }),
    });
    return handleResponse(res);
  },

  async getRun(runId) {
    const res = await fetch(`${API_BASE}/runs/${runId}`);
    return handleResponse(res);
  },

  async resumeRun(runId, { resume_token, new_request = '', files = [] }) {
    const res = await fetch(`${API_BASE}/runs/${runId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_token, new_request, files }),
    });
    return handleResponse(res);
  },

  // Multimodal File & Image Upload
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  // Knowledge / RAG
  async uploadKnowledgeDoc(file, companyId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (companyId) {
      formData.append('company_id', companyId);
    }
    const res = await fetch(`${API_BASE}/knowledge/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async getKnowledgeDocuments(companyId = null) {
    const url = companyId
      ? `${API_BASE}/knowledge/documents?company_id=${encodeURIComponent(companyId)}`
      : `${API_BASE}/knowledge/documents`;
    const res = await fetch(url);
    return handleResponse(res);
  },

  async searchKnowledge(query, companyId = null) {
    const url = companyId
      ? `${API_BASE}/knowledge/search?query=${encodeURIComponent(query)}&company_id=${encodeURIComponent(companyId)}`
      : `${API_BASE}/knowledge/search?query=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    return handleResponse(res);
  },

  async ingestDirectory(directory, companyId = null) {
    const res = await fetch(`${API_BASE}/knowledge/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory, company_id: companyId }),
    });
    return handleResponse(res);
  },

  // Agents Registry
  async getAgentsRegistry() {
    const res = await fetch(`${API_BASE}/agents/registry`);
    return handleResponse(res);
  },

  // Configuration / Setup
  async getConfig() {
    const res = await fetch(`${API_BASE}/config`);
    return handleResponse(res);
  },

  async updateConfig(payload) {
    const res = await fetch(`${API_BASE}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async testConfig(payload) {
    const res = await fetch(`${API_BASE}/config/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Cases
  async listCases() {
    const res = await fetch(`${API_BASE}/cases`);
    return handleResponse(res);
  },

  async getCase(caseId) {
    const res = await fetch(`${API_BASE}/cases/${caseId}`);
    return handleResponse(res);
  },
};
