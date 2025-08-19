/**
 * Utility functions for handling favicon and icon selection
 */

/**
 * Selects the best available favicon from the icons object
 * @param {Object} icons - Icons object from search result
 * @param {string} url - URL to get favicon for (fallback)
 * @returns {string} URL of the best available icon or fallback
 */
export const getBestFavicon = (icons, url = '') => {
  if (!icons || typeof icons !== 'object' || Object.keys(icons).length === 0) {
    return getFaviconFallback(url);
  }
  
  // Priority order for icon selection (most preferred first)
  const priority = [
    'apple-touch-icon-180x180',
    'apple-touch-icon-152x152',
    'apple-touch-icon',
    'favicon-32x32',
    'favicon-16x16',
    'icon',
    'shortcut icon',
    'favicon'
  ];
  
  // Check each priority option
  for (const iconType of priority) {
    if (icons[iconType]) {
      return icons[iconType];
    }
  }
  
  // Check for any icon containing 'apple-touch-icon'
  for (const [key, value] of Object.entries(icons)) {
    if (key.toLowerCase().includes('apple-touch-icon')) {
      return value;
    }
  }
  
  // Check for any icon containing 'favicon'
  for (const [key, value] of Object.entries(icons)) {
    if (key.toLowerCase().includes('favicon')) {
      return value;
    }
  }
  
  // Fallback to the first available icon
  const firstIcon = Object.values(icons)[0];
  return firstIcon || getFaviconFallback(url);
};

/**
 * Returns a favicon fallback using external services or default
 * @param {string} url - URL to get favicon for
 * @returns {string} Fallback favicon URL
 */
export const getFaviconFallback = (url) => {
  if (url) {
    const domain = extractDomain(url);
    if (domain) {
      // Try Google's favicon service first
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    }
  }
  return getDefaultFavicon();
};

/**
 * Returns a default favicon for when no icon is available
 * @returns {string} Default icon data URI or path
 */
export const getDefaultFavicon = () => {
  // Return a simple SVG icon as data URI for fallback
  return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiByeD0iMiIgZmlsbD0iIzY2NjY2NiIvPgo8cGF0aCBkPSJNNCA2SDEyVjEwSDRWNloiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPgo=';
};

/**
 * Extracts domain from a URL
 * @param {string} url - Full URL
 * @returns {string} Domain name
 */
export const extractDomain = (url) => {
  if (!url) return '';
  
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace(/^www\./, '');
  } catch (error) {
    // Fallback for invalid URLs
    const match = url.match(/https?:\/\/(?:www\.)?([^\/]+)/);
    return match ? match[1] : url;
  }
};

/**
 * Formats a URL for display (truncates if too long)
 * @param {string} url - Full URL
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Formatted URL
 */
export const formatDisplayUrl = (url, maxLength = 50) => {
  if (!url) return '';
  
  // Remove protocol for cleaner display
  let displayUrl = url.replace(/^https?:\/\//, '');
  
  if (displayUrl.length <= maxLength) {
    return displayUrl;
  }
  
  // Truncate in the middle to preserve domain and end of path
  const domain = displayUrl.split('/')[0];
  const remaining = displayUrl.substring(domain.length);
  
  if (domain.length >= maxLength - 3) {
    return domain.substring(0, maxLength - 3) + '...';
  }
  
  const availableSpace = maxLength - domain.length - 3; // 3 for "..."
  const endPart = remaining.substring(remaining.length - Math.floor(availableSpace / 2));
  
  return domain + '...' + endPart;
};

/**
 * Handles icon loading errors by providing fallback
 * @param {Event} event - Image error event
 */
export const handleIconError = (event) => {
  const currentSrc = event.target.src;
  const imgElement = event.target;
  
  // If already showing default, don't try again
  if (currentSrc.includes('data:image/svg+xml')) {
    return;
  }
  
  // Try to extract domain from the current page URL for favicon service
  const resultCard = imgElement.closest('[role="article"]');
  if (resultCard) {
    const linkElement = resultCard.querySelector('a[href]');
    if (linkElement) {
      const url = linkElement.href;
      const domain = extractDomain(url);
      if (domain && !currentSrc.includes('google.com/s2/favicons')) {
        // Try Google's favicon service as fallback
        imgElement.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        return;
      }
    }
  }
  
  // Final fallback to default icon
  imgElement.src = getDefaultFavicon();
  imgElement.onerror = null; // Prevent infinite loop
};
