import React from 'react';

const Features = ({ stats }) => {
  return (
    <div className="features">
      <div className="feature">
        <h3>⚡ Ultra Fast</h3>
        <p>Modular BM25 algorithm with sub-millisecond performance</p>
      </div>
      <div className="feature">
        <h3>🧠 Smart AI</h3>
        <p>Multiple AI models with intelligent fallbacks</p>
      </div>
      <div className="feature">
        <h3>🔧 Modular</h3>
        <p>Clean architecture with backend, frontend, and data pipeline</p>
      </div>
      <div className="feature">
        <h3>📊 Rich Data</h3>
        <p>
          {stats ? (
            <>
              {stats.total_documents?.toLocaleString()} documents across{' '}
              {stats.total_terms?.toLocaleString()} terms
            </>
          ) : (
            'Comprehensive index with advanced search capabilities'
          )}
        </p>
      </div>
      <div className="feature">
        <h3>🌐 Multi-Source</h3>
        <p>Content from diverse domains and websites</p>
      </div>
      <div className="feature">
        <h3>🔍 Relevant</h3>
        <p>BM25 ranking ensures most relevant results first</p>
      </div>
    </div>
  );
};

export default Features;
