import React from 'react';
import { motion } from 'framer-motion';

const SearchResults = ({ results }) => {
  if (!results) return null;

  const { query, results: searchResults, total_found, search_time_ms } = results;

  if (total_found === 0) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-20"
      >
        <div className="text-2xl text-gray-700 mb-4">No results found</div>
        <p className="text-gray-500 max-w-xl mx-auto">
          Your search for "{query}" did not match any documents. 
          Try different keywords or search terms.
        </p>
      </motion.div>
    );
  }

  return (
    <div>
      <div className="space-y-6">
        {searchResults.map((result, index) => (
          <motion.div
            key={result.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="p-6 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow duration-300"
          >
            <a 
              href={result.url} 
              className="block"
              target="_blank" 
              rel="noopener noreferrer"
            >
              <div className="mb-3">
                <h3 className="text-xl font-medium text-blue-600 underline">
                  {result.title}
                </h3>
              </div>
              
              <p className="text-gray-700 mb-4 leading-relaxed">
                {result.content_preview}
              </p>
              
              <div className="text-sm text-gray-500">
                <span className="flex items-center">
                  {result.domain}
                </span>
              </div>
            </a>
          </motion.div>
        ))}
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-12 pt-6 border-t border-gray-200 text-center text-sm text-gray-500"
      >
        <div className="inline-flex items-center space-x-6">
          <span className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {total_found} results found
          </span>
          <span className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {search_time_ms}ms search time
          </span>
        </div>
        <div className="mt-2 text-xs text-gray-400">
          Powered by Enhanced BM25 • Parallel AI Search Engine
        </div>
      </motion.div>
    </div>
  );
};

export default SearchResults;