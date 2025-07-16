import React from 'react';

const SearchResults = ({ results }) => {
  if (!results) return null;

  const { query, ai_summary, results: searchResults, total_found, search_time_ms, search_method, timestamp } = results;

  if (total_found === 0) {
    return (
      <div className="results-container">
        <div className="loading">
          No results found for "{query}". Try different keywords or check spelling.
        </div>
      </div>
    );
  }

  return (
    <div className="results-container fade-in">
      {/* AI Summary */}
      {ai_summary && (
        <div className="ai-summary">
          <h3>🧠 AI Summary</h3>
          <p>{ai_summary}</p>
        </div>
      )}

      {/* Search Results */}
      {searchResults.map((result, index) => (
        <div key={result.id} className="result-item result-card">
          <a 
            href={result.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="result-title"
          >
            {result.title}
          </a>
          <div className="result-url">{result.url}</div>
          <div className="result-preview">{result.content_preview}</div>
          <div className="result-meta">
            <div className="meta-item">🌐 {result.domain}</div>
            <div className="meta-item">📄 {result.word_count} words</div>
            <div className="meta-item">⭐ {result.relevance_score}</div>
          </div>
        </div>
      ))}

      {/* Stats */}
      <div className="stats">
        ⚡ Found {total_found} results in {search_time_ms}ms using {search_method}
        <br />
        📅 {new Date(timestamp * 1000).toLocaleString()}
      </div>
    </div>
  );
};

export default SearchResults;
