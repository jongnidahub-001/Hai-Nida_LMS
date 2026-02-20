import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlert } from '../contexts/AlertContext';
import { useNavigate, useParams } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './AdminHomePage.css';

function AdminUserDetail() {
  const { user, getAuthHeader } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();
  const { userId } = useParams();
  const [userDetail, setUserDetail] = useState(null);
  const [enrolledCourses, setEnrolledCourses] = useState([]);
  const [quizResults, setQuizResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('courses');
  const [selectedQuizAnswers, setSelectedQuizAnswers] = useState(null);
  const [showAnswersModal, setShowAnswersModal] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }
    fetchUserDetail();
  }, [user, navigate, userId]);

  const fetchUserDetail = async () => {
    try {
      // Fetch user details
      const userResponse = await fetch(`${API_BASE_URL}/api/admin/user/${userId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUserDetail(userData.user);
        setEnrolledCourses(userData.enrolled_courses || []);
        setQuizResults(userData.quiz_results || []);

      } else {
        console.error('Failed to fetch user details');
      }
    } catch (error) {
      console.error('Error fetching user details:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyColor = (level) => {
    switch(level?.toLowerCase()) {
      case 'casual': return 'is-info';
      case 'regular': return 'is-warning';
      case 'intense': return 'is-danger';
      default: return 'is-info';
    }
  };

  const getStatusColor = (status) => {
    switch(status?.toLowerCase()) {
      case 'complete': return 'is-success';
      case 'learning': return 'is-info';
      case 'completed': return 'is-success';
      default: return 'is-light';
    }
  };

  const handleViewAnswers = async (quiz) => {
    try {
      const answers = JSON.parse(quiz.answers);
      setLoading(true);
      
      // Fetch quiz questions to get question text
      const quizResponse = await fetch(`${API_BASE_URL}/api/quiz/${quiz.quiz_id}/questions`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (!quizResponse.ok) {
        throw new Error('Failed to fetch quiz questions');
      }
      
      const quizData = await quizResponse.json();
      const questions = quizData.questions || [];
      
      // Create a map of question_id to question data
      const questionMap = {};
      questions.forEach(q => {
        questionMap[q.question_id] = q;
      });
      
      // Enhance answers with question text and choice text for multiple choice
      const enhancedAnswers = await Promise.all(
        answers.map(async (answer) => {
          const questionData = questionMap[answer.question_id];
          let enhancedAnswer = {
            question_id: answer.question_id,
            answer: answer.answer,
            type: answer.type || 'Unknown',
            result: answer.result === true || answer.result === 'true', // Ensure boolean
            question_text: questionData ? questionData.question_text : 'Question not found'
          };
          
          // If it's multiple choice, fetch choices to map choice ID to choice text
          if (enhancedAnswer.type === 'Multiple Choice') {
            try {
              const choicesResponse = await fetch(`${API_BASE_URL}/api/question/${answer.question_id}/choices`, {
                headers: {
                  ...getAuthHeader(),
                  'Content-Type': 'application/json'
                }
              });
              
              if (choicesResponse.ok) {
                const choicesData = await choicesResponse.json();
                const choices = choicesData.choices || [];
                
                // Find the choice that matches the user's answer
                const selectedChoice = choices.find(choice => choice.choice_id === answer.answer);
                enhancedAnswer.choice_text = selectedChoice ? selectedChoice.choice_text : 'Choice not found';
              } else {
                enhancedAnswer.choice_text = 'Unable to load choice';
              }
            } catch (error) {
              console.error('Error fetching choices:', error);
              enhancedAnswer.choice_text = 'Error loading choice';
            }
          }
          
          return enhancedAnswer;
        })
      );
      
      setSelectedQuizAnswers({
        course_name: quiz.course_name,
        score: quiz.score,
        total_points: quiz.total_points,
        answers: enhancedAnswers
      });
      setShowAnswersModal(true);
    } catch (error) {
      console.error('Error loading quiz answers:', error);
      showAlert('Failed to load quiz answers. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const closeAnswersModal = () => {
    setShowAnswersModal(false);
    setSelectedQuizAnswers(null);
  };

  if (loading) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          <div className="has-text-centered">
            <div className="is-size-6">Loading user details...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!userDetail) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          <div className="has-text-centered">
            <div className="is-size-6 has-text-danger">User not found</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-home-bg">
      <Header />
      
      <div className="container mt-4">
        {/* User Profile Header */}
        <div className="box home-overview-card mb-4">
          <div className="is-flex is-justify-content-space-between is-align-items-start mb-4">
            <div>
              <h2 className="is-size-4 has-text-weight-bold mb-2">{userDetail.full_name || userDetail.username}</h2>
              <div className="tags">
                <span className={`tag ${userDetail.role === 'admin' ? 'is-danger' : 'is-info'}`}>
                  {userDetail.role}
                </span>
                <span className="tag is-light">
                  <i className="fas fa-envelope mr-1"></i>
                  {userDetail.email}
                </span>
              </div>
            </div>
            <button 
              className="button is-small is-light"
              onClick={() => navigate('/admin')}
            >
              <span className="icon">
                <i className="fas fa-arrow-left"></i>
              </span>
              <span>Back to Users</span>
            </button>
          </div>

          <div className="columns">
            <div className="column">
              <div className="box is-shadowless has-background-light">
                <div className="is-flex is-justify-content-space-between mb-2">
                  <span className="has-text-grey">Username</span>
                  <span className="has-text-weight-bold">{userDetail.username}</span>
                </div>
                <div className="is-flex is-justify-content-space-between mb-2">
                  <span className="has-text-grey">Enrolled Courses</span>
                  <span className="has-text-weight-bold">{enrolledCourses.length}</span>
                </div>
                <div className="is-flex is-justify-content-space-between">
                  <span className="has-text-grey">Quizzes Taken</span>
                  <span className="has-text-weight-bold">{quizResults.length}</span>
                </div>
              </div>
            </div>
            <div className="column is-8">
              <div className="box is-shadowless has-background-light">
                <h3 className="is-size-6 has-text-weight-bold mb-2">User Information</h3>
                <p className="has-text-grey mb-2">
                  <strong>Full Name:</strong> {userDetail.full_name || 'Not provided'}
                </p>
                <p className="has-text-grey mb-2">
                  <strong>Email:</strong> {userDetail.email}
                </p>
                <p className="has-text-grey">
                  <strong>Member Since:</strong> {userDetail.created_at ? new Date(parseInt(userDetail.created_at)).toLocaleDateString() : 'Unknown'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="box home-courses-card">
          <div className="tabs is-toggle is-small mb-4">
            <ul>
              <li className={activeTab === 'courses' ? 'is-active' : ''}>
                <a href="#courses" onClick={(e) => { e.preventDefault(); setActiveTab('courses'); }}>
                  <span className="icon is-small"><i className="fas fa-book"></i></span>
                  <span>Enrolled Courses ({enrolledCourses.length})</span>
                </a>
              </li>
              <li className={activeTab === 'quizzes' ? 'is-active' : ''}>
                <a href="#quizzes" onClick={(e) => { e.preventDefault(); setActiveTab('quizzes'); }}>
                  <span className="icon is-small"><i className="fas fa-clipboard-check"></i></span>
                  <span>Quiz Results ({quizResults.length})</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Enrolled Courses Tab */}
          {activeTab === 'courses' && (
            <div>
              {enrolledCourses.length === 0 ? (
                <div className="has-text-centered">
                  <div className="is-size-6 has-text-grey">No enrolled courses</div>
                </div>
              ) : (
                <div className="columns is-multiline">
                  {enrolledCourses.map((course) => (
                    <div className="column is-6" key={course.course_id}>
                      <div className="box home-course-row" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <div className="mb-3" style={{ flex: '1' }}>
                          <div className="is-flex is-justify-content-space-between is-align-items-center mb-2">
                            <div className="is-size-6 has-text-weight-bold">{course.course_name}</div>
                            <div className="is-flex is-align-items-center">
                              <span className={`tag is-small mr-2 ${getStatusColor(course.enrollment_status)}`}>
                                {course.enrollment_status}
                              </span>
                              <span className={`tag ${getDifficultyColor(course.difficulty_level)}`}>
                                {course.difficulty_level}
                              </span>
                            </div>
                          </div>
                          <div className="is-size-7 has-text-grey mb-2" style={{ 
                            minHeight: '2rem',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden'
                          }}>
                            {course.description}
                          </div>
                          <div className="mb-2">
                            <progress 
                              className="progress is-info is-small" 
                              value={course.progress_percentage || 0} 
                              max="100"
                            ></progress>
                            <span className="is-size-7 has-text-grey">
                              {course.progress_percentage || 0}% complete
                            </span>
                          </div>
                        </div>
                        <div className="is-flex is-justify-content-space-between is-align-items-center">
                          <div className="tags">
                            <span className="tag is-light">
                              <i className="fas fa-clock mr-1"></i>
                              {course.total_hour}h
                            </span>
                            <span className="tag is-light">
                              <i className="fas fa-book mr-1"></i>
                              {course.lesson_count} lessons
                            </span>
                          </div>
                          <button 
                            className="button is-small is-info"
                            onClick={() => navigate(`/admin/course/${course.course_id}`)}
                          >
                            View Course
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Quiz Results Tab */}
          {activeTab === 'quizzes' && (
            <div>
              {quizResults.length === 0 ? (
                <div className="has-text-centered">
                  <div className="is-size-6 has-text-grey">No quiz results</div>
                </div>
              ) : (
                <div className="table-container">
                  <table className="table is-fullwidth is-hoverable">
                    <thead>
                      <tr>
                        <th>Course</th>
                        <th>Score</th>
                        <th>Status</th>
                        <th>Date Taken</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quizResults.map((quiz, index) => (
                        <tr key={index}>
                          <td>
                            <div className="is-size-6 has-text-weight-bold">{quiz.course_name}</div>
                            <div className="is-size-7 has-text-grey">{quiz.course_id}</div>
                          </td>
                          <td>
                            <span className="has-text-weight-bold">
                              {quiz.score} / {quiz.total_points}
                            </span>
                            <div className="is-size-7 has-text-grey">
                              {Math.round((quiz.score / quiz.total_points) * 100)}%
                            </div>
                          </td>
                          <td>
                            <span className={`tag ${quiz.status === 'Completed' ? 'is-success' : 'is-warning'}`}>
                              {quiz.status}
                            </span>
                          </td>
                          <td>
                            <span className="is-size-7">
                              {quiz.attempted_at ? new Date(quiz.attempted_at).toLocaleDateString() : 'Unknown'}
                            </span>
                          </td>
                          <td>
                            <div className="buttons">
                              <button 
                                className="button is-small is-info mr-2"
                                onClick={() => navigate(`/admin/course/${quiz.course_id}`)}
                              >
                                View Course
                              </button>
                              <button 
                                className="button is-small is-success"
                                onClick={() => handleViewAnswers(quiz)}
                              >
                                View Answers
                              </button>
                            </div>
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

             {/* Quiz Answers Modal */}
       {showAnswersModal && (
         <div className="modal is-active">
           <div className="modal-background" onClick={closeAnswersModal}></div>
           <div className="modal-content" style={{ maxHeight: '80vh', overflow: 'auto' }}>
             <div className="box">
               <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
                 <h3 className="is-size-4 has-text-weight-bold">Quiz Answers</h3>
                 <button 
                   className="button is-small is-danger"
                   onClick={closeAnswersModal}
                 >
                   <span className="icon">
                     <i className="fas fa-times"></i>
                   </span>
                 </button>
               </div>
               
               <div className="box is-shadowless has-background-light mb-4">
                 <div className="is-size-6 has-text-weight-bold mb-2">{selectedQuizAnswers.course_name}</div>
                 <div className="is-flex is-justify-content-space-between">
                   <span>Score: <strong>{selectedQuizAnswers.score} / {selectedQuizAnswers.total_points}</strong></span>
                   <span>Percentage: <strong>{Math.round((selectedQuizAnswers.score / selectedQuizAnswers.total_points) * 100)}%</strong></span>
                 </div>
               </div>

               <div className="content">
                 <h4 className="is-size-5 has-text-weight-bold mb-3">User Answers</h4>
                 {selectedQuizAnswers.answers.map((answer, index) => (
                   <div key={index} className="box is-shadowless has-background-white-ter mb-3">
                     <div className="is-flex is-justify-content-space-between is-align-items-center mb-2">
                       <span className="is-size-6 has-text-weight-bold">Question {index + 1}</span>
                       <div className="is-flex is-align-items-center">
                         <span className={`tag is-small mr-2 ${answer.type === 'Multiple Choice' ? 'is-info' : answer.type === 'Subjective' ? 'is-warning' : answer.type === 'Fill in the Blank' ? 'is-primary' : 'is-light'}`}>
                           {answer.type || 'Unknown'}
                         </span>
                         <span className={`tag ${answer.result === true ? 'is-success' : 'is-danger'}`}>
                           {answer.result === true ? 'Correct' : 'Incorrect'}
                         </span>
                       </div>
                     </div>
                     <div className="mb-3">
                       <strong>Question:</strong>
                       <div className="content mt-1" style={{ 
                         padding: '0.5rem',
                         backgroundColor: '#ffffff',
                         borderRadius: '4px',
                         fontSize: '0.875rem',
                         border: '1px solid #e0e0e0'
                       }}>
                         {answer.question_text}
                       </div>
                     </div>
                     <div className="mb-2">
                       <strong>User's Answer:</strong>
                       <div className="content mt-1" style={{ 
                         maxHeight: '150px', 
                         overflow: 'auto',
                         padding: '0.5rem',
                         backgroundColor: '#f5f5f5',
                         borderRadius: '4px',
                         fontSize: '0.875rem'
                       }}>
                         {answer.type === 'Multiple Choice' ? (
                           <div>
                             <div className="is-size-7 has-text-grey mb-1">Selected choice:</div>
                             <span>{answer.choice_text || 'Choice not found'}</span>
                             {!answer.choice_text && (
                               <div className="is-size-7 has-text-grey mt-1">
                                 Choice ID: <code>{answer.answer}</code>
                               </div>
                             )}
                           </div>
                         ) : answer.type === 'Subjective' ? (
                           <div>
                             <div className="is-size-7 has-text-grey mb-1">User's essay answer:</div>
                             <span style={{ whiteSpace: 'pre-wrap' }}>{answer.answer || 'No answer provided'}</span>
                           </div>
                         ) : answer.type === 'Fill in the Blank' ? (
                           <div>
                             <div className="is-size-7 has-text-grey mb-1">User's answer:</div>
                             <span style={{ fontWeight: 'bold' }}>{answer.answer || 'No answer provided'}</span>
                           </div>
                         ) : (
                           <div>
                             <div className="is-size-7 has-text-grey mb-1">Answer:</div>
                             <span style={{ whiteSpace: 'pre-wrap' }}>{answer.answer || 'No answer provided'}</span>
                           </div>
                         )}
                       </div>
                     </div>
                   </div>
                 ))}
               </div>
             </div>
           </div>
         </div>
       )}
    </div>
  );
}

export default AdminUserDetail; 