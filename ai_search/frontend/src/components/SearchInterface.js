import React, { useState, useEffect } from 'react';
import SearchBox from './SearchBox';
import SearchResults from './SearchResults';
import Features from './Features';
import ApiLinks from './ApiLinks';

const SearchInterface = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  // Check API health on component mount
  useEffect(() => {
    // Health check
    fetch('/api/health')
      .then(response => response.json())
      .then(data => {
        if (data.status !== 'healthy') {
          console.warn('API health check failed:', data);
        }
      })
      .catch(error => console.error('Health check error:', error));

    // Get API stats
    fetch('/api/stats')
      .then(response => response.json())
      .then(data => setStats(data))
      .catch(error => console.error('Stats error:', error));
  }, []);

  const performSearch = async (searchQuery, limit = 10) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: limit,
          include_ai_summary: true
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResults(data);
      
    } catch (err) {
      setError(err.message);
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    performSearch(query);
  };

  const handleQueryChange = (newQuery) => {
    setQuery(newQuery);
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-container">
      {/* Header */}
      <div className="header">
        <h1>🚀 AI Search Engine</h1>
        <p>Modular BM25 ranking + intelligent summarization</p>
        <div className="version">v2.0 | React Frontend</div>
        <ApiLinks />
      </div>

      {/* Search Box */}
      <SearchBox
        query={query}
        onQueryChange={handleQueryChange}
        onSearch={handleSearch}
        onKeyPress={handleKeyPress}
        loading={loading}
      />

      {/* Error Display */}
      {error && (
        <div className="results-container">
          <div className="loading">
            ❌ Error: {error}
          </div>
        </div>
      )}

      {/* Loading Display */}
      {loading && (
        <div className="results-container">
          <div className="loading">
            🔍 Searching modular AI engine...
          </div>
        </div>
      )}

      {/* Search Results */}
      {results && !loading && (
        <SearchResults results={results} />
      )}

      {/* Features (shown when no results) */}
      {!results && !loading && !error && (
        <Features stats={stats} />
      )}
    </div>
  );
};

export default SearchInterface;
