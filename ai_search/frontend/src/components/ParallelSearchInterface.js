import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SearchResults from './SearchResults';
import AIStreamingSummary from './AIStreamingSummary';

const ParallelSearchInterface = ({ initialQuery = '' }) => {
  const [query, setQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiRequestId, setAiRequestId] = useState(null);
  const [error, setError] = useState(null);
  const websocketRef = useRef(null);

  useEffect(() => {
    if (initialQuery.trim()) {
      setQuery(initialQuery);
      performSearch(initialQuery);
    }
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, [initialQuery]);

  const performSearch = async (searchQuery) => {
    const queryString = typeof searchQuery === 'string' ? searchQuery : query;
    
    if (!queryString.trim()) return;
    
    setLoading(true);
    setError(null);
    setSearchResults(null);
    setAiRequestId(null);
    
    if (websocketRef.current) {
      websocketRef.current.close();
    }
    
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(queryString.trim())}&limit=10`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Search failed');
      }
      
      const data = await response.json();
      
      setSearchResults(data);
      setAiRequestId(data.ai_summary_request_id);
      setLoading(false);
      
    } catch (error) {
      console.error('Search error:', error);
      setError(error.message);
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      performSearch(query);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-4xl mx-auto mb-8"
        >
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Search for anything..."
              className="w-full px-6 py-4 text-lg bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <button
              onClick={() => performSearch(query)}
              disabled={loading || !query.trim()}
              className="absolute right-3 top-3 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg transition-colors duration-200"
            >
              {loading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-5 h-5 border-t-2 border-b-2 border-white rounded-full"
                />
              ) : (
                'Search'
              )}
            </button>
          </div>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-4xl mx-auto mb-8 p-4 bg-red-100 border border-red-300 rounded-lg text-red-700"
          >
            Error: {error}
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
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <div className="mb-6 text-gray-500 text-sm">
                    Found {searchResults.total_found} results in {searchResults.search_time_ms}ms
                  </div>
                  <SearchResults results={searchResults} />
                </div>
                
                {aiRequestId && (
                  <div className="lg:col-span-1">
                    <AIStreamingSummary 
                      requestId={aiRequestId} 
                      query={query}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!loading && !searchResults && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-4xl mx-auto mt-16 p-6 bg-gray-50 rounded-xl border border-gray-200"
          >
            <h3 className="text-lg font-medium text-blue-600 mb-4">⚡ How It Works</h3>
            <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <span className="text-green-500">1.</span>
                <span>Search returns instantly (sub-100ms)</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-green-500">2.</span>
                <span>AI summary generates in background</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-green-500">3.</span>
                <span>Real-time streaming via WebSocket</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-green-500">4.</span>
                <span>Live typing effect for AI insights</span>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default ParallelSearchInterface;