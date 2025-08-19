// SearchBar.js
import React, { useState, useEffect , useRef} from 'react';
import { motion } from 'framer-motion';

const SearchBar = ({ 
  onSearch, 
  initialQuery = '', 
  isLoading = false, 
  placeholder = "Search for anything...",
  className = "mx-auto mb-8",
  initialFeatures = { 
    enhanceQuery: true,
    caching: true,
    contentAnalysis: true,
    entityExtraction: true,
    intentClassification: true
  },
  initialFilters = { 
    domains: [],
    contentTypes: [],
    articleTypes: [],
    qualityScoreMin: 0,
    dateRange: 'all',
    hasAuthor: false,
    hasTableOfContents: false,
    hasImages: false
  }
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [features, setFeatures] = useState(initialFeatures);
  const [filters, setFilters] = useState(initialFilters);
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef(null);
  const [browserSupport, setBrowserSupport] = useState(true);
  const [audioStatus, setAudioStatus] = useState('idle'); // idle, listening, processing
  const [showFeaturesDropdown, setShowFeaturesDropdown] = useState(false);
  const [showFiltersDropdown, setShowFiltersDropdown] = useState(false);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

    // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn("Speech recognition not supported in this browser");
      setBrowserSupport(false);
      return;
    }
    
    console.log('Initializing speech recognition...');
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = 'en-US';
    
    recognitionRef.current.onstart = () => {
      console.log('Speech recognition started');
      setAudioStatus('listening');
    };
    
    recognitionRef.current.onresult = (event) => {
      console.log('Speech recognition result:', event);
      const transcript = Array.from(event.results)
        .map(result => result[0])
        .map(result => result.transcript)
        .join('');
      
      console.log('Transcript:', transcript);
      setQuery(transcript);
      
      // If it's a final result, automatically search
      if (event.results[event.results.length - 1].isFinal) {
        console.log('Final result, processing...');
        setAudioStatus('processing');
        setTimeout(() => {
          setIsRecording(false);
          setAudioStatus('idle');
          if (transcript.trim()) {
            onSearch({
              query: transcript.trim(),
              features,
              filters
            });
          }
        }, 500);
      }
    };
    
    recognitionRef.current.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setAudioStatus('idle');
      setIsRecording(false);
    };
    
    recognitionRef.current.onend = () => {
      console.log('Speech recognition ended');
      setAudioStatus('idle');
      setIsRecording(false);
    };
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [features, filters, onSearch]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showFeaturesDropdown && !event.target.closest('.features-dropdown')) {
        setShowFeaturesDropdown(false);
      }
      if (showFiltersDropdown && !event.target.closest('.filters-dropdown')) {
        setShowFiltersDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showFeaturesDropdown, showFiltersDropdown]);

  const handleSubmit = (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }
    if (query.trim() && !isLoading) {
      onSearch({
        query: query.trim(),
        features,
        filters
      });
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  
  const toggleAudioSearch = () => {
    if (!browserSupport) {
      console.log('Browser does not support speech recognition');
      return;
    }
    
    if (!isRecording) {
      console.log('Starting speech recognition...');
      setAudioStatus('listening');
      setIsRecording(true);
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error('Error starting speech recognition:', error);
        setAudioStatus('idle');
        setIsRecording(false);
      }
    } else {
      console.log('Stopping speech recognition...');
      recognitionRef.current.stop();
    }
  };
  
  const toggleFeature = (featureName) => {
    const newFeatures = {
      ...features,
      [featureName]: !features[featureName]
    };
    setFeatures(newFeatures);
    triggerSearchWithNewParams(newFeatures, filters);
  };

  const updateFilter = (filterName, value) => {
    const newFilters = {
      ...filters,
      [filterName]: value
    };
    setFilters(newFilters);
    triggerSearchWithNewParams(features, newFilters);
  };

  const triggerSearchWithNewParams = (newFeatures, newFilters) => {
    if (query.trim()) {
      onSearch({
        query: query.trim(),
        features: newFeatures,
        filters: newFilters
      });
    }
  };

  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.domains.length > 0) count++;
    if (filters.contentTypes.length > 0) count++;
    if (filters.articleTypes.length > 0) count++;
    if (filters.qualityScoreMin > 0) count++;
    if (filters.dateRange !== 'all') count++;
    if (filters.hasAuthor) count++;
    if (filters.hasTableOfContents) count++;
    if (filters.hasImages) count++;
    return count;
  };

    // Audio search status indicator
  const renderAudioIndicator = () => {
    if (!browserSupport) return null;
    
    const statusColors = {
      idle: 'text-gray-400',
      listening: 'text-red-500 animate-pulse',
      processing: 'text-blue-500 animate-spin'
    };
    
    const icons = {
      idle: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
        </svg>
      ),
      listening: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM14.657 2.929a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-2.929 7.071 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 10c0-2.21-.894-4.208-2.343-5.657a1 1 0 010-1.414zm-2.829 2.828a1 1 0 011.415 0A5.983 5.983 0 0115 10a5.984 5.984 0 01-1.757 4.243 1 1 0 01-1.415-1.415A3.984 3.984 0 0013 10a3.983 3.983 0 00-1.172-2.828 1 1 0 010-1.415z" clipRule="evenodd" />
        </svg>
      ),
      processing: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      )
    };
    return (
      <button
        type="button"
        onClick={toggleAudioSearch}
        disabled={isLoading}
        className={`p-2 rounded-full focus:outline-none ${statusColors[audioStatus]}`}
        aria-label={isRecording ? "Stop recording" : "Start voice search"}
      >
        {icons[audioStatus]}
      </button>
    );
  };

  return (
    <div className={className}>
      <form onSubmit={handleSubmit} className="relative gap-5 w-full flex border border-gray-300 dark:border-gray-600 rounded-full px-6 bg-white dark:bg-gray-800 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:focus:ring-blue-900 shadow transition-all duration-200" role="search">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          className="flex-grow  py-4 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none"
          disabled={isLoading}
          autoFocus
          aria-label="Search input"
          aria-describedby="search-help"
        />
        <div className='flex items-center gap-3'>
          <button
            type="button"
            onClick={() => setQuery('')}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Clear search"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" role="img" aria-label="Close" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
              <title>Close</title>
              <path d="M18.3 5.71a1 1 0 0 0-1.41 0L12 10.59 7.11 5.7A1 1 0 0 0 5.7 7.11L10.59 12l-4.89 4.89a1 1 0 1 0 1.41 1.41L12 13.41l4.89 4.89a1 1 0 0 0 1.41-1.41L13.41 12l4.89-4.89a1 1 0 0 0 0-1.4z"/>
            </svg>
          </button>
          
          {renderAudioIndicator()}
          <div className="relative inline-block text-left filters-dropdown">
            <button
              onClick={() => setShowFiltersDropdown(!showFiltersDropdown)}
              className={`flex items-center space-x-1 px-3 py-1.5 text-xs rounded-md border transition-colors ${
                getActiveFiltersCount() > 0
                  ? 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-900 dark:border-blue-600 dark:text-blue-300'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600'
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 4h18l-7 8v6l-4 2v-8L3 4z"
                />
              </svg>
              {getActiveFiltersCount() > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-600 text-white rounded-full">
                  {getActiveFiltersCount()}
                </span>
              )}
            </button>

            {showFiltersDropdown && (
              <div className="absolute w-48 right-0 mt-1 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-50 max-h-96 overflow-y-auto">
                <div className="p-4 space-y-4">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 border-b pb-2">
                    Filter by:
                  </h3>
                  <div>
                    <select
                      value={filters.dateRange}
                      onChange={(e) => updateFilter('dateRange', e.target.value)}
                      className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md p-2 bg-white dark:bg-gray-700"
                    >
                      <option value="all">All Time</option>
                      <option value="week">Past Week</option>
                      <option value="month">Past Month</option>
                      <option value="year">Past Year</option>
                    </select>
                  </div>
          
                    <div className="space-y-1 overflow-y-auto">
                      {['blog', 'news', 'tutorial', 'documentation', 'academic', 'reference'].map((type) => (
                        <label key={type} className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={filters.contentTypes.includes(type)}
                            onChange={() => {
                              const newTypes = filters.contentTypes.includes(type)
                                ? filters.contentTypes.filter(t => t !== type)
                                : [...filters.contentTypes, type];
                              updateFilter('contentTypes', newTypes);
                            }}
                            className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="text-xs text-gray-700 dark:text-gray-300 capitalize">only {type}</span>
                        </label>
                      ))}

                      <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasAuthor}
                        onChange={() => updateFilter('hasAuthor', !filters.hasAuthor)}
                        className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-xs text-gray-700 dark:text-gray-300">Has Author</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasTableOfContents}
                        onChange={() => updateFilter('hasTableOfContents', !filters.hasTableOfContents)}
                        className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-xs text-gray-700 dark:text-gray-300">Has Table of Contents</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasImages}
                        onChange={() => updateFilter('hasImages', !filters.hasImages)}
                        className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-xs text-gray-700 dark:text-gray-300">Has Images</span>
                    </label>
                    </div>
                  

                  {getActiveFiltersCount() > 0 && (
                    <button
                      onClick={() => {
                        const resetFilters = {
                          domains: [],
                          contentTypes: [],
                          articleTypes: [],
                          qualityScoreMin: 0,
                          dateRange: 'all',
                          hasAuthor: false,
                          hasTableOfContents: false,
                          hasImages: false
                        };
                        setFilters(resetFilters);
                        triggerSearchWithNewParams(features, resetFilters);
                      }}
                      className="w-full text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-3 rounded-md transition-colors"
                    >
                      Clear All Filters
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="relative inline-block text-left features-dropdown">
            <button
              onClick={() => setShowFeaturesDropdown(!showFeaturesDropdown)}
              className="flex items-center space-x-1 px-3 py-1.5 text-xs rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 6h16M4 12h8m-8 6h16"
                />
              </svg>
            </button>

            {showFeaturesDropdown && (
              <div className="absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-50">
                <div className="py-1">
                  {[
                    { key: 'enhanceQuery', label: 'Enhance Query' },
                    { key: 'caching', label: 'Smart Caching' },
                    { key: 'contentAnalysis', label: 'Content Analysis' },
                    { key: 'entityExtraction', label: 'Entity Extraction' },
                    { key: 'intentClassification', label: 'Intent Classification' }
                  ].map((feature) => (
                    <label
                      key={feature.key}
                      className="flex items-center space-x-3 px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={features[feature.key]}
                        onChange={() => toggleFeature(feature.key)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{feature.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full p-2 hover:opacity-90 transition-opacity disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-100"
            aria-label={isLoading ? "Searching..." : "Search"}
          >
            {isLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-6 h-6 border-t-2 border-b-2 border-white rounded-full"
                aria-hidden="true"
              />
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
          </button>
        </div>
        <div id="search-help" className="sr-only">
          Enter your search query and press Enter or click the search button
        </div>
      </form>

       {/* Audio search status */}
      {isRecording && (
        <div className="mt-2 text-center text-sm">
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
            className="inline-flex items-center"
          >
            <span className="h-2 w-2 rounded-full bg-red-500 mr-2"></span>
            Listening...
          </motion.div>
        </div>
      )}

    </div>
  );
};

export default SearchBar;