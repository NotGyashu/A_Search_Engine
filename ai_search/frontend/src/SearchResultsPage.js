import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import ParallelSearchInterface from './components/ParallelSearchInterface';
import HeaderWithClock from './components/HeaderWithClock';
import './index.css';

const SearchResultsPage = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialQuery = queryParams.get('q') || '';

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <HeaderWithClock />
      
      <div className="container mx-auto px-4 py-8 flex-grow">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-6xl mx-auto"
        >
          <ParallelSearchInterface initialQuery={initialQuery} />
        </motion.div>
      </div>
    </div>
  );
};

export default SearchResultsPage;