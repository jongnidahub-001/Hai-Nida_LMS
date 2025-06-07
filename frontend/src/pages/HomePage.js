import React, { useEffect, useState } from 'react';
import '../App.css';
import './HomePage.css';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

function HomePage() {
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Test the protected API endpoint
    fetch('http://localhost:5000/api/hello', {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'application/json'
      }
    })
    .then(res => res.json())
    .then(data => setMessage(data.message))
    .catch(() => setMessage('Could not connect to backend.'));
  }, [getAuthHeader]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="home-bg">
      {/* Header */}
      <nav className="navbar is-white home-navbar" role="navigation">
        <div className="navbar-brand">
          <span className="navbar-item has-text-weight-bold is-size-5">Hi HR</span>
        </div>
        <div className="navbar-menu">
          <div className="navbar-start">
            <div className="navbar-item"><input className="input is-rounded" type="search" placeholder="Search" style={{ width: 180 }} /></div>
            <a className="navbar-item is-active">Dashboard</a>
            <a className="navbar-item" onClick={() => navigate('/courses')} style={{ cursor: 'pointer' }}>All Courses</a>
            <a className="navbar-item">Take a Quiz</a>
            <a className="navbar-item">About us</a>
          </div>
          <div className="navbar-end">
            <div className="navbar-item has-dropdown is-hoverable">
              <a className="navbar-link">
                Welcome, {user?.username || 'User'}
              </a>
              <div className="navbar-dropdown">
                <a className="navbar-item">Profile</a>
                <a className="navbar-item">Settings</a>
                <hr className="navbar-divider" />
                <a className="navbar-item" onClick={handleLogout} style={{ cursor: 'pointer' }}>
                  Logout
                </a>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Backend Connection Status */}
      {message && (
        <div className="container mt-2">
          <div className="notification is-info is-light">
            <button className="delete" onClick={() => setMessage('')}></button>
            {message}
          </div>
        </div>
      )}

      {/* Overview & Schedule */}
      <div className="container mt-4">
        <div className="columns">
          <div className="column">
            <div className="box home-overview-card">
              <div className="is-size-5 has-text-weight-bold mb-2">MBA Program</div>
              <div className="is-size-7 mb-2">Stay focused and connected—your MBA journey continues. With every activity, project, and lesson, you're getting closer to your goals. Follow your schedule and keep up with MBA Program activities.</div>
              <div className="is-size-7 mb-2">John Doe <span className="tag is-info is-light ml-2">MBA Preview</span></div>
              <div className="is-size-7">Course update</div>
            </div>
          </div>
          <div className="column">
            <div className="box home-schedule-card">
              <div className="is-size-6 has-text-weight-bold mb-2">Schedule</div>
              <div className="is-size-7 mb-2">November 2024</div>
              <div className="columns is-mobile is-multiline is-gapless">
                {[1,2,8,9,15,16,20,21,28,29].map(day => (
                  <div className="column is-one-fifth has-text-centered" key={day}>
                    <div className="box home-schedule-day">{day}<br /><span className="is-size-7">Tue</span></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* My Courses */}
      <div className="container mt-4">
        <div className="box home-courses-card">
          <div className="is-size-5 has-text-weight-bold mb-3">MY COURSES</div>
          <div className="tabs is-toggle is-small mb-2">
            <ul>
              <li className="is-active"><a>ALL</a></li>
              <li><a>Learn</a></li>
              <li><a>Resume</a></li>
              <li><a>Complete</a></li>
            </ul>
          </div>
          {[0,1,2,3].map((idx) => (
            <div className="box home-course-row mb-2" key={idx}>
              <div className="columns is-vcentered">
                <div className="column is-2">
                  <div className="is-flex is-align-items-center">
                    <span className="icon is-medium mr-2"><i className="fas fa-book"></i></span>
                    <span className="is-size-7">MBA - FULL TIME</span>
                  </div>
                  <div className="is-size-7 has-text-grey">ABC: Business Innovation</div>
                </div>
                <div className="column">
                  <progress className="progress is-info is-small" value={idx === 0 ? 80 : idx === 1 ? 40 : 0} max="100" style={{ height: 6 }}></progress>
                  <div className="is-size-7 has-text-grey mt-1">6 hours attended / 8 hours total</div>
                </div>
                <div className="column is-2">
                  <button className={`button is-${idx === 0 ? 'primary' : idx === 1 ? 'info' : 'light'} is-small is-fullwidth`}>{idx === 0 ? 'Resume' : idx === 1 ? 'Learn' : 'Complete'}</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Classmate */}
      <div className="container mt-4 mb-6">
        <div className="box home-classmate-card">
          <div className="is-size-5 has-text-weight-bold mb-3">CLASSMATE</div>
          <div className="columns is-mobile is-multiline">
            {[0,1,2,3,4,5].map(idx => (
              <div className="column is-2 has-text-centered" key={idx}>
                <div className="home-classmate-avatar mb-2"></div>
                <div className="is-size-7 has-text-weight-bold">John Doe</div>
                <div className="is-size-7">Sasin, Student</div>
                <div className="is-size-7 has-text-grey">ex.sasinproject@actor<br />02-xxxxxxx</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
