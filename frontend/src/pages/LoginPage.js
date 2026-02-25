import React, { useState, useEffect } from 'react';
import '../App.css';
import './LoginPage.css';
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
    <div className="columns login-page-layout" style={{ minHeight: '100vh', margin: 0 }}>
      {/* Sidebar: Developer Info */}
      <div className="column is-narrow p-0" style={{ minWidth: sidebarCollapsed ? '60px' : '260px', maxWidth: sidebarCollapsed ? '60px' : '260px', transition: 'min-width 0.2s, max-width 0.2s' }}>
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(c => !c)} />
      </div>
      {/* Main content: Left branding | Right form */}
      <div className="column p-0 is-flex" style={{ flex: 1, minWidth: 0 }}>
        {/* Left section: Branding (~65%) */}
        <div className="login-left-section">
          <div className="login-left-inner">
            <img src={`${process.env.PUBLIC_URL}/project_logo.png`} alt="Project Logo" className="login-project-logo" />
            <h1 className="login-main-title">Agentic AI for Personalized Training and Development: Accelerating Learning and Closing Skill Gaps</h1>
            <p className="login-description">The NLP, LLM, and Generative AI Initiatives at NIDA Hub Natural Language Processing (NLP), Large Language Models (LLMs), and Generative AI: The NLP, LLM, and Gen AI projects and use cases to support the analysis and generation of human language for understanding and enhancement of human capabilities.</p>
            <div className="login-logos-row">
              <img
                src={`${process.env.PUBLIC_URL}/project_logo.png`}
                alt="Hi HR"
                className="login-nida-logo"
                style={{ width: '80px' }}
              />
              <img
                src={`${process.env.PUBLIC_URL}/nida_logo.png`}
                alt="NIDA Business School"
                className="login-nida-logo"
                style={{ width: '100px' }}
              />
            </div>
            <p className="login-copyright">Copyright © 2026 NIDA Business School. All rights reserved.</p>
          </div>
        </div>
        {/* Right section: Sign in card (~35%) */}
        <div className="login-right-section">
          <div className="login-form-card">
            <h2 className="login-signin-title">Sign in</h2>
            <form onSubmit={handleSubmit} className="login-form">
              <div className="field">
                <label className="label">Username</label>
                <div className="control">
                  <input 
                    className="input" 
                    type="text"
                    autoComplete="username"
                    value={email} 
                    onChange={e => setEmail(e.target.value)} 
                    placeholder="Enter username"
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
                    autoComplete="current-password"
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    placeholder="•••••••"
                    required 
                    disabled={isLoading}
                  />
                </div>
              </div>
              {error && <p className="help is-danger">{error}</p>}
              <div className="field">
                <div className="control has-text-centered">
                  <button 
                    className={`button login-signin-btn ${isLoading ? 'is-loading' : ''}`} 
                    type="submit"
                    disabled={isLoading}
                  >
                    Sign In
                  </button>
                </div>
              </div>
            </form>
            <p className="login-demo-text is-size-7">
              Demo: admin@admin.com / admin
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
