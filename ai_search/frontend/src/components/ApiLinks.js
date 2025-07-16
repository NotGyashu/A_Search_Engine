import React from 'react';

const ApiLinks = () => {
  return (
    <div className="api-links">
      <a href="/api/docs" target="_blank" rel="noopener noreferrer">
        📚 API Docs
      </a>
      <a href="/health" target="_blank" rel="noopener noreferrer">
        ❤️ Health
      </a>
      <a href="/api/stats" target="_blank" rel="noopener noreferrer">
        📊 Stats
      </a>
      <a href="/api/config" target="_blank" rel="noopener noreferrer">
        ⚙️ Config
      </a>
    </div>
  );
};

export default ApiLinks;
