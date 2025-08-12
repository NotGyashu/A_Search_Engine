import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AIStreamingSummary = ({ requestId, query, className = '' }) => {
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('connecting');
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const websocketRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const connectionAttempted = useRef(false);

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
  const backendHost = process.env.REACT_APP_BACKEND_URL || window.location.hostname;
  const wsPort = process.env.REACT_APP_WS_PORT || '8000';
  const wsPath = process.env.REACT_APP_WS_PATH || `/api/ws/summary`;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const wsUrl = `${protocol}//${backendHost}:${wsPort}${wsPath}/${requestId}`;

    websocketRef.current = new WebSocket(wsUrl);
    websocketRef.current.withCredentials = true;

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
      className={`p-6 bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}
    >
      <div className="flex items-start">
        <div className="mr-3 mt-1">
          {getStatusIcon()}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-medium text-blue-600">
              AI Insight
            </h3>
            <span className={`text-xs font-medium ${getStatusColor()}`}>
              {status === 'connecting' && 'Connecting...'}
              {status === 'connected' && 'Connected'}
              {status === 'streaming' && 'Generating...'}
              {status === 'completed' && 'Complete'}
              {status === 'failed' && 'Failed'}
            </span>
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
                className="text-gray-800 leading-relaxed"
              >
                {summary}
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
              className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500"
            >
              <div className="flex items-center space-x-4">
                <span>✨ Generated by AI</span>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default AIStreamingSummary;