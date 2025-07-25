import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './AdminHomePage.css';

// LessonExpander Component (copied from AdminAllCourse.js)
const LessonExpander = ({ lesson, lessonContents }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatMarkdownContent = (content) => {
    if (!content) return '';
    
    // Basic markdown formatting for display
    return content
      .replace(/^### (.*$)/gim, '<h4 class="title is-5 mt-4 mb-2">$1</h4>')
      .replace(/^## (.*$)/gim, '<h3 class="title is-4 mt-5 mb-3">$1</h3>')
      .replace(/^# (.*$)/gim, '<h2 class="title is-3 mt-5 mb-3">$1</h2>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="card mb-4" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
      {/* Card Header - Clickable */}
      <header 
        className="card-header"
        style={{ 
          cursor: 'pointer',
          transition: 'background-color 0.2s ease',
          backgroundColor: isExpanded ? '#f5f5f5' : 'white'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
        onMouseEnter={(e) => e.target.style.backgroundColor = '#f8f9fa'}
        onMouseLeave={(e) => e.target.style.backgroundColor = isExpanded ? '#f5f5f5' : 'white'}
      >
        <div className="card-header-title">
          <div className="is-flex is-align-items-center">
            <span className="icon is-medium mr-3 has-text-info">
              <i className="fas fa-book"></i>
            </span>
            <div>
              <p className="title is-6 mb-1">
                Lesson {lesson.lesson_order}: {lesson.lesson_title}
              </p>
              <p className="subtitle is-7 has-text-grey mb-0">
                <span className="icon is-small mr-1">
                  <i className="fas fa-clock"></i>
                </span>
                {lesson.duration_hours} hours
                {lessonContents && lessonContents.length > 0 && (
                  <>
                    <span className="mx-2">•</span>
                    <span className="icon is-small mr-1">
                      <i className="fas fa-file-alt"></i>
                    </span>
                    {lessonContents.length} content item{lessonContents.length !== 1 ? 's' : ''}
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="card-header-icon">
          <span className="icon">
            <i 
              className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}
              style={{ 
                transition: 'transform 0.3s ease',
                transform: isExpanded ? 'rotate(0deg)' : 'rotate(0deg)'
              }}
            ></i>
          </span>
        </div>
      </header>

      {/* Card Content - Collapsible */}
      <div 
        className="card-content"
        style={{ 
          display: isExpanded ? 'block' : 'none',
          animation: isExpanded ? 'fadeIn 0.3s ease-in' : 'none'
        }}
      >
        {/* Learning Objectives */}
        <div className="content mb-4">
          <h6 className="title is-6 mb-2 has-text-primary">
            <span className="icon is-small mr-2">
              <i className="fas fa-target"></i>
            </span>
            What you will learn:
          </h6>
          <div className="box has-background-info-light">
            <ul className="mb-0">
              {lesson.what_you_will_learn?.map((item, idx) => (
                <li key={idx} className="mb-1">{item}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Lesson Content */}
        {lessonContents && lessonContents.length > 0 && (
          <div className="content">
            <h6 className="title is-6 mb-3 has-text-primary">
              <span className="icon is-small mr-2">
                <i className="fas fa-book-open"></i>
              </span>
              Lesson Content
            </h6>
            
            {lessonContents.map((contentItem, index) => (
              <div key={index} className="mb-4">
                {contentItem.content_type === 'text' && (
                  <div className="card">
                    <div className="card-content">
                      <div 
                        className="lesson-content content"
                        style={{ 
                          fontSize: '0.9rem', 
                          lineHeight: '1.6',
                          maxHeight: '500px',
                          overflowY: 'auto'
                        }}
                        dangerouslySetInnerHTML={{ 
                          __html: formatMarkdownContent(contentItem.content) 
                        }}
                      />
                    </div>
                  </div>
                )}
                
                {contentItem.content_type !== 'text' && (
                  <div className="notification is-warning is-light">
                    <div className="is-flex is-align-items-center">
                      <span className="icon is-small mr-2">
                        <i className="fas fa-exclamation-triangle"></i>
                      </span>
                      <div>
                        <strong>Content Type:</strong> {contentItem.content_type}
                        <br />
                        <em>This content type is not yet supported for preview.</em>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

function AdminCourseDetail() {
  const { user, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [enrolledUsers, setEnrolledUsers] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [lessonContents, setLessonContents] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [choices, setChoices] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('course');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    // Redirect if not admin
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }

    fetchCourseDetails();
  }, [user, navigate, courseId]);

  const fetchCourseDetails = async () => {
    try {
      // Fetch basic course details and enrolled users
      const response = await fetch(`${API_BASE_URL}/api/admin/courses/${courseId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setCourse(data.course);
        setEnrolledUsers(data.enrolled_users || []);
      } else {
        console.error('Failed to fetch course details');
      }

      // Fetch lessons and lesson contents
      const lessonsResponse = await fetch(`${API_BASE_URL}/api/admin/courses/${courseId}/lessons`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });

      if (lessonsResponse.ok) {
        const lessonsData = await lessonsResponse.json();
        setLessons(lessonsData.lessons || []);
        setLessonContents(lessonsData.lesson_contents || []);
      }

      // Fetch quiz data
      const quizResponse = await fetch(`${API_BASE_URL}/api/admin/courses/${courseId}/quiz`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });

      if (quizResponse.ok) {
        const quizData = await quizResponse.json();
        setQuiz(quizData.quiz);
        setQuestions(quizData.questions || []);
        setChoices(quizData.choices || []);
        setAnswers(quizData.answers || []);
      }

    } catch (error) {
      console.error('Error fetching course details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCourse = async () => {
    if (!course) return;
    
    setDeleting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/courses/${courseId}`, {
        method: 'DELETE',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Success: ${result.message}`);
        navigate('/admin/courses');
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to delete course'}`);
      }
    } catch (error) {
      console.error('Error deleting course:', error);
      alert('Error: Failed to delete course. Please try again.');
    } finally {
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const filteredUsers = enrolledUsers.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getDifficultyColor = (level) => {
    switch(level?.toLowerCase()) {
      case 'beginner': return 'is-success';
      case 'intermediate': return 'is-warning';
      case 'advanced': return 'is-danger';
      case 'casual': return 'is-info';
      case 'regular': return 'is-warning';
      case 'intense': return 'is-danger';
      default: return 'is-info';
    }
  };

  if (loading) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          <div className="has-text-centered">
            <div className="is-size-6">Loading course details...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          <div className="has-text-centered">
            <div className="is-size-6 has-text-danger">Course not found</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-home-bg">
      <Header />
      
      <div className="container mt-4">
        {/* Course Header */}
        <div className="box admin-home-card mb-4">
          <div className="is-flex is-justify-content-space-between is-align-items-start mb-4">
            <div>
              <h2 className="is-size-4 has-text-weight-bold mb-2">{course.course_name}</h2>
              <span className={`tag ${getDifficultyColor(course.difficulty_level)}`}>
                {course.difficulty_level}
              </span>
            </div>
            <a
              onClick={() => navigate('/admin/courses')}
              style={{ cursor: 'pointer' }}
            >
              <span className="icon">
                <i className="fas fa-arrow-left"></i>
              </span>
              <span>Back to Courses</span>
            </a>
          </div>

          <div className="columns mb-4">
            <div className="column">
              <div className="box is-shadowless has-background-light">
                <div className="is-flex is-justify-content-space-between mb-2">
                  <span className="has-text-grey">Total Hours</span>
                  <span className="has-text-weight-bold">{course.total_hour}h</span>
                </div>
                <div className="is-flex is-justify-content-space-between mb-2">
                  <span className="has-text-grey">Total Lessons</span>
                  <span className="has-text-weight-bold">{lessons.length}</span>
                </div>
                <div className="is-flex is-justify-content-space-between">
                  <span className="has-text-grey">Enrolled Students</span>
                  <span className="has-text-weight-bold">{enrolledUsers.length}</span>
                </div>
              </div>
            </div>
            <div className="column is-8">
              <div className="box is-shadowless has-background-light">
                <h3 className="is-size-6 has-text-weight-bold mb-2">Description</h3>
                <p className="has-text-grey">{course.description || 'No description available'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="box admin-home-card">
          <div className="tabs is-boxed">
            <ul>
              <li className={activeTab === 'course' ? 'is-active' : ''}>
                <a style={{ 
                      color: activeTab === 'logs' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeTab === 'logs' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onClick={() => setActiveTab('course')}>
                  <span className="icon is-small">
                    <i className="fas fa-book"></i>
                  </span>
                  <span>Course</span>
                </a>
              </li>
              <li className={activeTab === 'quiz' ? 'is-active' : ''}>
                <a 
                style={{ 
                      color: activeTab === 'logs' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeTab === 'logs' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                onClick={() => setActiveTab('quiz')}>
                  <span className="icon is-small">
                    <i className="fas fa-question-circle"></i>
                  </span>
                  <span>Quiz</span>
                </a>
              </li>
              <li className={activeTab === 'users' ? 'is-active' : ''}>
                <a 
                style={{ 
                      color: activeTab === 'logs' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeTab === 'logs' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                onClick={() => setActiveTab('users')}>
                  <span className="icon is-small">
                    <i className="fas fa-users"></i>
                  </span>
                  <span>Enrolled Users ({enrolledUsers.length})</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Course Tab */}
          {activeTab === 'course' && (
            <div className="content">
              <div className="mb-4">
                <h4 className="title is-5 mb-3">Course Content</h4>
                
                {course.learning_objectives && course.learning_objectives.length > 0 && (
                  <div className="box has-background-info-light mb-4">
                    <h6 className="title is-6 mb-2 has-text-primary">Learning Objectives</h6>
                    <ul className="mb-0">
                      {course.learning_objectives.map((objective, index) => (
                        <li key={index}>{objective}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {course.prerequisites && course.prerequisites.length > 0 && (
                  <div className="box has-background-warning-light mb-4">
                    <h6 className="title is-6 mb-2 has-text-warning-dark">Prerequisites</h6>
                    <ul className="mb-0">
                      {course.prerequisites.map((prerequisite, index) => (
                        <li key={index}>{prerequisite}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <h6 className="title is-6 mb-3">Lessons ({lessons.length})</h6>
                {lessons.length > 0 ? (
                  lessons.sort((a, b) => a.lesson_order - b.lesson_order).map((lesson) => {
                    const lessonContent = lessonContents.filter(
                      content => content.lesson_id === lesson.lesson_id
                    ).sort((a, b) => a.content_order - b.content_order);
                    
                    return (
                      <LessonExpander 
                        key={lesson.lesson_id}
                        lesson={lesson}
                        lessonContents={lessonContent}
                      />
                    );
                  })
                ) : (
                  <div className="has-text-centered">
                    <div className="is-size-6 has-text-grey">No lessons available</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Quiz Tab */}
          {activeTab === 'quiz' && (
            <div className="content">
              <div className="mb-4">
                <h4 className="title is-5 mb-3">Quiz Content</h4>
                
                {quiz ? (
                  <div>
                    <div className="box has-background-light mb-4">
                      <h5 className="title is-6 mb-2">{quiz.quiz_title}</h5>
                      <p className="has-text-grey mb-2">{quiz.description}</p>
                      <div className="tags">
                        <span className={`tag ${getDifficultyColor(quiz.difficulty_level)}`}>
                          {quiz.difficulty_level}
                        </span>
                        <span className="tag is-info">{questions.length} questions</span>
                      </div>
                    </div>

                    <h6 className="title is-6 mb-3">Questions</h6>
                    {questions.length > 0 ? (
                      questions.sort((a, b) => a.question_order - b.question_order).map((question, index) => (
                        <div key={question.question_id} className="card mb-4">
                          <div className="card-content">
                            <div className="content">
                              <div className="is-flex is-align-items-center mb-2">
                                <span className="tag is-primary mr-2">Q{index + 1}</span>
                                <span className={`tag ${(question.question_type === 'Multiple Choice' || question.question_type === 'choices') ? 'is-info' : (question.question_type === 'Subjective' || question.question_type === 'subjective') ? 'is-success' : 'is-warning'} mr-2`}>
                                  {question.question_type === 'choices' ? 'Multiple Choice' : 
                                   question.question_type === 'fill' ? 'Fill in the Blank' : 
                                   question.question_type === 'subjective' ? 'Subjective' : 
                                   question.question_type}
                                </span>
                                <span className="tag is-light">{question.points} pts</span>
                              </div>
                              <p className="has-text-weight-semibold mb-3">{question.question_text}</p>
                              
                              {(question.question_type === 'Multiple Choice' || question.question_type === 'choices') && (
                                <div className="content">
                                  <p className="has-text-weight-semibold mb-2">Choices:</p>
                                  {choices.filter(choice => choice.question_id === question.question_id).map((choice, idx) => (
                                    <div key={choice.choice_id} className="field">
                                      <div className="control">
                                        <label className="radio">
                                          <input type="radio" name={`question_${question.question_id}`} disabled />
                                          <span className={`ml-2 ${choice.is_correct ? 'has-text-success has-text-weight-bold' : ''}`}>
                                            {choice.choice_text}
                                            {choice.is_correct && <span className="icon is-small ml-1"><i className="fas fa-check"></i></span>}
                                          </span>
                                        </label>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                              
                              {(question.question_type === 'Subjective' || question.question_type === 'subjective') && (
                                <div className="content">
                                  <p className="has-text-weight-semibold mb-2">Expected Answer:</p>
                                  {answers.filter(answer => answer.question_id === question.question_id).map((answer) => (
                                    <div key={answer.answer_id} className="box has-background-light">
                                      <p className="has-text-weight-semibold">{answer.answer_text || answer.correct_answer}</p>
                                    </div>
                                  ))}
                                </div>
                              )}
                              
                              {(question.question_type === 'Fill in the Blank' || question.question_type === 'fill') && (
                                <div className="content">
                                  <p className="has-text-weight-semibold mb-2">Correct Answer:</p>
                                  {answers.filter(answer => answer.question_id === question.question_id).map((answer) => (
                                    <span key={answer.answer_id} className="tag is-success is-medium">
                                      {answer.answer_text || answer.correct_answer}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="has-text-centered">
                        <div className="is-size-6 has-text-grey">No questions available</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="has-text-centered">
                    <div className="is-size-6 has-text-grey">No quiz available for this course</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Enrolled Users Tab */}
          {activeTab === 'users' && (
            <div className="content">
              <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
                <div className="is-size-5 has-text-weight-bold">Enrolled Users</div>
                <div className="field">
                  <div className="control has-icons-left">
                    <input
                      className="input is-small"
                      type="text"
                      placeholder="Search users..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    <span className="icon is-small is-left">
                      <i className="fas fa-search"></i>
                    </span>
                  </div>
                </div>
              </div>

              {filteredUsers.length === 0 ? (
                <div className="has-text-centered">
                  <div className="is-size-6 has-text-grey">No users found</div>
                </div>
              ) : (
                <div className="table-container">
                  <table className="table is-fullwidth is-hoverable">
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Progress</th>
                        <th>Quiz Status</th>
                        <th>Quiz Score</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((user) => (
                        <tr key={user.id}>
                          <td>{user.username}</td>
                          <td>{user.email}</td>
                          <td>
                            <progress 
                              className="progress is-info is-small" 
                              value={user.progress_percentage} 
                              max="100"
                            ></progress>
                            <span className="is-size-7 has-text-grey">
                              {user.progress_percentage}%
                            </span>
                          </td>
                          <td>
                            <span className={`tag ${user.quiz_status === 'Completed' ? 'is-success' : 
                              (user.quiz_status === 'Not Attempted' ? 'is-warning' : 'is-light')}`}>
                              {user.quiz_status || 'No Quiz'}
                            </span>
                          </td>
                          <td>
                            {user.quiz_score ? (
                              <span className="has-text-weight-bold">
                                {user.quiz_score} / {user.quiz_total_points}
                              </span>
                            ) : (
                              <span className="has-text-grey">-</span>
                            )}
                          </td>
                          <td>
                            <button 
                              className="button is-small is-info"
                              onClick={() => navigate(`/admin/user/${user.user_id}`)}
                            >
                              View User
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Floating Delete Button */}
      <div 
        style={{
          position: 'fixed',
          bottom: '30px',
          right: '30px',
          zIndex: 40
        }}
      >
        <button
          className="button is-danger"
          onClick={() => setShowDeleteModal(true)}
          disabled={deleting}
          style={{
            borderRadius: '25px',
            padding: '0.5rem 1rem',
            boxShadow: '0 2px 8px rgba(255, 56, 96, 0.3)',
            transition: 'all 0.3s ease',
            transform: deleting ? 'scale(0.95)' : 'scale(1)'
          }}
          onMouseEnter={(e) => {
            if (!deleting) {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.boxShadow = '0 4px 12px rgba(255, 56, 96, 0.4)';
            }
          }}
          onMouseLeave={(e) => {
            if (!deleting) {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = '0 2px 8px rgba(255, 56, 96, 0.3)';
            }
          }}
        >
          <span className="icon is-small">
            <i className="fas fa-trash"></i>
          </span>
          <span>Delete Course</span>
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      <div className={`modal ${showDeleteModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => setShowDeleteModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header 
            className="modal-card-head"
            style={{ 
              backgroundColor: 'white', 
              borderBottom: '1px solid var(--medium-grey)' 
            }}
          >
            <p 
              className="modal-card-title"
              style={{ 
                color: 'var(--primary-black)', 
                fontWeight: 'bold' 
              }}
            >
              <span className="icon is-medium has-text-danger mr-2">
                <i className="fas fa-exclamation-triangle"></i>
              </span>
              Delete Course Confirmation
            </p>
            <button 
              className="delete" 
              aria-label="close"
              onClick={() => setShowDeleteModal(false)}
              disabled={deleting}
            ></button>
          </header>
          <section 
            className="modal-card-body"
            style={{ backgroundColor: 'white', maxHeight: '70vh', overflowY: 'auto' }}
          >
            <div className="content">
              <p 
                className="has-text-weight-semibold mb-3"
                style={{ color: 'var(--primary-black)' }}
              >
                Are you sure you want to delete the course "{course?.course_name}"?
              </p>
              
              <div 
                className="notification is-warning is-light"
                style={{ 
                  backgroundColor: '#fefefe', 
                  borderLeft: '4px solid #ffdd57',
                  border: '1px solid var(--medium-grey)'
                }}
              >
                <p 
                  className="has-text-weight-semibold mb-2"
                  style={{ color: 'var(--primary-black)' }}
                >
                  <span className="icon is-small mr-1">
                    <i className="fas fa-exclamation-triangle"></i>
                  </span>
                  This action will permanently delete:
                </p>
                <ul className="ml-4" style={{ color: 'var(--primary-black)' }}>
                  <li>The course and all its details</li>
                  <li>All lessons and lesson content</li>
                  <li>All quizzes, questions, and answers</li>
                  <li>All user enrollments and progress</li>
                  <li>All quiz scores and results</li>
                </ul>
              </div>

              <div 
                className="notification is-danger is-light"
                style={{ 
                  backgroundColor: '#fefefe', 
                  borderLeft: '4px solid #ff3860',
                  border: '1px solid var(--medium-grey)'
                }}
              >
                <p 
                  className="has-text-weight-semibold"
                  style={{ color: 'var(--primary-black)' }}
                >
                  <span className="icon is-small mr-1">
                    <i className="fas fa-exclamation-circle"></i>
                  </span>
                  This action cannot be undone!
                </p>
              </div>

              {enrolledUsers.length > 0 && (
                <div 
                  className="notification is-info is-light"
                  style={{ 
                    backgroundColor: '#fefefe', 
                    borderLeft: '4px solid #3298dc',
                    border: '1px solid var(--medium-grey)'
                  }}
                >
                  <p 
                    className="has-text-weight-semibold"
                    style={{ color: 'var(--primary-black)' }}
                  >
                    <span className="icon is-small mr-1">
                      <i className="fas fa-users"></i>
                    </span>
                    {enrolledUsers.length} user{enrolledUsers.length !== 1 ? 's are' : ' is'} currently enrolled in this course.
                  </p>
                </div>
              )}
            </div>
          </section>
          <footer 
            className="modal-card-foot"
            style={{ 
              backgroundColor: 'white', 
              borderTop: '1px solid var(--medium-grey)', 
              gap: '12px' 
            }}
          >
            <button 
              className={`button is-danger ${deleting ? 'is-loading' : ''}`}
              onClick={handleDeleteCourse}
              disabled={deleting}
              style={{
                backgroundColor: '#ff3860',
                borderColor: '#ff3860',
                color: 'white'
              }}
            >
              <span className="icon">
                <i className="fas fa-trash"></i>
              </span>
              <span>Yes, Delete Course</span>
            </button>
            <button 
              className="button" 
              onClick={() => setShowDeleteModal(false)}
              disabled={deleting}
              style={{
                backgroundColor: 'white',
                borderColor: 'var(--medium-grey)',
                color: 'var(--primary-black)'
              }}
            >
              Cancel
            </button>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default AdminCourseDetail; 