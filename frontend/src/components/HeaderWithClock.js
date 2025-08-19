import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';

const HeaderWithClock = () => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString([], { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  return (
    <header className="w-full py-4 px-8 flex justify-between items-center border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 transition-colors duration-300">
      <Link to="/" className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-indigo-600">
        NEBULA
      </Link>
      <div className="flex items-center space-x-4">
        <div className="text-right">
          <div className="text-gray-700 dark:text-gray-300 text-sm">{formatDate(currentTime)}</div>
          <div className="text-gray-900 dark:text-gray-100 text-xl font-semibold">{formatTime(currentTime)}</div>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
};

export default HeaderWithClock;