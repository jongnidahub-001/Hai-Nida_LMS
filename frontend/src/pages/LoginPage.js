import React, { useState, useEffect } from 'react';
import '../App.css';
import './LoginPage.css';
import projectLogo from '../assets/project_logo.png';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

import Sidebar from '../component/Sidebar';

function LoginPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login, isAuthenticated, user } = useAuth();

  // Redirect to appropriate page if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      if (!user?.is_auth) {
        navigate('/first-time-setup');
      } else if (user?.role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/home');
      }
    }
  }, [isAuthenticated, user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login(email, password);
      if (result.success) {
        // Check if user needs first-time setup
        if (!result.user.is_auth) {
          navigate('/first-time-setup');
        } else if (result.user.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/home');
        }
      } else {
        setError(result.message || 'Login failed');
      }
    } catch (error) {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="columns" style={{ minHeight: '100vh' }}>
      {/* Sidebar: Developer Info */}
      <div className="column is-narrow p-0" style={{ minWidth: sidebarCollapsed ? '60px' : '260px', maxWidth: sidebarCollapsed ? '60px' : '260px', transition: 'min-width 0.2s, max-width 0.2s' }}>
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(c => !c)} />
      </div>
      <div className="column is-flex is-align-items-center is-justify-content-center" style={{ background: 'var(--light-grey)' }}>
        <div className="card" style={{ minWidth: '600px', maxWidth: '1000px', margin: 'auto', border: '1px solid var(--medium-grey)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <div className="card-content">
            <div className="columns">
              {/* Left side: Logo and Info */}
              <div className="column is-three-fifths is-flex is-flex-direction-column is-align-items-center is-justify-content-center" style={{ borderRight: '1px solid var(--medium-grey)', backgroundColor: 'white' }}>
                <img src={projectLogo} alt="Project Logo" style={{ width: '120px', marginBottom: '1rem' }} />
                <h2 className="title is-4" style={{ color: 'var(--primary-black)' }}>Welcome Back!</h2>
                <p className="subtitle is-6" style={{ color: 'var(--primary-black)' }}>Please login to your account</p>
              </div>
              {/* Right side: Login Form */}
              <div className="column login-form-section">
                <form onSubmit={handleSubmit} className="login-form">
                  <div className="field">
                    <label className="label">Email</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="email" 
                        value={email} 
                        onChange={e => setEmail(e.target.value)} 
                        required 
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label">Password</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="password" 
                        value={password} 
                        onChange={e => setPassword(e.target.value)} 
                        required 
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                  {error && <p className="help is-danger">{error}</p>}
                  <div className="field is-grouped is-grouped-right">
                    <div className="control">
                      <button 
                        className={`button is-primary ${isLoading ? 'is-loading' : ''}`} 
                        type="submit"
                        disabled={isLoading}
                      >
                        {isLoading ? 'Logging in...' : 'Login'}
                      </button>
                    </div>
                  </div>
                </form>
                <div className="has-text-centered mt-4">
                  <p className="is-size-7 login-demo-text">
                    Demo credentials: admin@admin.com / admin
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
