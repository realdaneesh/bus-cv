import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = 'Loading...' }) => (
  <div className="state-container">
    <div className="spinner" />
    <span className="state-message">{message}</span>
  </div>
);

export default LoadingSpinner;
