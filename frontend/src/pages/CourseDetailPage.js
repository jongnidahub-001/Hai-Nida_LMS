import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './CourseDetailPage.css';
import Header from '../components/Header';

function CourseDetailPage() {
  const { courseId } = useParams();
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  
  const [courseData, setCourseData] = useState(null);
  const [courseContent, setCourseContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeLesson, setActiveLesson] = useState(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollmentSuccess, setEnrollmentSuccess] = useState(false);

  useEffect(() => {
    fetchCourseDetails();
    fetchCourseContent();
  }, [courseId]);

  const fetchCourseDetails = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/course-progress/${courseId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setCourseData(data);
        // Set first lesson as active by default
        if (data.lessons && data.lessons.length > 0) {
          setActiveLesson(data.lessons[0]);
        }
      } else {
        setError('Failed to fetch course details');
      }
    } catch (error) {
      console.error('Error fetching course details:', error);
      setError('Error loading course details');
    } finally {
      setLoading(false);
    }
  };

  const fetchCourseContent = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/course-content/${courseId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setCourseContent(data.course_content);
        }
      }
    } catch (error) {
      console.error('Error fetching course content:', error);
      // Don't set error state for content fetch failure, use fallback content
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleLessonClick = (lesson) => {
    setActiveLesson(lesson);
  };

  const handleEnrollment = async () => {
    setEnrolling(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:5000/api/enroll', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          course_id: courseId
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setEnrollmentSuccess(true);
        // Refresh course data to get updated enrollment status
        await fetchCourseDetails();
        // Show success message briefly
        setTimeout(() => setEnrollmentSuccess(false), 3000);
      } else {
        setError(data.message || 'Failed to enroll in course');
      }
    } catch (error) {
      console.error('Error enrolling in course:', error);
      setError('Error enrolling in course. Please try again.');
    } finally {
      setEnrolling(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Complete':
        return <span className="icon has-text-success"><i className="fas fa-check-circle"></i></span>;
      case 'In Progress':
        return <span className="icon has-text-info"><i className="fas fa-play-circle"></i></span>;
      default:
        return <span className="icon has-text-grey-light"><i className="far fa-circle"></i></span>;
    }
  };

  const getDifficultyColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'beginner':
        return 'is-success';
      case 'intermediate':
        return 'is-warning';
      case 'advanced':
        return 'is-danger';
      default:
        return 'is-info';
    }
  };

  if (loading) {
    return (
      <div className="course-detail-bg">
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4">Loading course details...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !courseData) {
    return (
      <div className="course-detail-bg">
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4 has-text-danger">{error || 'Course not found'}</div>
            <button className="button is-primary mt-4" onClick={() => navigate('/courses')}>
              Back to Courses
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { course, enrollment, lessons, progress_summary } = courseData;

  return (
    <div className="course-detail-bg">
      {/* Header */}
      <Header />

      {/* Breadcrumbs */}
      <div className="container mt-4">
        <nav className="breadcrumb" aria-label="breadcrumbs">
          <ul>
            <li><a href="#home" onClick={(e) => { e.preventDefault(); navigate('/home'); }}>Home</a></li>
            <li><a href="#courses" onClick={(e) => { e.preventDefault(); navigate('/courses'); }}>Courses</a></li>
            <li className="is-active"><a href="#course">{course.course_name}</a></li>
          </ul>
        </nav>
      </div>

      {/* Success Message */}
      {enrollmentSuccess && (
        <div className="container">
          <div className="notification is-success is-light">
            <button className="delete" onClick={() => setEnrollmentSuccess(false)}></button>
            Successfully enrolled in the course! You can now access all lessons.
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="container">
          <div className="notification is-danger is-light">
            <button className="delete" onClick={() => setError(null)}></button>
            {error}
          </div>
        </div>
      )}

      {/* Course Header */}
      <div className="container">
        <div className="box course-header-card">
          <div className="columns">
            <div className="column is-8">
              <div className="tags mb-3">
                <span className={`tag ${getDifficultyColor(course.difficulty_level)}`}>
                  {course.difficulty_level?.toUpperCase()}
                </span>
                <span className="tag is-light">{course.total_hour} hours</span>
                <span className="tag is-light">{lessons?.length || 0} lessons</span>
              </div>
              
              <h1 className="title is-2 mb-3">{course.course_name}</h1>
              <p className="subtitle is-5 has-text-grey mb-4">{course.description}</p>

              {/* Learning Objectives */}
              <div className="content">
                <h3 className="title is-4">Learning objectives</h3>
                <p>In this course, you'll learn:</p>
                <ul>
                  {courseContent?.learning_objectives?.map((objective, index) => (
                    <li key={index}>{objective}</li>
                  )) || [
                    <li key="1">How to master the fundamental concepts covered in this course</li>,
                    <li key="2">Practical skills that you can apply immediately</li>,
                    <li key="3">Best practices and industry standards</li>,
                    <li key="4">How to build real-world solutions using what you've learned</li>
                  ]}
                </ul>
              </div>

              {/* Prerequisites */}
              <div className="content">
                <h3 className="title is-4">Prerequisites</h3>
                {courseContent?.prerequisites?.length > 0 ? (
                  <ul>
                    {courseContent.prerequisites.map((prerequisite, index) => (
                      <li key={index}>{prerequisite}</li>
                    ))}
                  </ul>
                ) : (
                  <p>None - This course is designed for learners at the {course.difficulty_level} level.</p>
                )}
              </div>
            </div>
            
            <div className="column is-4">
              <div className="box course-progress-card">
                <h4 className="title is-5 mb-3">Your Progress</h4>
                <div className="mb-4">
                  <progress 
                    className="progress is-primary is-medium" 
                    value={progress_summary?.progress_percentage || 0} 
                    max="100"
                  ></progress>
                  <p className="has-text-centered mt-2">
                    <strong>{progress_summary?.progress_percentage || 0}%</strong> complete
                  </p>
                </div>
                
                <div className="course-stats">
                  <div className="level is-mobile mb-3">
                    <div className="level-item has-text-centered">
                      <div>
                        <p className="heading">Completed</p>
                        <p className="title is-5">{progress_summary?.completed_lessons || 0}</p>
                      </div>
                    </div>
                    <div className="level-item has-text-centered">
                      <div>
                        <p className="heading">Remaining</p>
                        <p className="title is-5">{(progress_summary?.total_lessons || 0) - (progress_summary?.completed_lessons || 0)}</p>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mb-3">
                  <strong>Status:</strong> 
                  <span className={`tag ml-2 ${enrollment?.status === 'Complete' ? 'is-success' : 'is-info'}`}>
                    {enrollment?.status || 'Not Enrolled'}
                  </span>
                </div>
                
                {enrollment?.enroll_date && (
                  <div className="mb-3">
                    <strong>Enrolled:</strong> {new Date(enrollment.enroll_date).toLocaleDateString()}
                  </div>
                )}
                
                {enrollment?.complete_date && (
                  <div className="mb-3">
                    <strong>Completed:</strong> {new Date(enrollment.complete_date).toLocaleDateString()}
                  </div>
                )}

                <div className="buttons is-fullwidth mt-4">
                  {!enrollment ? (
                    <button 
                      className={`button is-primary is-fullwidth ${enrolling ? 'is-loading' : ''}`}
                      onClick={handleEnrollment}
                      disabled={enrolling}
                    >
                      <span className="icon"><i className="fas fa-play"></i></span>
                      <span>{enrolling ? 'Enrolling...' : 'Start Course'}</span>
                    </button>
                  ) : enrollment.status === 'Complete' ? (
                    <button className="button is-success is-fullwidth">
                      <span className="icon"><i className="fas fa-trophy"></i></span>
                      <span>Course Completed</span>
                    </button>
                  ) : (
                    <button 
                      className="button is-primary is-fullwidth"
                      onClick={() => {
                        // Continue course logic - could implement lesson navigation here
                        console.log('Continuing course:', courseId);
                      }}
                    >
                      <span className="icon"><i className="fas fa-play"></i></span>
                      <span>Continue Course</span>
                    </button>
                  )}
                  
                  <button className="button is-light is-fullwidth mt-2">
                    <span className="icon"><i className="fas fa-clipboard-check"></i></span>
                    <span>Take Assessment</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Course Content */}
      <div className="container mt-4 mb-6">
        <div className="columns">
          {/* Lesson List */}
          <div className="column is-4">
            <div className="box course-lessons-card">
              <h3 className="title is-4 mb-4">Course Content</h3>
              <div className="lesson-list">
                {lessons?.map((lesson, index) => (
                  <div 
                    key={lesson.lesson_id}
                    className={`lesson-item ${activeLesson?.lesson_id === lesson.lesson_id ? 'is-active' : ''}`}
                    onClick={() => handleLessonClick(lesson)}
                  >
                    <div className="level is-mobile">
                      <div className="level-left">
                        <div className="level-item">
                          {getStatusIcon(lesson.status)}
                          <div className="ml-3">
                            <div className="has-text-weight-semibold">{lesson.lesson_title}</div>
                            <div className="is-size-7 has-text-grey">{lesson.duration_hours} hours</div>
                          </div>
                        </div>
                      </div>
                      <div className="level-right">
                        <div className="level-item">
                          <span className="is-size-7 has-text-grey">#{lesson.lesson_order}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Lesson Content */}
          <div className="column is-8">
            <div className="box course-content-card">
              {activeLesson ? (
                <>
                  <div className="level mb-4">
                    <div className="level-left">
                      <div className="level-item">
                        <h2 className="title is-3">{activeLesson.lesson_title}</h2>
                      </div>
                    </div>
                    <div className="level-right">
                      <div className="level-item">
                        {getStatusIcon(activeLesson.status)}
                        <span className="ml-2 has-text-weight-semibold">{activeLesson.status || 'Not Started'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="tags mb-4">
                    <span className="tag is-light">
                      <span className="icon"><i className="fas fa-clock"></i></span>
                      <span>{activeLesson.duration_hours} hours</span>
                    </span>
                    <span className="tag is-light">
                      <span className="icon"><i className="fas fa-list-ol"></i></span>
                      <span>Lesson {activeLesson.lesson_order}</span>
                    </span>
                  </div>

                  <div className="content">
                    <p className="is-size-5 mb-4">{activeLesson.description}</p>
                    
                    <div className="notification is-info is-light">
                      <p><strong>Note:</strong> This is a preview of the lesson content. The full interactive lesson content will be loaded from ChromaDB when you start the lesson.</p>
                    </div>

                    <h4 className="title is-4">What you'll learn</h4>
                    <ul>
                      {activeLesson.what_you_will_learn && activeLesson.what_you_will_learn.length > 0 ? (
                        activeLesson.what_you_will_learn.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))
                      ) : (
                        <>
                          <li>Key concepts and fundamentals related to this lesson</li>
                          <li>Practical applications and real-world examples</li>
                          <li>Hands-on exercises and activities</li>
                          <li>Best practices and industry insights</li>
                        </>
                      )}
                    </ul>

                    <div className="buttons mt-5">
                      <button 
                        className={`button is-primary is-medium ${activeLesson.status === 'Complete' ? 'is-success' : ''}`}
                        onClick={() => {
                          // Here you would implement starting/continuing the lesson
                          console.log('Starting lesson:', activeLesson.lesson_id);
                        }}
                      >
                        {activeLesson.status === 'Complete' ? 'Review Lesson' : 
                         activeLesson.status === 'In Progress' ? 'Continue Lesson' : 'Start Lesson'}
                      </button>
                      
                      {activeLesson.status === 'Complete' && (
                        <button className="button is-light">
                          <span className="icon"><i className="fas fa-certificate"></i></span>
                          <span>View Certificate</span>
                        </button>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="has-text-centered">
                  <div className="is-size-5 has-text-grey">Select a lesson to view its content</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CourseDetailPage; 