import React, { useEffect, useState, useCallback } from 'react';
import '../App.css';
import './HomePage.css';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';

function HomePage() {
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [myCourses, setMyCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('ALL');

  const fetchMyCourses = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:5000/api/my-courses', {
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
      const response = await fetch('http://localhost:5000/api/courses', {
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

    // Fetch user's enrolled courses
    fetchMyCourses();
    
    // Fetch all courses for the slide
    fetchAllCourses();
  }, [getAuthHeader, fetchMyCourses, fetchAllCourses]);

  // Auto-slide effect for featured courses
  useEffect(() => {
    if (allCourses.length > 1) {
      const slideInterval = setInterval(() => {
        if (!isAnimating) {
          setIsAnimating(true);
          setTimeout(() => {
            setCurrentSlide((prev) => (prev + 1) % allCourses.length);
            setIsAnimating(false);
          }, 150);
        }
              }, 7000); // Change slide every 7 seconds

      return () => clearInterval(slideInterval);
    }
  }, [allCourses.length, isAnimating]);

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
    if (course.enrollment_status === 'Complete') return 'Complete';
    if (course.progress.progress_percentage > 0) return 'Resume';
    return 'Learn';
  };

  const getButtonStyle = (course) => {
    if (course.enrollment_status === 'Complete') {
      return {
        backgroundColor: '#4A4A4A',
        color: '#FFFFFF !important',
        border: 'none'
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
    if (allCourses.length > 0 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide((prev) => (prev + 1) % allCourses.length);
        setIsAnimating(false);
      }, 150);
    }
  };

  const prevSlide = () => {
    if (allCourses.length > 0 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide((prev) => (prev - 1 + allCourses.length) % allCourses.length);
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
              <div className="is-size-5 has-text-weight-bold mb-2">MBA Program</div>
              <div className="is-size-7 mb-2">Stay focused and connected—your MBA journey continues. With every activity, project, and lesson, you're getting closer to your goals. Follow your schedule and keep up with MBA Program activities.</div>
              <div className="is-size-7 mb-2">John Doe <span className="tag is-info is-light ml-2">MBA Preview</span></div>
              <div className="is-size-7">Course update</div>
            </div>
          </div>
          <div className="column">
            <div className="box home-overview-card" style={{ backgroundColor: '#2c2c2c', border: 'none', height: '100%' }}>
              <div className="is-size-5 has-text-weight-bold mb-2" style={{ color: '#ffdd57' }}>Featured Courses</div>
              {allCourses.length > 0 ? (
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
                        <h4 className="is-size-5 has-text-weight-bold has-text-white">{allCourses[currentSlide]?.course_name}</h4>
                        <span className={`tag ${getDifficultyColor(allCourses[currentSlide]?.difficulty_level)}`}>
                          {allCourses[currentSlide]?.difficulty_level}
                        </span>
                      </div>
                      
                      <p className="is-size-7 has-text-light" style={{ lineHeight: '1.4', color: '#b3b3b3' }}>
                        {allCourses[currentSlide]?.description || 'Comprehensive course designed to enhance your skills and knowledge.'}
                      </p>
                      
                      <div className="is-flex is-justify-content-center is-align-items-center" style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}>
                        <div className="course-stats" style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}>
                          <span className="tag mr-2" style={{ backgroundColor: '#fff', color: '#000', border: 'none', boxShadow: 'none' }}>
                            <i className="fas fa-clock mr-1"></i>
                            {allCourses[currentSlide]?.total_hour}h
                          </span>
                          <span className="tag" style={{ backgroundColor: '#fff', color: '#000', border: 'none', boxShadow: 'none' }}>
                            <i className="fas fa-book mr-1"></i>
                            {allCourses[currentSlide]?.lesson_count} lessons
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
                        onClick={() => navigate(`/course/${allCourses[currentSlide]?.course_id}`)}
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
                    {allCourses.map((_, index) => (
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
              <li className={activeTab === 'Learn' ? 'is-active' : ''}><a href="#learn" onClick={(e) => { e.preventDefault(); setActiveTab('Learn'); }}>Learn</a></li>
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
                        <div className="is-size-7 has-text-grey">{course.difficulty_level.toUpperCase()}</div>
                      </div>
                    </div>
                  </div>
                  <div className="column">
                    <progress 
                      className="progress is-info is-small" 
                      value={course.progress.progress_percentage} 
                      max="100" 
                      style={{ height: 6 }}
                    ></progress>
                    <div className="is-size-7 has-text-grey mt-1">
                      {formatProgress(course.progress)} • {course.total_hour} hours total
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
