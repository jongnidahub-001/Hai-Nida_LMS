import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import projectLogo from '../assets/project_logo.png';
import './Header.css';

function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav className="navbar app-header" role="navigation">
      <div className="navbar-brand">
        <div className="navbar-item">
          <img src={projectLogo} alt="Project Logo" className="app-logo" />
          <span className="navbar-brand-text has-text-weight-bold is-size-5 ml-2">Hi HR</span>
        </div>
      </div>
      <div className="navbar-menu">
        <div className="navbar-start">
          <div className="navbar-item">
            <input className="input is-rounded search-input" type="search" placeholder="Search" />
          </div>
          <a className={`navbar-item navbar-link-item ${isActive('/home') ? 'is-active' : ''}`} href="#dashboard" onClick={(e) => { e.preventDefault(); navigate('/home'); }} style={{ cursor: 'pointer' }}>Dashboard</a>
          <a className={`navbar-item navbar-link-item ${isActive('/courses') ? 'is-active' : ''}`} href="#courses" onClick={(e) => { e.preventDefault(); navigate('/courses'); }} style={{ cursor: 'pointer' }}>All Courses</a>
          <a className="navbar-item navbar-link-item" href="#quiz">Take a Quiz</a>
          <a className="navbar-item navbar-link-item" href="#about">About us</a>
        </div>
        <div className="navbar-end">
          <div className="navbar-item">
            <button className="button logout-button" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Header; 