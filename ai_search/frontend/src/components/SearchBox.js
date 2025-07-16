import React from 'react';

const SearchBox = ({ query, onQueryChange, onSearch, onKeyPress, loading }) => {
  return (
    <div className="search-box-container">
      <div className="search-box">
        <input
          type="text"
          className="search-input"
          placeholder="Search across 22,000+ documents..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyPress={onKeyPress}
          disabled={loading}
        />
        <button
          className="search-btn"
          onClick={onSearch}
          disabled={loading || !query.trim()}
        >
          {loading ? '🔍 Searching...' : '🔍 Search'}
        </button>
      </div>
    </div>
  );
};

export default SearchBox;
