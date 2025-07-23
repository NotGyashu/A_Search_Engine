import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './HomePage';
import SearchResultsPage from './SearchResultsPage';

function App() {
  return (
    <div className="min-h-screen bg-white">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchResultsPage />} />
      </Routes>
    </div>
  );
}

export default App;