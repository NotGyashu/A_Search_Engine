// API Service Layer
// Centralizes all API calls with consistent error handling and configuration

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:${process.env.REACT_APP_WS_PORT || '8000'}`;

// Base fetch wrapper with error handling
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    // Log error for debugging
    console.error(`API Request failed: ${url}`, error);
    throw error;
  }
};

// Search API endpoints
export const searchApi = {
  /**
   * Perform search query with AI enhancement options and filters
   * @param {string} query - Search query string
   * @param {Object} options - Search options
   * @param {number} options.limit - Number of results per page
   * @param {number} options.offset - Offset for pagination
   * @param {boolean} options.enable_ai_enhancement - Enable AI Intelligence Hub features
   * @param {boolean} options.enable_cache - Enable caching
   * @param {Array} options.content_types - Filter by content types
   * @param {Array} options.article_types - Filter by article types
   * @param {Array} options.domains - Filter by domains
   * @param {number} options.quality_score_min - Minimum quality score (0-1)
   * @param {string} options.date_range - Date range filter ('all', 'week', 'month', 'year')
   * @param {boolean} options.has_author - Filter by author presence
   * @param {boolean} options.has_table_of_contents - Filter by table of contents presence
   * @param {boolean} options.has_images - Filter by image presence
   * @returns {Promise<Object>} Enhanced search results with AI insights
   */
  search: async (query, { 
    limit = 10, 
    offset = 0, 
    enable_ai_enhancement = true, 
    enable_cache = true,
    content_types = [],
    article_types = [],
    domains = [],
    quality_score_min = 0,
    date_range = 'all',
    has_author = false,
    has_table_of_contents = false,
    has_images = false
  } = {}) => {
    const params = new URLSearchParams({
      q: query.trim(),
      limit: limit.toString(),
      offset: offset.toString(),
      enable_ai_enhancement: enable_ai_enhancement.toString(),
      enable_cache: enable_cache.toString(),
    });

    // Add filter parameters if they have values
    if (content_types.length > 0) {
      params.append('content_types', content_types.join(','));
    }
    if (article_types.length > 0) {
      params.append('article_types', article_types.join(','));
    }
    if (domains.length > 0) {
      params.append('domains', domains.join(','));
    }
    if (quality_score_min > 0) {
      params.append('quality_score_min', quality_score_min.toString());
    }
    if (date_range !== 'all') {
      params.append('date_range', date_range);
    }
    if (has_author) {
      params.append('has_author', 'true');
    }
    if (has_table_of_contents) {
      params.append('has_table_of_contents', 'true');
    }
    if (has_images) {
      params.append('has_images', 'true');
    }

    return apiRequest(`/search?${params}`);
  },

  /**
   * Get search suggestions
   * @param {string} query - Partial query string
   * @returns {Promise<Array>} Array of suggestions
   */
  suggestions: async (query) => {
    const params = new URLSearchParams({ q: query.trim() });
    return apiRequest(`/suggestions?${params}`);
  },
};

// WebSocket connection helper
export const websocketApi = {
  /**
   * Create WebSocket connection for AI summary
   * @param {string} requestId - AI summary request ID
   * @returns {WebSocket} WebSocket instance
   */
  connectAISummary: (requestId) => {
    const wsPath = process.env.REACT_APP_WS_PATH || '/api/ws/summary';
    const wsUrl = `${WS_BASE_URL}${wsPath}/${requestId}`;
    
    const ws = new WebSocket(wsUrl);
    ws.withCredentials = true;
    
    return ws;
  },
};

// Health check and utility endpoints
export const utilityApi = {
  /**
   * Check API health status
   * @returns {Promise<Object>} Health status
   */
  healthCheck: async () => {
    return apiRequest('/health');
  },

  /**
   * Get API version info
   * @returns {Promise<Object>} Version information
   */
  version: async () => {
    return apiRequest('/version');
  },
};

// Error types for consistent error handling
export class ApiError extends Error {
  constructor(message, status, endpoint) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.endpoint = endpoint;
  }
}

export class NetworkError extends Error {
  constructor(message, endpoint) {
    super(message);
    this.name = 'NetworkError';
    this.endpoint = endpoint;
  }
}

// Request timeout helper
export const withTimeout = (promise, timeoutMs = 10000) => {
  return Promise.race([
    promise,
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
    ),
  ]);
};

export default {
  searchApi,
  websocketApi,
  utilityApi,
  ApiError,
  NetworkError,
  withTimeout,
};
