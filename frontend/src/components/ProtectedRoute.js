import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // Show loading spinner while checking authentication
    return (
      <div className="is-flex is-justify-content-center is-align-items-center" style={{ minHeight: '100vh' }}>
        <div className="has-text-centered">
          <div className="is-size-4">Loading...</div>
          <progress className="progress is-primary" max="100" style={{ width: '200px' }}></progress>
        </div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

export default ProtectedRoute; 