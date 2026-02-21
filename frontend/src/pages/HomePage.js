import React, { useEffect, useState, useCallback } from 'react';
import '../App.css';
import './HomePage.css';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';

function HomePage() {
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [myCourses, setMyCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [recommendationCourses, setRecommendationCourses] = useState([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('ALL');

  const fetchMyCourses = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/my-courses`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setMyCourses(data.courses || []);
      } else {
        console.error('Failed to fetch courses');
      }
    } catch (error) {
      console.error('Error fetching courses:', error);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  const fetchAllCourses = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/courses`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAllCourses(data.courses || []);
      } else {
        console.error('Failed to fetch all courses');
      }
    } catch (error) {
      console.error('Error fetching all courses:', error);
    }
  }, [getAuthHeader]);

  const fetchRecommendationCourses = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recommendation-courses`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setRecommendationCourses((data.courses || []).filter(c => c));
      } else {
        setRecommendationCourses([]);
      }
    } catch (error) {
      console.error('Error fetching recommendation courses:', error);
      setRecommendationCourses([]);
    }
  }, [getAuthHeader]);

  useEffect(() => {
    // Test the protected API endpoint
    fetch(`${API_BASE_URL}/api/hello`, {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'application/json'
      }
    })
    .then(res => res.json())
    .then(data => setMessage(data.message))
    .catch(() => setMessage('Could not connect to backend.'));

    // Fetch user's enrolled courses
    fetchMyCourses();
    
    // Fetch all courses and recommendation courses for Featured Courses
    fetchAllCourses();
    fetchRecommendationCourses();
  }, [getAuthHeader, fetchMyCourses, fetchAllCourses, fetchRecommendationCourses]);

  // Featured Courses: use recommendation from quiz if available, else all courses
  const featuredCourses = recommendationCourses.length > 0 ? recommendationCourses : allCourses;

  // Reset slide index when featured courses change (avoid out-of-bounds)
  useEffect(() => {
    setCurrentSlide(prev => Math.min(prev, Math.max(0, featuredCourses.length - 1)));
  }, [featuredCourses.length]);

  // Auto-slide effect for featured courses
  useEffect(() => {
    if (featuredCourses.length > 1) {
      const slideInterval = setInterval(() => {
        if (!isAnimating) {
          setIsAnimating(true);
          setTimeout(() => {
            setCurrentSlide((prev) => (prev + 1) % featuredCourses.length);
            setIsAnimating(false);
          }, 150);
        }
      }, 7000); // Change slide every 7 seconds

      return () => clearInterval(slideInterval);
    }
  }, [featuredCourses.length, isAnimating]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getFilteredCourses = () => {
    if (activeTab === 'ALL') return myCourses;
    if (activeTab === 'Learn') return myCourses.filter(course => course.enrollment_status === 'Learning');
    if (activeTab === 'Resume') return myCourses.filter(course => course.progress.progress_percentage > 0 && course.enrollment_status === 'Learning');
    if (activeTab === 'Complete') return myCourses.filter(course => course.enrollment_status === 'Complete');
    return myCourses;
  };

  const getButtonText = (course) => {
    if (course.enrollment_status === 'Complete') {
      return 'Completed';
    }
    if (course.progress.progress_percentage > 0) {
      return 'Resume';
    }
    return 'Learn';
  };

  const getButtonStyle = (course) => {
    if (course.enrollment_status === 'Complete') {
      return {
        backgroundColor: '#48c774',
        color: '#000',
        border: 'none',
        fontWeight: '500'
      };
    }
    if (course.progress.progress_percentage > 0) {
      return {
        backgroundColor: '#FFC107',
        color: '#000',
        border: 'none',
        fontWeight: '500'
      };
    }
    return {
      backgroundColor: 'white',
      color: '#000',
      border: '1px solid #ddd'
    };
  };

  const formatProgress = (progress) => {
    const completed = progress.completed_lessons || 0;
    const total = progress.total_lessons || 0;
    return `${completed} lessons completed / ${total} lessons total`;
  };

  const nextSlide = () => {
    if (featuredCourses.length > 0 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide((prev) => (prev + 1) % featuredCourses.length);
        setIsAnimating(false);
      }, 150);
    }
  };

  const prevSlide = () => {
    if (featuredCourses.length > 0 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide((prev) => (prev - 1 + featuredCourses.length) % featuredCourses.length);
        setIsAnimating(false);
      }, 150);
    }
  };

  const getDifficultyColor = (level) => {
    switch(level?.toLowerCase()) {
      case 'beginner': return 'is-success';
      case 'intermediate': return 'is-warning';
      case 'advanced': return 'is-danger';
      default: return 'is-info';
    }
  };

  return (
    <div className="home-bg">
      {/* Header */}
      <Header />

      {/* Backend Connection Status */}
      {/*message && (
        <div className="container mt-2">
          <div className="notification is-info is-light">
            <button className="delete" onClick={() => setMessage('')}></button>
            {message}
          </div>
        </div>
      )*/}

      {/* Overview & Schedule */}
      <div className="container mt-4">
        <div className="columns">
          <div className="column">
            <div className="box home-overview-card" style={{ height: '100%' }}>
              <div className="is-size-5 has-text-weight-bold mb-2">About Hi HR</div>
              <div className="is-size-7 mb-2">Hi HR is a Learning Management System (LMS) for professional development. Browse and enroll in courses, study lessons with AI-powered chat support, and take quizzes to test your knowledge.</div>
              <div className="is-size-7 mb-2"><strong>Key features:</strong> Course catalog · AI tutoring · Progress tracking · Quizzes</div>
              <div className="is-size-7">Go to <strong>All Courses</strong> to explore and enroll in available courses.</div>
            </div>
          </div>
          <div className="column">
            <div className="box home-overview-card" style={{ backgroundColor: '#2c2c2c', border: 'none', height: '100%' }}>
              <div className="is-size-5 has-text-weight-bold mb-2" style={{ color: '#ffdd57' }}>
                Featured Courses
                {recommendationCourses.length > 0 && (
                  <span className="tag is-warning is-light ml-2" style={{ fontSize: '0.65rem' }}>Recommended for you</span>
                )}
              </div>
              {featuredCourses.length > 0 ? (
                <div className="course-slide-container" style={{ position: 'relative', minHeight: '200px' }}>
                  <div className="course-slide" style={{ 
                    padding: '20px', 
                    backgroundColor: '#1a1a1a', 
                    borderRadius: '8px',
                    transition: 'all 0.3s ease',
                    transform: isAnimating ? 'translateX(10px)' : 'translateX(0px)',
                    opacity: isAnimating ? 0.6 : 1
                  }}>
                    <div className="course-slide-content">
                      <div className="is-flex is-justify-content-space-between is-align-items-start mb-3">
                        <h4 className="is-size-5 has-text-weight-bold has-text-white">{featuredCourses[currentSlide]?.course_name}</h4>
                        <span className={`tag ${getDifficultyColor(featuredCourses[currentSlide]?.difficulty_level)}`}>
                          {featuredCourses[currentSlide]?.difficulty_level}
                        </span>
                      </div>
                      
                      <p className="is-size-7 has-text-light" style={{ lineHeight: '1.4', color: '#b3b3b3' }}>
                        {featuredCourses[currentSlide]?.description || 'Comprehensive course designed to enhance your skills and knowledge.'}
                      </p>
                      
                      <div className="is-flex is-justify-content-center is-align-items-center" style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}>
                        <div className="course-stats" style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}>
                          <span className="tag mr-2" style={{ backgroundColor: '#fff', color: '#000', border: 'none', boxShadow: 'none' }}>
                            <i className="fas fa-clock mr-1"></i>
                            {featuredCourses[currentSlide]?.total_hour}h
                          </span>
                          <span className="tag" style={{ backgroundColor: '#fff', color: '#000', border: 'none', boxShadow: 'none' }}>
                            <i className="fas fa-book mr-1"></i>
                            {featuredCourses[currentSlide]?.lesson_count} lessons
                          </span>
                        </div>
                      </div>
                      
                      <button 
                        className="button is-small is-fullwidth"
                        style={{
                          backgroundColor: '#ffdd57',
                          color: '#000',
                          border: 'none',
                          fontWeight: '500'
                        }}
                        onClick={() => navigate(`/course/${featuredCourses[currentSlide]?.course_id}`)}
                      >
                        View Course
                      </button>
                    </div>
                  </div>
                  
                  {/* Navigation buttons */}
                  <button 
                    className="button is-small" 
                    onClick={prevSlide}
                    style={{ 
                      position: 'absolute', 
                      left: '5px', 
                      top: '50%', 
                      transform: 'translateY(-50%)',
                      backgroundColor: '#fff',
                      color: '#000',
                      border: '1px solid #ddd',
                      borderRadius: '50%',
                      width: '30px',
                      height: '30px'
                    }}
                  >
                    <i className="fas fa-chevron-left"></i>
                  </button>
                  
                  <button 
                    className="button is-small" 
                    onClick={nextSlide}
                    style={{ 
                      position: 'absolute', 
                      right: '5px', 
                      top: '50%', 
                      transform: 'translateY(-50%)',
                      backgroundColor: '#fff',
                      color: '#000',
                      border: '1px solid #ddd',
                      borderRadius: '50%',
                      width: '30px',
                      height: '30px'
                    }}
                  >
                    <i className="fas fa-chevron-right"></i>
                  </button>
                  
                  {/* Slide indicators */}
                  <div className="slide-indicators" style={{ textAlign: 'center', marginTop: '10px' }}>
                    {featuredCourses.map((_, index) => (
                      <span 
                        key={index}
                        className="tag is-small mr-1"
                        style={{ 
                          cursor: 'pointer',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          padding: '0',
                          backgroundColor: index === currentSlide ? '#ffdd57' : '#555',
                          border: 'none'
                        }}
                        onClick={() => {
                          if (!isAnimating && index !== currentSlide) {
                            setIsAnimating(true);
                            setTimeout(() => {
                              setCurrentSlide(index);
                              setIsAnimating(false);
                            }, 150);
                          }
                        }}
                      ></span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="has-text-centered" style={{ padding: '40px' }}>
                  <div className="is-size-7 has-text-grey">Loading courses...</div>
                </div>
              )}
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
              <li className={activeTab === 'ALL' ? 'is-active' : ''}><a href="#all" onClick={(e) => { e.preventDefault(); setActiveTab('ALL'); }}>ALL</a></li>
              <li className={activeTab === 'Resume' ? 'is-active' : ''}><a href="#resume" onClick={(e) => { e.preventDefault(); setActiveTab('Resume'); }}>Resume</a></li>
              <li className={activeTab === 'Complete' ? 'is-active' : ''}><a href="#complete" onClick={(e) => { e.preventDefault(); setActiveTab('Complete'); }}>Complete</a></li>
            </ul>
          </div>
          
          {loading ? (
            <div className="has-text-centered">
              <div className="is-size-6">Loading courses...</div>
            </div>
          ) : getFilteredCourses().length === 0 ? (
            <div className="has-text-centered">
              <div className="is-size-6 has-text-grey">No courses found</div>
            </div>
          ) : (
            getFilteredCourses().map((course) => (
              <div className="box home-course-row mb-2" key={course.course_id}>
                <div className="columns is-vcentered">
                  <div className="column is-3">
                    <div className="is-flex is-align-items-center">
                      <span className="icon is-medium mr-2"><i className="fas fa-book"></i></span>
                      <div>
                        <div className="is-size-7 has-text-weight-bold">{course.course_name}</div>
                        <div className="is-size-7 has-text-grey">{course.difficulty_level?.toUpperCase()}</div>
                      </div>
                    </div>
                  </div>
                  <div className="column">
                    <progress 
                      className="progress is-info is-small" 
                      value={course.progress?.progress_percentage || 0} 
                      max="100" 
                      style={{ height: 6 }}
                    ></progress>
                    <div className="is-size-7 has-text-grey mt-1">
                      {formatProgress(course.progress || {})} • {course.total_hour} hours total
                    </div>
                  </div>
                  <div className="column is-2">
                    <button 
                      className="button is-small is-fullwidth"
                      style={getButtonStyle(course)}
                      onClick={() => navigate(`/course/${course.course_id}`)}
                    >
                      {getButtonText(course)}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* My Quiz Status */}
      <div className="container mt-4 mb-6">
        <div className="box home-courses-card" style={{ borderRadius: '12px', background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div className="is-size-5 has-text-weight-bold mb-3">MY QUIZ STATUS</div>
          <div className="columns is-multiline">
            {!loading && myCourses.length === 0 ? (
              <div className="column is-12">
                <div className="has-text-centered is-size-6 has-text-grey">No quiz data</div>
              </div>
            ) : loading ? (
              <div className="column is-12">
                <div className="has-text-centered is-size-6 has-text-grey">Loading...</div>
              </div>
            ) : (
              myCourses.map((course) => {
                const qs = course.quiz_status || {};
                const quizAttempted = qs.attempted === true;
                const quizScoreStr = quizAttempted && qs.score != null && qs.total_points != null 
                  ? `${qs.score} / ${qs.total_points}` : '-';
                const quizStatusLabel = qs.status || 'No Quiz';
                const quizBg = quizStatusLabel === 'Completed' ? '#48c774' : (quizStatusLabel === 'Not Attempted' ? '#ffe082' : '#e0e0e0');
                return (
                  <div className="column is-4" key={course.course_id}>
                    <div 
                      className="box home-course-row" 
                      style={{ 
                        height: '100%', 
                        display: 'flex', 
                        flexDirection: 'column', 
                        borderRadius: '10px', 
                        background: '#fff', 
                        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
                        cursor: quizAttempted ? 'pointer' : 'default',
                        transition: 'box-shadow 0.2s ease'
                      }}
                      onClick={() => quizAttempted && navigate(`/course/${course.course_id}/quiz-result`)}
                      onMouseEnter={(e) => { if (quizAttempted) e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)'; }}
                      onMouseLeave={(e) => { if (quizAttempted) e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'; }}
                    >
                      <div className="mb-2">
                        <div className="is-size-6 has-text-weight-bold">{course.course_name}</div>
                      </div>
                      <div className="mb-2">
                        <span className="tag is-medium" style={{ backgroundColor: quizBg, color: '#222' }}>{quizStatusLabel}</span>
                      </div>
                      <div className="is-size-7 has-text-grey">Score: <span className="has-text-weight-bold" style={{ color: '#222' }}>{quizScoreStr}</span></div>
                      {quizAttempted && (
                        <div className="mt-2 is-size-7 has-text-info">
                          <span className="icon is-small"><i className="fas fa-chart-bar"></i></span> Click to view result
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
