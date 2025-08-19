// HomePage.js
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import HeaderWithClock from './components/HeaderWithClock';
import SearchBar from './components/SearchBar';

const HomePage = () => {
  const navigate = useNavigate();
  const [browserSupport, setBrowserSupport] = useState(true);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setBrowserSupport(!!SpeechRecognition);
  }, []);

  // Changed to accept the params object and extract the query
  const handleSearch = (params) => {
    if (params.query && params.query.trim()) {
      navigate(`/search?q=${encodeURIComponent(params.query)}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-gray-900 transition-colors duration-300">
      <HeaderWithClock />
      
      <div className="flex-grow flex flex-col items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <div className="text-6xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-indigo-600">
            NEBULA
          </div>
          <div className="h-1 w-32 bg-gradient-to-r from-blue-500 to-indigo-500 mx-auto rounded-full"></div>
        </motion.div>

        <motion.div
          className="w-full max-w-xl"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <SearchBar 
            onSearch={handleSearch}  // Now passing the object
            placeholder="Search the cosmos..."
            className="w-full"
          />
        </motion.div>

        {!browserSupport && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 text-sm text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 px-4 py-2 rounded-md"
          >
            Voice search is not supported in your browser. Try Chrome or Edge.
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute bottom-8 text-gray-500 dark:text-gray-400 text-sm transition-colors duration-300"
        >
          AI-Powered Cosmic Search
        </motion.div>
      </div>
    </div>
  );
};

export default HomePage;