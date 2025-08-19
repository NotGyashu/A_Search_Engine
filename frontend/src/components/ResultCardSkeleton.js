import React from 'react';

const ResultCardSkeleton = () => (
  <div className="mb-6 p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
    {/* Header with favicon and domain skeleton */}
    <div className="flex items-center mb-3 animate-pulse">
      <div className="w-6 h-6 mr-3 rounded-full bg-gray-300 dark:bg-gray-600"></div>
      <div className="flex-1">
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-32 mb-1"></div>
        <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-48"></div>
      </div>
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-16"></div>
    </div>
    
    {/* Title skeleton */}
    <div className="mb-3 animate-pulse">
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-2"></div>
    </div>
    
    {/* Description skeleton */}
    <div className="mb-4 animate-pulse">
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-full mb-2"></div>
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-5/6 mb-2"></div>
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-4/5"></div>
    </div>
    
    {/* Metadata tags skeleton */}
    <div className="flex flex-wrap gap-2 mb-3 animate-pulse">
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded-full w-16"></div>
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded-full w-20"></div>
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded-full w-14"></div>
    </div>
    
    {/* Footer with date and quality score skeleton */}
    <div className="flex items-center justify-between text-sm animate-pulse">
      <div className="flex items-center space-x-4">
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-24"></div>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-20"></div>
      </div>
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-16"></div>
    </div>
  </div>
);

const ResultCardSkeletonList = ({ count = 5 }) => (
  <div>
    {Array.from({ length: count }).map((_, index) => (
      <ResultCardSkeleton key={index} />
    ))}
  </div>
);

export default ResultCardSkeleton;
export { ResultCardSkeletonList };
