import React, { useEffect, useState } from 'react';
import '../App.css';
import './HomePage.css';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

function AllCoursesPage() {
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const coursesPerPage = 12;

  useEffect(() => {
    fetchCourses();
  }, [getAuthHeader]);

  const fetchCourses = () => {
    fetch('http://localhost:5000/api/courses', {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'application/json'
      }
    })
    .then(res => res.json())
    .then(data => {
      if (data.courses) {
        setCourses(data.courses);
      } else {
        setError('Failed to load courses');
      }
      setLoading(false);
    })
    .catch(err => {
      setError('Could not connect to backend');
      setLoading(false);
    });
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredCourses = courses.filter(course => {
    const matchesSearch = course.course_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         course.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDifficulty = selectedDifficulty === 'ALL' || course.difficulty_level === selectedDifficulty;
    return matchesSearch && matchesDifficulty;
  });

  // Pagination logic
  const totalPages = Math.ceil(filteredCourses.length / coursesPerPage);
  const startIndex = (currentPage - 1) * coursesPerPage;
  const endIndex = startIndex + coursesPerPage;
  const currentCourses = filteredCourses.slice(startIndex, endIndex);

  // Reset to first page when search or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedDifficulty]);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getDifficultyColor = (difficulty) => {
    switch(difficulty) {
      case 'Beginner': return 'is-success';
      case 'Intermediate': return 'is-warning';
      case 'Advanced': return 'is-danger';
      default: return 'is-info';
    }
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
            <div className="navbar-item">
              <input 
                className="input is-rounded" 
                type="search" 
                placeholder="Search courses..." 
                style={{ width: 180 }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <a className="navbar-item" onClick={() => navigate('/home')} style={{ cursor: 'pointer' }}>Dashboard</a>
            <a className="navbar-item is-active">All Courses</a>
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

      {/* Error Message */}
      {error && (
        <div className="container mt-2">
          <div className="notification is-danger is-light">
            <button className="delete" onClick={() => setError('')}></button>
            {error}
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="container mt-4">
        <div className="box home-overview-card">
          <div className="columns is-vcentered">
            <div className="column">
              <div className="is-size-4 has-text-weight-bold mb-2">All Courses</div>
              <div className="is-size-6 has-text-grey">Explore all available courses and enhance your skills</div>
            </div>
            <div className="column is-narrow">
              <div className="field">
                <div className="control">
                  <div className="select">
                    <select 
                      value={selectedDifficulty} 
                      onChange={(e) => setSelectedDifficulty(e.target.value)}
                    >
                      <option value="ALL">All Levels</option>
                      <option value="Casual">Casual</option>
                      <option value="Regular">Regular</option>
                      <option value="Intense">Intense</option>
                      
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filter Section */}
      <div className="container mt-4">
        <div className="box home-courses-card">
          <div className="columns is-vcentered">
            <div className="column">
              <div className="field">
                <div className="control has-icons-left">
                  <input 
                    className="input is-medium" 
                    type="search" 
                    placeholder="Search courses by name or description..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <span className="icon is-left">
                    <i className="fas fa-search"></i>
                  </span>
                </div>
              </div>
            </div>
            <div className="column is-narrow">
              <div className="field">
                <div className="control">
                  <div className="tags has-addons">
                    <span className="tag is-light">Total Courses:</span>
                    <span className="tag is-info">{filteredCourses.length}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Courses Grid */}
      <div className="container mt-4 mb-6">
        {loading ? (
          <div className="box home-courses-card has-text-centered">
            <div className="is-size-5 has-text-grey">Loading courses...</div>
          </div>
        ) : (
          <div className="box home-courses-card">
            <div className="columns is-multiline">
              {currentCourses.length > 0 ? (
                currentCourses.map((course) => (
                  <div className="column is-4" key={course.course_id}>
                    <div className="box home-course-row">
                      <div className="mb-3">
                        <div className="is-flex is-justify-content-space-between is-align-items-center mb-2">
                          <div className="is-size-6 has-text-weight-bold">{course.course_name}</div>
                          <span className={`tag ${getDifficultyColor(course.difficulty_level)}`}>
                            {course.difficulty_level}
                          </span>
                        </div>
                        <div className="is-size-7 has-text-grey mb-2">
                          {course.description}
                        </div>
                      </div>
                      
                      <div className="mb-3">
                        <div className="columns is-mobile is-vcentered">
                          <div className="column">
                            <div className="is-size-7">
                              <span className="icon is-small">
                                <i className="fas fa-clock"></i>
                              </span>
                              {course.total_hour} hours
                            </div>
                          </div>
                          <div className="column">
                            <div className="is-size-7">
                              <span className="icon is-small">
                                <i className="fas fa-book"></i>
                              </span>
                              {course.lesson_count} lessons
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="buttons">
                        <button className="button is-primary is-small is-fullwidth">
                          <span className="icon is-small">
                            <i className="fas fa-play"></i>
                          </span>
                          <span>More Detail..</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="column is-12">
                  <div className="has-text-centered">
                    <div className="is-size-5 has-text-grey mb-2">No courses found</div>
                    <div className="is-size-6 has-text-grey">
                      {searchTerm || selectedDifficulty !== 'ALL' 
                        ? 'Try adjusting your search or filter criteria' 
                        : 'No courses are available at the moment'}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="has-text-centered mt-5">
                <nav className="pagination is-centered" role="navigation">
                  <button 
                    className="pagination-previous" 
                    disabled={currentPage === 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                  >
                    Previous
                  </button>
                  <button 
                    className="pagination-next" 
                    disabled={currentPage === totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                  >
                    Next
                  </button>
                  <ul className="pagination-list">
                    {/* First page */}
                    {currentPage > 3 && (
                      <>
                        <li>
                          <button 
                            className="pagination-link" 
                            onClick={() => handlePageChange(1)}
                          >
                            1
                          </button>
                        </li>
                        {currentPage > 4 && (
                          <li><span className="pagination-ellipsis">&hellip;</span></li>
                        )}
                      </>
                    )}

                    {/* Pages around current page */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => 
                        page >= Math.max(1, currentPage - 2) && 
                        page <= Math.min(totalPages, currentPage + 2)
                      )
                      .map(page => (
                        <li key={page}>
                          <button 
                            className={`pagination-link ${page === currentPage ? 'is-current' : ''}`}
                            onClick={() => handlePageChange(page)}
                          >
                            {page}
                          </button>
                        </li>
                      ))
                    }

                    {/* Last page */}
                    {currentPage < totalPages - 2 && (
                      <>
                        {currentPage < totalPages - 3 && (
                          <li><span className="pagination-ellipsis">&hellip;</span></li>
                        )}
                        <li>
                          <button 
                            className="pagination-link" 
                            onClick={() => handlePageChange(totalPages)}
                          >
                            {totalPages}
                          </button>
                        </li>
                      </>
                    )}
                  </ul>
                </nav>
                
                {/* Page info */}
                <div className="has-text-grey is-size-7 mt-2">
                  Showing {startIndex + 1}-{Math.min(endIndex, filteredCourses.length)} of {filteredCourses.length} courses
                  {totalPages > 1 && ` (Page ${currentPage} of ${totalPages})`}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AllCoursesPage; 