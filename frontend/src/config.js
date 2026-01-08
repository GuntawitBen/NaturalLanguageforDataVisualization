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
    LIST: `${API_BASE_URL}/datasets/`,
    GET: (id) => `${API_BASE_URL}/datasets/${id}`,
    QUERY: (id) => `${API_BASE_URL}/datasets/${id}/query`,
    DELETE: (id) => `${API_BASE_URL}/datasets/${id}`,
    PREVIEW: (id) => `${API_BASE_URL}/datasets/${id}/preview`,
    STATS: (id) => `${API_BASE_URL}/datasets/${id}/stats`,
    VALIDATION_CONFIG: `${API_BASE_URL}/datasets/validation/config`,
  },

  // EDA Agent
  EDA: {
    ANALYZE: `${API_BASE_URL}/agents/eda/analyze`,
    ANALYZE_STREAM: `${API_BASE_URL}/agents/eda/analyze-stream`,
    HEALTH: `${API_BASE_URL}/agents/eda/health`,
  },

  // Health check
  HELLO: `${API_BASE_URL}/api/hello`,
};

export default {
  API_BASE_URL,
  FRONTEND_URL,
  API_ENDPOINTS,
};
