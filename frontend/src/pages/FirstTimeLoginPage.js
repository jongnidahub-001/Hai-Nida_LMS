import React, { useState, useEffect } from 'react';
import '../App.css';
import './LoginPage.css';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAlert } from '../contexts/AlertContext';
import { API_BASE_URL } from '../config/api';

import Sidebar from '../component/Sidebar';

function FirstTimeLoginPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { user, getAuthHeader, logout } = useAuth();
  const { showAlert } = useAlert();

  // Redirect if user is already authenticated or not logged in
  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (user.is_auth) {
      navigate('/home');
      return;
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!username.trim()) {
      setError('Username is required');
      return;
    }
    if (!fullName.trim()) {
      setError('Full name is required');
      return;
    }
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/first-time-setup`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: username.trim(),
          full_name: fullName.trim(),
          new_password: newPassword
        })
      });

      const data = await response.json();

      if (data.success) {
        showAlert('Profile updated successfully! Please login again with your new credentials.', 'success');
        logout();
        navigate('/login');
      } else {
        setError(data.message || 'Failed to update profile');
      }
    } catch (error) {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  if (!user || user.is_auth) {
    return null; // Don't render anything while redirecting
  }

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
              <div className="column is-two-fifths is-flex is-flex-direction-column is-align-items-center is-justify-content-center" style={{ borderRight: '1px solid var(--medium-grey)', backgroundColor: 'white' }}>
                <img src={`${process.env.PUBLIC_URL}/project_logo.png`} alt="Project Logo" style={{ width: '120px', marginBottom: '1rem' }} />
                <h2 className="title is-4" style={{ color: 'var(--primary-black)' }}>First Time Setup</h2>
                <p className="subtitle is-6" style={{ color: 'var(--primary-black)', textAlign: 'center' }}>
                  Welcome! Please complete your profile setup and change your password.
                </p>
                <div className="notification is-info is-light mt-3">
                  <p className="is-size-7">
                    <strong>Email:</strong> {user?.email}
                  </p>
                </div>
              </div>
              {/* Right side: Setup Form */}
              <div className="column login-form-section">
                <form onSubmit={handleSubmit} className="login-form">
                  <div className="field">
                    <label className="label">Username</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="text" 
                        value={username} 
                        onChange={e => setUsername(e.target.value)} 
                        required 
                        disabled={isLoading}
                        placeholder="Enter your username"
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label">Full Name</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="text" 
                        value={fullName} 
                        onChange={e => setFullName(e.target.value)} 
                        required 
                        disabled={isLoading}
                        placeholder="Enter your full name"
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label">New Password</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="password" 
                        value={newPassword} 
                        onChange={e => setNewPassword(e.target.value)} 
                        required 
                        disabled={isLoading}
                        placeholder="Enter new password (min 6 characters)"
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label">Confirm Password</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="password" 
                        value={confirmPassword} 
                        onChange={e => setConfirmPassword(e.target.value)} 
                        required 
                        disabled={isLoading}
                        placeholder="Confirm your new password"
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
                        {isLoading ? 'Updating...' : 'Complete Setup'}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FirstTimeLoginPage; 