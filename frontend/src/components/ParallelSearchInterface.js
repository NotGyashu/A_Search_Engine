// ParallelSearchInterface.js
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '../services/api';
import SearchBar from './SearchBar';
import SearchResults from './SearchResults';
import AIStreamingSummary from './AIStreamingSummary';
import ThemeToggle from './ThemeToggle';

const searchApiWrapper = async ({ queryKey }) => {
  const [, searchQuery, page, resultsPerPage, features, filters] = queryKey;
  
  if (!searchQuery?.trim()) {
    return null;
  }
  
  const offset = (page - 1) * resultsPerPage;
  return searchApi.search(searchQuery, { 
    limit: resultsPerPage, 
    offset,
    enable_ai_enhancement: features.enhanceQuery || features.contentAnalysis || features.entityExtraction || features.intentClassification,
    enable_cache: features.caching,
    content_types: filters.contentTypes,
    article_types: filters.articleTypes,
    domains: filters.domains,
    quality_score_min: filters.qualityScoreMin / 100,
    date_range: filters.dateRange,
    has_author: filters.hasAuthor,
    has_table_of_contents: filters.hasTableOfContents,
    has_images: filters.hasImages
  });
};

const ParallelSearchInterface = ({ initialQuery = '' }) => {
  const [activeQuery, setActiveQuery] = useState(''); 
  const [currentPage, setCurrentPage] = useState(1);
  const [aiRequestId, setAiRequestId] = useState(null);
  const [searchParams, setSearchParams] = useState({
    query: initialQuery,
    features: {
      enhanceQuery: true,
      caching: true,
      contentAnalysis: true,
      entityExtraction: true,
      intentClassification: true
    },
    filters: {
      domains: [],
      contentTypes: [],
      articleTypes: [],
      qualityScoreMin: 0,
      dateRange: 'all',
      hasAuthor: false,
      hasTableOfContents: false,
      hasImages: false
    }
  });
  
  const resultsPerPage = 10;
  const websocketRef = useRef(null);

  const { 
    data: searchResults, 
    isLoading, 
    error, 
    isFetching 
  } = useQuery({
    queryKey: ['search', activeQuery, currentPage, resultsPerPage, searchParams.features, searchParams.filters],
    queryFn: searchApiWrapper,
    enabled: !!activeQuery.trim(),
    staleTime: 5 * 60 * 1000,
    cacheTime: 10 * 60 * 1000,
    keepPreviousData: true
  });

  useEffect(() => {
    if (searchResults && currentPage === 1) {
      if (searchResults.ai_summary_request_id) {
        setAiRequestId(searchResults.ai_summary_request_id);
      }
    }
  }, [searchResults, currentPage]);

  const totalPages = searchResults ? Math.ceil(searchResults.total_results / resultsPerPage) : 0;
  const showLoading = isLoading && !searchResults;

  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      setActiveQuery(initialQuery);
    }
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, [initialQuery]);

  const handleSearch = (params) => {
    const { query, features, filters } = params;
    setSearchParams(params);
    setActiveQuery(query);
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="py-8 px-4 justify-center gap-4 flex flex-col">
        <div className="flex items-center justify-between gap-2 mx-auto min-w-[90vw] ">
          <div className='w-36  items-center flex justify-center'>Logo</div>
          <SearchBar 
            initialQuery={initialQuery}
            onSearch={handleSearch}
            isLoading={showLoading}
            placeholder="Search for anything..."
            className='flex-grow'
            initialFeatures={searchParams.features}
            initialFilters={searchParams.filters}
          />
          <div className='flex flex-row-reverse w-36'><ThemeToggle /></div>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-4xl mx-auto mb-8 p-4 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-400"
          >
            Error: {error.message}
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {searchResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-6xl mx-auto"
            >
              <div className="flex flex-col gap-5">
                {aiRequestId && (
                  <div className="">
                    <AIStreamingSummary 
                      requestId={aiRequestId} 
                      query={activeQuery}
                    />
                  </div>
                )}
                <div className="">
                  <SearchResults 
                    results={searchResults}
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                    loading={isFetching}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!showLoading && !searchResults && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-4xl mx-auto mt-16 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
          >
            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-4 flex items-center">
              <span className="mr-2">🔍</span>
              Search Engine
            </h3>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              Enter your search query above and use the feature controls to customize your search experience.
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default ParallelSearchInterface;