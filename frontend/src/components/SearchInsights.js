import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const SearchInsights = ({ insights, className = "" }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!insights || Object.keys(insights).length === 0) {
    return null;
  }

  const {
    total_results = 0,
    domains_found = 0,
    top_domains = {},
    content_types = {},
    article_types = {},
    top_categories = {},
    date_range = null,
    results_with_authors = 0,
    results_with_toc = 0,
    average_quality_score = 0,
    average_relevance_score = 0,
    has_recent_content = false,
    content_diversity_score = 0
  } = insights;

  const hasDetailedInsights = domains_found > 0 || Object.keys(content_types).length > 0 || Object.keys(top_categories).length > 0;

  if (!hasDetailedInsights) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Search Insights
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center"
        >
          {isExpanded ? 'Show Less' : 'Show More'}
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`h-4 w-4 ml-1 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Quick Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{domains_found}</div>
          <div className="text-xs text-gray-600 dark:text-gray-400">Domains</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {Math.round(average_quality_score * 100)}%
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">Avg Quality</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{results_with_authors}</div>
          <div className="text-xs text-gray-600 dark:text-gray-400">With Authors</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {Math.round(content_diversity_score * 100)}%
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">Diversity</div>
        </div>
      </div>

      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-4"
          >
            {/* Top Domains */}
            {Object.keys(top_domains).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Top Domains</h4>
                <div className="space-y-1">
                  {Object.entries(top_domains).slice(0, 5).map(([domain, count]) => (
                    <div key={domain} className="flex justify-between items-center text-sm">
                      <span className="text-gray-700 dark:text-gray-300 truncate">{domain}</span>
                      <span className="text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full text-xs">
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Content Types */}
            {Object.keys(content_types).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Content Types</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(content_types).map(([type, count]) => (
                    <span 
                      key={type}
                      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400"
                    >
                      {type} ({count})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Top Categories */}
            {Object.keys(top_categories).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Top Categories</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(top_categories).slice(0, 8).map(([category, count]) => (
                    <span 
                      key={category}
                      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400"
                    >
                      {category} ({count})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Date Range */}
            {date_range && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Date Range</h4>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center space-x-4">
                    <span>From: {date_range.earliest}</span>
                    <span>To: {date_range.latest}</span>
                    <span>Span: {date_range.span_days} days</span>
                  </div>
                </div>
              </div>
            )}

            {/* Additional Metrics */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Results with Table of Contents:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">{results_with_toc}</span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Average Relevance Score:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">{Math.round(average_relevance_score)}</span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Recent Content:</span>
                <span className={`ml-2 font-medium ${has_recent_content ? 'text-green-600 dark:text-green-400' : 'text-gray-500'}`}>
                  {has_recent_content ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default SearchInsights;
