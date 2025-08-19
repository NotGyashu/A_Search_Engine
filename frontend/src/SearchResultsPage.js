import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import ParallelSearchInterface from './components/ParallelSearchInterface';
import './index.css';

const SearchResultsPage = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialQuery = queryParams.get('q') || '';

  return (
    <div className="bg-white dark:bg-gray-900 min-h-screen  container">
      
    
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto"
        >
          <ParallelSearchInterface initialQuery={initialQuery} />
        </motion.div>
      
    </div>
  );
};

export default SearchResultsPage;