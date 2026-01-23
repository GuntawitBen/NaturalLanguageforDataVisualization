/**
 * Application Configuration
 * Centralizes all environment-specific settings
 */

// Get API base URL from environment variable or use default
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Frontend URL (for redirects)
export const FRONTEND_URL = import.meta.env.VITE_FRONTEND_URL || 'http://localhost:5173';

// API Endpoints
export const API_ENDPOINTS = {
  // Auth
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login`,
    LOGOUT: `${API_BASE_URL}/auth/logout`,
    REGISTER: `${API_BASE_URL}/auth/register`,
    GOOGLE_LOGIN: `${API_BASE_URL}/auth/google/login`,
    ME: `${API_BASE_URL}/auth/me`,
  },

  // Datasets
  DATASETS: {
    UPLOAD: `${API_BASE_URL}/datasets/upload`,
    UPLOAD_TEMP: `${API_BASE_URL}/datasets/upload-temp`,
    FINALIZE: `${API_BASE_URL}/datasets/finalize`,
    CLEANUP_TEMP: `${API_BASE_URL}/datasets/cleanup-temp`,
    PREVIEW_TEMP: `${API_BASE_URL}/datasets/preview-temp`,
    LIST: `${API_BASE_URL}/datasets/`,
    GET: (id) => `${API_BASE_URL}/datasets/${id}`,
    QUERY: (id) => `${API_BASE_URL}/datasets/${id}/query`,
    DELETE: (id) => `${API_BASE_URL}/datasets/${id}`,
    PREVIEW: (id) => `${API_BASE_URL}/datasets/${id}/preview`,
    STATS: (id) => `${API_BASE_URL}/datasets/${id}/stats`,
    VALIDATION_CONFIG: `${API_BASE_URL}/datasets/validation/config`,
  },

  // Cleaning Agent
  CLEANING: {
    START_SESSION: `${API_BASE_URL}/agents/cleaning/start-session`,
    APPLY_OPERATION: `${API_BASE_URL}/agents/cleaning/apply-operation`,
    CONFIRM_OPERATION: `${API_BASE_URL}/agents/cleaning/confirm-operation`,
    UNDO_LAST: `${API_BASE_URL}/agents/cleaning/undo-last`,
    GET_SESSION: (id) => `${API_BASE_URL}/agents/cleaning/session/${id}`,
    GET_RECOMMENDATION: (id) => `${API_BASE_URL}/agents/cleaning/session/${id}/recommendation`,
    HEALTH: `${API_BASE_URL}/agents/cleaning/health`,
  },

  // Text-to-SQL Agent
  TEXT_TO_SQL: {
    START_SESSION: `${API_BASE_URL}/agents/text-to-sql/start-session`,
    CHAT: `${API_BASE_URL}/agents/text-to-sql/chat`,
    GET_SESSION: (id) => `${API_BASE_URL}/agents/text-to-sql/session/${id}`,
    END_SESSION: (id) => `${API_BASE_URL}/agents/text-to-sql/session/${id}`,
    HISTORY: `${API_BASE_URL}/agents/text-to-sql/history`,
    HISTORY_BY_DATASET: (datasetId) => `${API_BASE_URL}/agents/text-to-sql/history?dataset_id=${datasetId}`,
    GET_HISTORY: (id) => `${API_BASE_URL}/agents/text-to-sql/history/${id}`,
    RESUME_SESSION: (id) => `${API_BASE_URL}/agents/text-to-sql/history/${id}/resume`,
    DELETE_HISTORY: (id) => `${API_BASE_URL}/agents/text-to-sql/history/${id}`,
  },

  // Health check
  HELLO: `${API_BASE_URL}/api/hello`,
};

export default {
  API_BASE_URL,
  FRONTEND_URL,
  API_ENDPOINTS,
};
