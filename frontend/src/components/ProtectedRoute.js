import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * @param {Object} props
 * @param {React.ReactNode} props.children
 * @param {boolean} [props.requireFullAuth] - If true, redirects first-time users (is_auth=false) to /first-time-setup
 */
const ProtectedRoute = ({ children, requireFullAuth = false }) => {
  const { isAuthenticated, user, loading } = useAuth();

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

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // First-time users must complete setup before accessing these routes
  if (requireFullAuth && user && !user.is_auth) {
    return <Navigate to="/first-time-setup" replace />;
  }

  return children;
};

export default ProtectedRoute; 