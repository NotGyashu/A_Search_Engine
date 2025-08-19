import React from 'react';
import { motion } from 'framer-motion';
import { getBestFavicon, extractDomain, formatDisplayUrl, handleIconError } from '../utils/iconHelper';
import { formatDate, formatRelativeDate } from '../utils/dateHelper';

const ResultCard = ({ result, index = 0 }) => {
  const { 
    title, 
    url, 
    canonical_url,
    content_preview, 
    description,
    text_snippet,
    icons, 
    categories,
    content_categories, // Backend sends this field
    published_date,
    modified_date,
    quality_score,
    relevance_score,
    domain_score,
    domain,
    author,
    author_info,
    article_type,
    content_type,
    table_of_contents,
    semantic_info,
    structured_data_type,
    chunk_count,
    word_count,
    images,
    has_images,
    image_count,
    keywords
  } = result;

  // Use categories or content_categories (for backend compatibility)
  const resultCategories = categories || content_categories || [];
  
  // Use the provided domain or extract from URL
  const displayDomain = domain || extractDomain(url);
  const faviconUrl = getBestFavicon(icons, url);
  const displayUrl = formatDisplayUrl(canonical_url || url, 60);
  
  // Use content_preview (which is enhanced in the new backend) or fallback to text_snippet
  const snippet = content_preview || text_snippet || description || '';
  
  // Format publication date with fallback
  const formattedDate = formatDate(published_date);
  const relativeDate = formatRelativeDate(published_date);
  
  // Enhanced date display logic
  const shouldShowDate = published_date || ['news.ycombinator.com', 'reddit.com', 'twitter.com', 'github.com'].includes(displayDomain);
  const fallbackDate = !published_date && shouldShowDate ? 'Recent' : null;

  // Calculate reading time from word count
  const readingTime = word_count ? Math.ceil(word_count / 200) : null; // Average 200 words per minute

  // Enhanced author display
  const authorDisplay = author || (author_info?.name) || (author_info?.display_name);
  
  // Content type display
  const contentTypeDisplay = content_type || article_type || structured_data_type;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-xl hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-750 transition-all duration-300"
      role="article"
      aria-labelledby={`result-title-${index}`}
    >
      {/* Header with favicon, domain, and enhanced metadata */}
      <div className="flex items-center mb-3">
        <div className="flex-shrink-0 mr-3">
          <img 
            src={faviconUrl} 
            alt={`${displayDomain} favicon`} 
            className="w-6 h-6 object-contain rounded-sm"
            onError={handleIconError}
          />
        </div>
        <div className="flex-grow min-w-0">
          <div className="flex items-center space-x-2 flex-wrap">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {displayDomain}
            </p>
            
            {/* Content Type Badge */}
            {contentTypeDisplay && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400">
                {contentTypeDisplay}
              </span>
            )}
            
            {/* Quality Score Badge */}
            {quality_score && (
              <span 
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400"
                aria-label={`Quality score: ${Math.round(quality_score * 100)} percent`}
              >
                {Math.round(quality_score * 100)}% quality
              </span>
            )}
            
            {/* Relevance Score Badge */}
            {relevance_score && relevance_score > 10 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-400">
                {Math.round(relevance_score)} relevance
              </span>
            )}
            
            {/* Has Images Indicator */}
            {has_images && image_count > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400">
                📷 {image_count} images
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
            {displayUrl}
          </p>
        </div>
      </div>

      {/* Title */}
      <div className="mb-3">
        <a 
          href={url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="block group"
          aria-describedby={`result-snippet-${index}`}
        >
          <h3 
            id={`result-title-${index}`}
            className="text-xl font-semibold text-blue-600 dark:text-blue-400 group-hover:text-blue-800 dark:group-hover:text-blue-300 group-hover:underline leading-tight line-clamp-2"
          >
            {title}
          </h3>
        </a>
      </div>

      {/* Content preview/snippet */}
      <div className="mb-4">
        <p 
          id={`result-snippet-${index}`}
          className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm line-clamp-3"
        >
          {snippet}
        </p>
      </div>

      {/* Enhanced Metadata Footer */}
      <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        {/* Primary metadata row */}
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center space-x-4 flex-wrap">
            {/* Publication date */}
            {(formattedDate || fallbackDate) && (
              <div className="flex items-center space-x-1">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>{relativeDate || formattedDate || fallbackDate}</span>
              </div>
            )}

            {/* Enhanced Author with author_info */}
            {authorDisplay && (
              <div className="flex items-center space-x-1">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="truncate max-w-32" title={author_info?.display_name || author_info?.name || authorDisplay}>
                  {authorDisplay}
                </span>
              </div>
            )}

            {/* Reading Time */}
            {readingTime && (
              <div className="flex items-center space-x-1">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{readingTime} min read</span>
              </div>
            )}

            {/* Word Count */}
            {word_count && (
              <div className="flex items-center space-x-1">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>{word_count.toLocaleString()} words</span>
              </div>
            )}
          </div>

          {/* Technical metadata */}
          <div className="flex items-center space-x-2">
            {chunk_count && (
              <span className="text-gray-400 dark:text-gray-500" title="Content chunks indexed">
                {chunk_count} chunks
              </span>
            )}
            {domain_score && (
              <span className="text-gray-400 dark:text-gray-500" title="Domain authority score">
                DA: {Math.round(domain_score * 100)}
              </span>
            )}
          </div>
        </div>

        {/* Categories and Table of Contents row */}
        {(resultCategories?.length > 0 || table_of_contents?.length > 0) && (
          <div className="space-y-2">
            {/* Categories */}
            {resultCategories && resultCategories.length > 0 && (
              <div className="flex items-start space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <div className="flex flex-wrap gap-1" role="list" aria-label="Categories">
                  {resultCategories.slice(0, 4).map((category, idx) => (
                    <span 
                      key={idx}
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 cursor-default transition-colors"
                      role="listitem"
                    >
                      {category}
                    </span>
                  ))}
                  {resultCategories.length > 4 && (
                    <span className="text-gray-400 dark:text-gray-500" aria-label={`${resultCategories.length - 4} more categories`}>
                      +{resultCategories.length - 4} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Table of Contents Preview */}
            {table_of_contents && table_of_contents.length > 0 && (
              <div className="flex items-start space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-medium">Contents: </span>
                  <span className="truncate">
                    {table_of_contents.slice(0, 2).join(' • ')}
                    {table_of_contents.length > 2 && ` • +${table_of_contents.length - 2} more`}
                  </span>
                </div>
              </div>
            )}

            {/* Keywords Preview */}
            {keywords && keywords.length > 0 && (
              <div className="flex items-start space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-medium">Keywords: </span>
                  <span className="truncate">
                    {keywords.slice(0, 3).join(', ')}
                    {keywords.length > 3 && `, +${keywords.length - 3} more`}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default ResultCard;
