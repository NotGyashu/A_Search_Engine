import React from 'react';
import { motion } from 'framer-motion';
import ResultCard from './ResultCard';
import Pagination from './Pagination';
import { ResultCardSkeletonList } from './ResultCardSkeleton';

const SearchResults = ({ 
  results, 
  currentPage = 1, 
  totalPages = 0, 
  onPageChange = () => {}, 
  loading = false 
}) => {
  // Show skeleton loaders while loading initial results
  if (loading && !results) {
    return (
      <div role="status" aria-live="polite" aria-label="Loading search results">
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 text-sm text-gray-600 dark:text-gray-400"
        >
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-48 animate-pulse"></div>
        </motion.div>
        <ResultCardSkeletonList count={10} />
        <div className="sr-only">Loading search results, please wait...</div>
      </div>
    );
  }

  if (!results) return null;

  const { 
    query, 
    results: searchResults, 
    total_results, 
    response_time_ms,
    search_insights = {}
  } = results;

  // Extract search insights for performance display
  const {
    domains_found = 0,
    average_quality_score = 0,
    quality_score = 0
  } = search_insights;

  if (total_results === 0) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-20"
        role="status"
        aria-live="polite"
      >
        <div className="text-2xl text-gray-700 dark:text-gray-300 mb-4">No results found</div>
        <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
          Your search for "{query}" did not match any documents. 
          Try different keywords or search terms.
        </p>
      </motion.div>
    );
  }

  return (
    <div role="main" aria-label="Search results">
      {/* Results Grid */}
      <motion.div 
        className="space-y-4 mb-8"
        role="list"
        aria-label="Search results list"
      >
        {searchResults.map((result, index) => (
          <ResultCard
            key={`${result.url}-${currentPage}-${index}`}
            result={result}
            index={index}
            searchQuery={query}
          />
        ))}
      </motion.div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={onPageChange}
          totalResults={total_results}
          resultsPerPage={10}
        />
      )}
    </div>
  );
};

export default SearchResults;
