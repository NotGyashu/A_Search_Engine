import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { websocketApi } from '../services/api';

const AIStreamingSummary = ({ requestId, query, className = '' }) => {
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('connecting');
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const websocketRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const connectionAttempted = useRef(false);

  // Copy to clipboard function
  const handleCopyToClipboard = async () => {
    if (!summary) return;
    
    try {
      await navigator.clipboard.writeText(summary);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = summary;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  useEffect(() => {
    if (!requestId || connectionAttempted.current) return;
    
    connectionAttempted.current = true;
    setStatus('connecting');
    setError(null);
    setIsComplete(false);
    setSummary('');
    
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
    }
    
    connectionTimeoutRef.current = setTimeout(() => {
      if (status === 'connecting') {
        setError('Connection timeout');
        setStatus('failed');
        websocketRef.current?.close();
      }
    }, 10000);

    // Use the API service for WebSocket connection
    websocketRef.current = websocketApi.connectAISummary(requestId);

    websocketRef.current.onopen = () => {
      console.log('WebSocket connected');
      clearTimeout(connectionTimeoutRef.current);
      setStatus('connected');
      setProgress('Initializing AI...');
    };

    websocketRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'ping') {
          websocketRef.current.send(JSON.stringify({type: 'pong'}));
          return;
        }

        switch (data.type) {
          case 'status':
            setStatus(data.status);
            if (data.progress) setProgress(data.progress);
            break;
          case 'progress':
            setProgress(data.progress);
            break;
          case 'summary_chunk':
            setSummary(prev => prev + data.text);
            setStatus('streaming');
            setProgress('');
            break;
          case 'summary_done':
            setIsComplete(true);
            setStatus('completed');
            setProgress('');
            setTimeout(() => {
              websocketRef.current?.close(1000, 'AI processing completed');
            }, 1000);
            break;
          case 'error':
            setError(data.error);
            setStatus('failed');
            setProgress('');
            setIsComplete(true);
            break;
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    websocketRef.current.onerror = (event) => {
      console.error('WebSocket error:', event);
      clearTimeout(connectionTimeoutRef.current);
      setError('Connection error');
      setStatus('failed');
    };

    websocketRef.current.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason || 'No reason');
      clearTimeout(connectionTimeoutRef.current);
      
      if (event.code !== 1000 && !isComplete && !error) {
        setError(event.reason || 'Connection closed unexpectedly');
        setStatus('failed');
      }
    };

    return () => {
      clearTimeout(connectionTimeoutRef.current);
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [requestId]);

  const getStatusColor = () => {
    switch (status) {
      case 'connecting':
      case 'connected':
        return 'text-yellow-500';
      case 'streaming':
        return 'text-blue-500';
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'connecting':
      case 'connected':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-5 h-5 border-t-2 border-b-2 border-yellow-500 rounded-full"
          />
        );
      case 'streaming':
        return (
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="w-5 h-5 bg-blue-500 rounded-full"
          />
        );
      case 'completed':
        return (
          <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 bg-white dark:bg-gray-800 rounded-lg border dark:text-white border-gray-200 dark:border-gray-700 shadow-sm ${className}`}
    >
      <div className="flex items-start">
        <div className="mr-3 mt-1">
          { status != 'completed' && getStatusIcon()}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-3">
            
            <div className="flex items-center space-x-2">
              {summary && isComplete && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleCopyToClipboard}
                  className="p-1  text-gray-500 dark:text-white hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  aria-label="Copy AI summary to clipboard"
                >
                  {copySuccess ? (
                    <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  )}
                </motion.button>
              )}
              <span className={`text-xs font-medium ${getStatusColor()}`}>
                {status === 'connecting' && 'Connecting...'}
                {status === 'connected' && 'Connected'}
                {status === 'streaming' && 'Generating...'}
                {status === 'completed' && ''}
                {status === 'failed' && 'Failed'}
              </span>
            </div>
          </div>

          {progress && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-3 text-sm text-gray-600"
            >
              {progress}
            </motion.div>
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-3"
            >
              AI Summary Error: {error}
            </motion.div>
          )}

          <div className="min-h-[60px]">
            {summary ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-gray-800 leading-relaxed dark:text-white"
              >
                <ReactMarkdown
                  components={{
                    // Custom styling for markdown elements
                    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="mb-3 ml-4 list-disc">{children}</ul>,
                    ol: ({ children }) => <ol className="mb-3 ml-4 list-decimal">{children}</ol>,
                    li: ({ children }) => <li className="mb-1">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                    em: ({ children }) => <em className="italic">{children}</em>,
                    code: ({ children }) => <code className="px-1 py-0.5 bg-gray-100 rounded text-sm font-mono">{children}</code>,
                    h1: ({ children }) => <h1 className="text-lg font-semibold text-gray-900 mb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-base font-semibold text-gray-900 mb-2">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-sm font-semibold text-gray-900 mb-2">{children}</h3>,
                  }}
                >
                  {summary}
                </ReactMarkdown>
                {status === 'streaming' && (
                  <motion.span
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
                    className="text-blue-500"
                  >
                    |
                  </motion.span>
                )}
              </motion.div>
            ) : status === 'connecting' || status === 'connected' ? (
              <div className="flex items-center space-x-2 text-gray-500">
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="text-sm"
                >
                  Preparing AI analysis for "{query}"...
                </motion.div>
              </div>
            ) : status === 'failed' ? (
              <div className="text-gray-500 text-sm">
                AI summary unavailable for this search.
              </div>
            ) : (
              <div className="text-gray-500 text-sm">
                Waiting for AI response...
              </div>
            )}
          </div>

          {isComplete && summary && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-3 pt-3 border-t border-gray-200 text-xs dark:text-white text-gray-500"
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center">
                  <span>✨ Generated by AI</span>
                </span>
                {copySuccess && (
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="text-green-600 font-medium"
                  >
                    Copied!
                  </motion.span>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default AIStreamingSummary;