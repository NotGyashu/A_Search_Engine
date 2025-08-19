import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AIInsights = ({ insights, className = "" }) => {
  const [expandedSection, setExpandedSection] = useState(null);

  if (!insights || Object.keys(insights).length === 0) {
    return null;
  }

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const renderQueryEnhancement = (enhancement) => {
    if (!enhancement) return null;
    
    return (
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Enhanced Query</div>
            <div className="text-sm text-blue-600 dark:text-blue-400 mt-1 font-mono text-xs bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded">
              {enhancement.enhanced_query}
            </div>
          </div>
          <div className="text-xs text-gray-500 ml-2">
            {enhancement.processing_time_ms}ms • {Math.round(enhancement.confidence * 100)}% confidence
          </div>
        </div>
        
        {enhancement.expansions && enhancement.expansions.length > 0 && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Expansions:</div>
            <div className="flex flex-wrap gap-1">
              {enhancement.expansions.map((expansion, idx) => (
                <span key={idx} className="text-xs bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-2 py-1 rounded">
                  {expansion}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {enhancement.suggestions && enhancement.suggestions.length > 0 && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Suggestions:</div>
            <div className="space-y-1">
              {enhancement.suggestions.map((suggestion, idx) => (
                <div key={idx} className="text-xs text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 px-2 py-1 rounded">
                  {suggestion}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderIntentClassification = (intent) => {
    if (!intent) return null;
    
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Primary Intent: </span>
            <span className="text-sm bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 px-2 py-1 rounded">
              {intent.primary_intent}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            {intent.processing_time_ms}ms • {Math.round(intent.confidence * 100)}% confidence
          </div>
        </div>
        
        {intent.suggested_filters && intent.suggested_filters.length > 0 && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Suggested Filters:</div>
            <div className="flex flex-wrap gap-1">
              {intent.suggested_filters.map((filter, idx) => (
                <span key={idx} className="text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 px-2 py-1 rounded">
                  {filter}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderEntityExtraction = (entities) => {
    if (!entities || !entities.entities) return null;
    
    const { entities: entityData, entity_count } = entities;
    
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Extracted Entities ({entity_count} found)
          </div>
          <div className="text-xs text-gray-500">
            {entities.processing_time_ms}ms
          </div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {Object.entries(entityData).map(([type, items]) => (
            items && items.length > 0 && (
              <div key={type} className="space-y-1">
                <div className="text-xs font-medium text-gray-600 dark:text-gray-400 capitalize">
                  {type.replace('_', ' ')}
                </div>
                <div className="space-y-1">
                  {items.map((item, idx) => (
                    <span key={idx} className="block text-xs bg-teal-100 dark:bg-teal-900/20 text-teal-700 dark:text-teal-400 px-2 py-1 rounded">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
      </div>
    );
  };

  const renderContentAnalysis = (analysis) => {
    if (!analysis) return null;
    
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Content Analysis
          </div>
          <div className="text-xs text-gray-500">
            {analysis.processing_time_ms}ms
          </div>
        </div>
        
        {analysis.quality_distribution && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">Quality Distribution</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-green-50 dark:bg-green-900/20 p-2 rounded">
                <div className="font-medium text-green-700 dark:text-green-400">High Quality</div>
                <div className="text-green-600 dark:text-green-300">{analysis.quality_distribution.high_quality_count} results</div>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
                <div className="font-medium text-yellow-700 dark:text-yellow-400">Average: {Math.round(analysis.quality_distribution.average * 100)}%</div>
                <div className="text-yellow-600 dark:text-yellow-300">Quality Score</div>
              </div>
            </div>
          </div>
        )}
        
        {analysis.content_types && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Content Types</div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(analysis.content_types).map(([type, count]) => (
                <span key={type} className="text-xs bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 px-2 py-1 rounded">
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {analysis.insights && analysis.insights.length > 0 && (
          <div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Key Insights</div>
            <div className="space-y-1">
              {analysis.insights.map((insight, idx) => (
                <div key={idx} className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 px-2 py-1 rounded">
                  • {insight}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const sections = [
    {
      key: 'query_enhancement',
      title: '🚀 Query Enhancement',
      data: insights.query_enhancement,
      render: renderQueryEnhancement,
      color: 'blue'
    },
    {
      key: 'intent_classification',
      title: '🎯 Intent Classification',
      data: insights.intent_classification,
      render: renderIntentClassification,
      color: 'orange'
    },
    {
      key: 'entity_extraction',
      title: '🏷️ Entity Extraction',
      data: insights.entity_extraction,
      render: renderEntityExtraction,
      color: 'teal'
    },
    {
      key: 'content_analysis',
      title: '📊 Content Analysis',
      data: insights.content_analysis,
      render: renderContentAnalysis,
      color: 'indigo'
    },
    {
      key: 'comprehensive_insights',
      title: '🧠 Comprehensive Insights',
      data: insights.comprehensive_insights,
      render: (data) => data && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">AI Intelligence Summary</div>
            <div className="text-xs text-gray-500">{data.processing_time_ms}ms</div>
          </div>
          {data.recommendations && data.recommendations.length > 0 && (
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Recommendations</div>
              <div className="space-y-1">
                {data.recommendations.map((rec, idx) => (
                  <div key={idx} className="text-xs text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-900/20 px-2 py-1 rounded">
                    💡 {rec}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ),
      color: 'purple'
    }
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/10 dark:to-purple-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center">
          <span className="mr-2">🤖</span>
          AI Intelligence Insights
          <span className="ml-2 text-xs bg-blue-500 text-white px-2 py-1 rounded-full">
            Batch Optimized
          </span>
        </h3>
        <div className="text-xs text-gray-500">
          {sections.filter(s => s.data).length} analysis modules
        </div>
      </div>
      
      <div className="space-y-2">
        {sections.map((section) => (
          section.data && (
            <div key={section.key} className="border border-gray-200 dark:border-gray-700 rounded-lg">
              <button
                onClick={() => toggleSection(section.key)}
                className={`w-full px-3 py-2 text-left text-sm font-medium bg-${section.color}-50 dark:bg-${section.color}-900/20 hover:bg-${section.color}-100 dark:hover:bg-${section.color}-900/30 rounded-lg transition-colors flex items-center justify-between`}
              >
                <span className="text-gray-700 dark:text-gray-300">{section.title}</span>
                <motion.svg
                  animate={{ rotate: expandedSection === section.key ? 180 : 0 }}
                  className="w-4 h-4 text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </motion.svg>
              </button>
              
              <AnimatePresence>
                {expandedSection === section.key && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="p-3 bg-white dark:bg-gray-800/50">
                      {section.render(section.data)}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        ))}
      </div>
    </motion.div>
  );
};

export default AIInsights;
