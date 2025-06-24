import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import './AdminHomePage.css';

// Add custom styles for animations
const customStyles = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .lesson-card-header:hover {
    background-color: #f8f9fa !important;
  }
  
  .lesson-content h2, .lesson-content h3, .lesson-content h4 {
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
  }
  
  .lesson-content ul {
    margin-left: 1rem;
    margin-bottom: 1rem;
  }
  
  .lesson-content li {
    margin-bottom: 0.5rem;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = customStyles;
  if (!document.head.querySelector('[data-lesson-styles]')) {
    styleElement.setAttribute('data-lesson-styles', 'true');
    document.head.appendChild(styleElement);
  }
}

// LessonExpander Component
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

// LogCard Component
const LogCard = ({ logEntry, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getAgentIcon = (agentName) => {
    switch (agentName?.toLowerCase()) {
      case 'user':
        return 'fas fa-user';
      case 'expert_agent':
        return 'fas fa-brain';
      case 'validator_agent':
        return 'fas fa-check-circle';
      default:
        return 'fas fa-robot';
    }
  };

  const getAgentColor = (agentName) => {
    switch (agentName?.toLowerCase()) {
      case 'user':
        return 'is-info';
      case 'expert_agent':
        return 'is-primary';
      case 'validator_agent':
        return 'is-success';
      default:
        return 'is-warning';
    }
  };

  const formatLogContent = (content) => {
    if (typeof content === 'object') {
      return JSON.stringify(content, null, 2);
    }
    return content;
  };

  const getContentPreview = (content) => {
    const formatted = formatLogContent(content);
    if (formatted.length > 200) {
      return formatted.substring(0, 200) + '...';
    }
    return formatted;
  };

  const isContentLong = (content) => {
    return formatLogContent(content).length > 200;
  };

  return (
    <div className="card mb-4" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
      {/* Card Header */}
      <header className="card-header">
        <div className="card-header-title">
          <div className="is-flex is-align-items-center">
            <span className={`icon is-medium mr-3 has-text-${getAgentColor(logEntry.agent).replace('is-', '')}`}>
              <i className={getAgentIcon(logEntry.agent)}></i>
            </span>
            <div>
              <p className="title is-6 mb-1">
                <span className={`tag ${getAgentColor(logEntry.agent)} mr-2`}>
                  Step {index + 1}
                </span>
                {logEntry.agent}
              </p>
              <p className="subtitle is-7 has-text-grey mb-0">
                <span className="icon is-small mr-1">
                  <i className="fas fa-code"></i>
                </span>
                {typeof logEntry.content === 'object' ? 'Structured Data' : 'Text Output'}
                <span className="mx-2">•</span>
                <span className="icon is-small mr-1">
                  <i className="fas fa-text-height"></i>
                </span>
                {formatLogContent(logEntry.content).length} characters
              </p>
            </div>
          </div>
        </div>
        {isContentLong(logEntry.content) && (
          <div 
            className="card-header-icon"
            style={{ cursor: 'pointer' }}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span className="icon">
              <i 
                className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}
                style={{ transition: 'transform 0.3s ease' }}
              ></i>
            </span>
          </div>
        )}
      </header>

      {/* Card Content */}
      <div className="card-content">
        <div className="content">
          {/* Content Preview or Full Content */}
          <div 
            className="code-content"
            style={{
              backgroundColor: 'white',
              border: '1px solid #dbdbdb',
              borderRadius: '4px',
              padding: '1rem',
              maxHeight: isExpanded ? 'none' : '300px',
              overflowY: isExpanded ? 'visible' : 'auto',
              fontFamily: 'monospace'
            }}
          >
            <pre 
              style={{ 
                whiteSpace: 'pre-wrap', 
                fontSize: '0.8rem',
                margin: 0,
                lineHeight: '1.4',
                backgroundColor: 'white',
                border: '1px solid #dbdbdb',
                borderRadius: '4px',
                padding: '1rem'
              }}
            >
              {isExpanded || !isContentLong(logEntry.content) 
                ? formatLogContent(logEntry.content)
                : getContentPreview(logEntry.content)
              }
            </pre>
          </div>

          {/* Toggle Button for Long Content */}
          {isContentLong(logEntry.content) && (
            <div className="has-text-centered mt-3">
              <button 
                className="button is-small is-text is-expander"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                <span className="icon is-small">
                  <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}></i>
                </span>
                <span>{isExpanded ? 'Show Less' : 'Show More'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function AdminAllCourse() {
  const { user, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [activeTab, setActiveTab] = useState('preview');
  const [showQuizPreview, setShowQuizPreview] = useState(false);
  const [quizPreviewData, setQuizPreviewData] = useState(null);
  const [activeQuizTab, setActiveQuizTab] = useState('preview');
  const [creatingQuiz, setCreatingQuiz] = useState(false);
  const [documentBase64, setDocumentBase64] = useState(null);
  
  // New state variables for course/quiz parameters
  const [difficulty, setDifficulty] = useState('Regular');
  const [numberOfQuestions, setNumberOfQuestions] = useState(10);
  const [numberOfChoices, setNumberOfChoices] = useState(4);
  const [numberOfSubjectiveQuestions, setNumberOfSubjectiveQuestions] = useState(2);
  const [numberOfFillInTheBlankQuestions, setNumberOfFillInTheBlankQuestions] = useState(2);
  
  // Store parameters for regeneration
  const [courseParams, setCourseParams] = useState(null);

  // Helper functions for number inputs
  const handleNumberChange = (setter, value, defaultValue, min = 0, max = 50) => {
    if (value === '') {
      setter(''); // Allow empty string temporarily
    } else {
      const numValue = parseInt(value);
      if (!isNaN(numValue) && numValue >= min && numValue <= max) {
        setter(numValue);
      }
    }
  };

  const handleNumberBlur = (setter, value, defaultValue, min = 0, max = 50) => {
    if (value === '' || isNaN(parseInt(value))) {
      setter(defaultValue);
    } else {
      const numValue = parseInt(value);
      if (numValue < min) setter(min);
      else if (numValue > max) setter(max);
      else setter(numValue);
    }
  };

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }
    fetchCourses();
  }, [user, navigate]);

  const fetchCourses = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/admin/courses', {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      if (response.ok) {
        const data = await response.json();
        setCourses(data.courses || []);
      } else {
        console.error('Failed to fetch courses');
      }
    } catch (error) {
      console.error('Error fetching courses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF file');
      event.target.value = '';
    }
  };

  const validateQuizParameters = () => {
    // Ensure all values are numbers
    const totalQuestions = typeof numberOfQuestions === 'number' ? numberOfQuestions : parseInt(numberOfQuestions) || 10;
    const choices = typeof numberOfChoices === 'number' ? numberOfChoices : parseInt(numberOfChoices) || 4;
    const subjective = typeof numberOfSubjectiveQuestions === 'number' ? numberOfSubjectiveQuestions : parseInt(numberOfSubjectiveQuestions) || 2;
    const fillInBlank = typeof numberOfFillInTheBlankQuestions === 'number' ? numberOfFillInTheBlankQuestions : parseInt(numberOfFillInTheBlankQuestions) || 2;
    
    const totalQuestionTypes = choices + subjective + fillInBlank;
    if (totalQuestionTypes > totalQuestions) {
      alert(`Total question types (${totalQuestionTypes}) cannot exceed total questions (${totalQuestions})`);
      return false;
    }
    return true;
  };

  const resetModalForm = () => {
    setSelectedFile(null);
    setDifficulty('Regular');
    setNumberOfQuestions(10);
    setNumberOfChoices(4);
    setNumberOfSubjectiveQuestions(2);
    setNumberOfFillInTheBlankQuestions(2);
  };

  const handleCloseModal = () => {
    setShowImportModal(false);
    resetModalForm();
  };

  const convertToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const base64String = reader.result.split(',')[1]; // Remove data:application/pdf;base64, prefix
        resolve(base64String);
      };
      reader.onerror = (error) => reject(error);
    });
  };

  const handleUploadDocument = async () => {
    if (!selectedFile) {
      alert('Please select a PDF file first');
      return;
    }

    if (!validateQuizParameters()) {
      return;
    }

    setUploading(true);
    try {
      const base64Document = await convertToBase64(selectedFile);
      
      // Store parameters for regeneration
      const params = {
        difficulty,
        numberOfQuestions: typeof numberOfQuestions === 'number' ? numberOfQuestions : parseInt(numberOfQuestions) || 10,
        numberOfChoices: typeof numberOfChoices === 'number' ? numberOfChoices : parseInt(numberOfChoices) || 4,
        numberOfSubjectiveQuestions: typeof numberOfSubjectiveQuestions === 'number' ? numberOfSubjectiveQuestions : parseInt(numberOfSubjectiveQuestions) || 2,
        numberOfFillInTheBlankQuestions: typeof numberOfFillInTheBlankQuestions === 'number' ? numberOfFillInTheBlankQuestions : parseInt(numberOfFillInTheBlankQuestions) || 2
      };
      setCourseParams(params);
      
      const response = await fetch('http://localhost:5000/api/create-course/preview', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          DocumentBased64: base64Document,
          difficulty_level: difficulty
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPreviewData(data);
        setDocumentBase64(base64Document); // Store document for quiz creation
        setShowImportModal(false);
        setShowPreview(true);
        setSelectedFile(null);
      } else {
        alert('Failed to process document. Please try again.');
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      alert('Error processing document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleReGenerate = async () => {
    if (!documentBase64) {
      alert('No document to regenerate from');
      return;
    }
    
    if (!courseParams) {
      alert('No course parameters available for regeneration');
      return;
    }
    
    setUploading(true);
    try {
      const response = await fetch('http://localhost:5000/api/create-course/preview', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          DocumentBased64: documentBase64,
          difficulty_level: courseParams.difficulty
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPreviewData(data);
      } else {
        alert('Failed to regenerate course. Please try again.');
      }
    } catch (error) {
      console.error('Error regenerating course:', error);
      alert('Error regenerating course. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleCreateQuiz = async () => {
    if (!documentBase64) {
      alert('No document to create quiz from');
      return;
    }
    
    if (!courseParams) {
      alert('No course parameters available for quiz creation');
      return;
    }
    
    setCreatingQuiz(true);
    try {
      const response = await fetch('http://localhost:5000/api/create-quiz/preview', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          DocumentBased64: documentBase64,
          number_of_questions: courseParams.numberOfQuestions,
          number_of_choices: courseParams.numberOfChoices,
          number_of_subjective_questions: courseParams.numberOfSubjectiveQuestions,
          number_of_fill_in_the_blank_questions: courseParams.numberOfFillInTheBlankQuestions,
          difficulty_level: courseParams.difficulty
        })
      });

      if (response.ok) {
        const data = await response.json();
        setQuizPreviewData(data);
        setShowPreview(false);
        setShowQuizPreview(true);
        // Keep previewData available for quiz submission
      } else {
        alert('Failed to create quiz. Please try again.');
      }
    } catch (error) {
      console.error('Error creating quiz:', error);
      alert('Error creating quiz. Please try again.');
    } finally {
      setCreatingQuiz(false);
    }
  };

  const handleReGenerateQuiz = async () => {
    if (!documentBase64) {
      alert('No document to regenerate quiz from');
      return;
    }
    
    if (!courseParams) {
      alert('No course parameters available for quiz regeneration');
      return;
    }
    
    setCreatingQuiz(true);
    try {
      const response = await fetch('http://localhost:5000/api/create-quiz/preview', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          DocumentBased64: documentBase64,
          number_of_questions: courseParams.numberOfQuestions,
          number_of_choices: courseParams.numberOfChoices,
          number_of_subjective_questions: courseParams.numberOfSubjectiveQuestions,
          number_of_fill_in_the_blank_questions: courseParams.numberOfFillInTheBlankQuestions,
          difficulty_level: courseParams.difficulty
        })
      });

      if (response.ok) {
        const data = await response.json();
        setQuizPreviewData(data);
      } else {
        alert('Failed to regenerate quiz. Please try again.');
      }
    } catch (error) {
      console.error('Error regenerating quiz:', error);
      alert('Error regenerating quiz. Please try again.');
    } finally {
      setCreatingQuiz(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quizPreviewData) {
      alert('No quiz data to submit');
      return;
    }
    
    if (!previewData) {
      alert('No course data to submit. Please generate course first.');
      return;
    }
    
    setCreatingQuiz(true);
    try {
      // Ensure the quiz has the same course_id as the course
      const courseId = previewData.output.course.course_id;
      const updatedQuizData = {
        ...quizPreviewData.output.quiz,
        course_id: courseId
      };

      // Combine course data and quiz data
      const combinedData = {
        course: previewData.output.course,
        lessons: previewData.output.lessons,
        lesson_contents: previewData.output.lesson_contents,
        quiz: updatedQuizData,
        questions: quizPreviewData.output.questions,
        choices: quizPreviewData.output.choices,
        answers: quizPreviewData.output.answers
      };

      console.log('Submitting combined data:', combinedData);

      const response = await fetch('http://localhost:5000/api/create-quiz/submit', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          quiz_data: combinedData
        })
      });

      if (response.ok) {
        const result = await response.json();
        alert('Course and Quiz saved to database successfully!');
        setShowQuizPreview(false);
        setQuizPreviewData(null);
        setPreviewData(null); // Clear course preview data too
        setSelectedFile(null);
        setDocumentBase64(null);
        fetchCourses(); // Refresh courses list
      } else {
        const errorData = await response.text();
        console.error('Failed to save quiz:', errorData);
        alert(`Failed to save quiz: ${errorData}`);
      }
    } catch (error) {
      console.error('Error saving quiz:', error);
      alert(`Error saving quiz: ${error.message}`);
    } finally {
      setCreatingQuiz(false);
    }
  };

  const filteredCourses = courses.filter(course =>
    course.course_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (course.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getDifficultyColor = (difficulty) => {
    switch (difficulty?.toLowerCase()) {
      case 'casual': return 'is-info';
      case 'regular': return 'is-warning';
      case 'intense': return 'is-danger';
      default: return 'is-info';
    }
  };

  if (showPreview && previewData) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          {/* Page Header */}
          <div className="box home-overview-card">
            <div className="columns is-vcentered">
              <div className="column">
                <div className="is-size-4 has-text-weight-bold mb-2">Course Preview</div>
                <div className="is-size-6 has-text-grey">Review the generated course content</div>
              </div>
              <div className="column is-narrow">
                <button 
                  className="button is-light mr-2"
                  onClick={() => {
                    setShowPreview(false);
                    setDocumentBase64(null);
                    setPreviewData(null);
                  }}
                >
                  <span className="icon">
                    <i className="fas fa-arrow-left"></i>
                  </span>
                  <span>Back to Courses</span>
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="box home-courses-card">
            <div className="tabs is-boxed">
              <ul>
                <li className={activeTab === 'preview' ? 'is-active' : ''}>
                  <a 
                    onClick={() => setActiveTab('preview')}
                    style={{ 
                      color: activeTab === 'preview' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeTab === 'preview' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (activeTab !== 'preview') {
                        e.target.style.color = 'var(--primary-yellow)';
                        e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (activeTab !== 'preview') {
                        e.target.style.color = 'white';
                        e.target.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-eye"></i>
                    </span>
                    <span>Course Preview</span>
                  </a>
                </li>
                <li className={activeTab === 'logs' ? 'is-active' : ''}>
                  <a 
                    onClick={() => setActiveTab('logs')}
                    style={{ 
                      color: activeTab === 'logs' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeTab === 'logs' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (activeTab !== 'logs') {
                        e.target.style.color = 'var(--primary-yellow)';
                        e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (activeTab !== 'logs') {
                        e.target.style.color = 'white';
                        e.target.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-code"></i>
                    </span>
                    <span>Agent Logs</span>
                  </a>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            {activeTab === 'preview' && (
              <div className="content">
                <div className="columns">
                  <div className="column">
                    <h3 className="title is-4">{previewData.output.course.course_name}</h3>
                    <p className="subtitle is-6">{previewData.output.course.description}</p>
                    
                    <div className="columns is-mobile mb-4">
                      <div className="column">
                        <div className="field">
                          <label className="label">Duration</label>
                          <div className="control">
                            <span className="tag is-info">{previewData.output.course.total_hour} hours</span>
                          </div>
                        </div>
                      </div>
                      <div className="column">
                        <div className="field">
                          <label className="label">Difficulty</label>
                          <div className="control">
                            <span className={`tag ${getDifficultyColor(previewData.output.course.difficulty_level)}`}>
                              {previewData.output.course.difficulty_level}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="field">
                      <label className="label">Learning Objectives</label>
                      <div className="content">
                        <ul>
                          {previewData.output.course.learning_objectives?.map((objective, index) => (
                            <li key={index}>{objective}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="field">
                      <label className="label">Prerequisites</label>
                      <div className="content">
                        <ul>
                          {previewData.output.course.prerequisites?.map((prerequisite, index) => (
                            <li key={index}>{prerequisite}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="field">
                      <label className="label">Lessons ({previewData.output.lessons?.length || 0})</label>
                      <div className="content">
                        {previewData.output.lessons?.map((lesson, index) => {
                          const lessonContents = previewData.output.lesson_contents?.filter(
                            content => content.lesson_id === lesson.lesson_id
                          ).sort((a, b) => a.content_order - b.content_order);
                          
                          return (
                            <LessonExpander 
                              key={lesson.lesson_id}
                              lesson={lesson}
                              lessonContents={lessonContents}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'logs' && (
              <div className="content">
                <div className="field">
                  <label className="label">Agent Processing Logs</label>
                  <p className="subtitle is-6 has-text-grey mb-4">
                    View the step-by-step processing logs from the AI agents
                  </p>
                  {previewData.log?.map((logEntry, index) => (
                    <LogCard key={index} logEntry={logEntry} index={index} />
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="field is-grouped is-grouped-right mt-5">
              <div className="control">
                <button 
                  className={`button is-warning ${uploading ? 'is-loading' : ''}`}
                  onClick={handleReGenerate}
                  disabled={uploading}
                >
                  <span className="icon">
                    <i className="fas fa-sync-alt"></i>
                  </span>
                  <span>Re-Generate</span>
                </button>
              </div>
              <div className="control">
                <button 
                  className={`button is-info ${creatingQuiz ? 'is-loading' : ''}`}
                  onClick={handleCreateQuiz}
                  disabled={creatingQuiz}
                >
                  <span className="icon">
                    <i className="fas fa-question-circle"></i>
                  </span>
                  <span>Create Quiz</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (showQuizPreview && quizPreviewData) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          {/* Page Header */}
          <div className="box home-overview-card">
            <div className="columns is-vcentered">
              <div className="column">
                <div className="is-size-4 has-text-weight-bold mb-2">Quiz Preview</div>
                <div className="is-size-6 has-text-grey">Review the generated quiz content</div>
              </div>
              <div className="column is-narrow">
                <button 
                  className="button is-light mr-2"
                  onClick={() => {
                    setShowQuizPreview(false);
                    setShowPreview(true); // Go back to course preview instead
                  }}
                >
                  <span className="icon">
                    <i className="fas fa-arrow-left"></i>
                  </span>
                  <span>Back to Course Preview</span>
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="box home-courses-card">
            <div className="tabs is-boxed">
              <ul>
                <li className={activeQuizTab === 'preview' ? 'is-active' : ''}>
                  <a 
                    onClick={() => setActiveQuizTab('preview')}
                    style={{ 
                      color: activeQuizTab === 'preview' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeQuizTab === 'preview' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (activeQuizTab !== 'preview') {
                        e.target.style.color = 'var(--primary-yellow)';
                        e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (activeQuizTab !== 'preview') {
                        e.target.style.color = 'white';
                        e.target.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-eye"></i>
                    </span>
                    <span>Quiz Preview</span>
                  </a>
                </li>
                <li className={activeQuizTab === 'logs' ? 'is-active' : ''}>
                  <a 
                    onClick={() => setActiveQuizTab('logs')}
                    style={{ 
                      color: activeQuizTab === 'logs' ? 'var(--primary-black)' : 'white',
                      backgroundColor: activeQuizTab === 'logs' ? 'white' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (activeQuizTab !== 'logs') {
                        e.target.style.color = 'var(--primary-yellow)';
                        e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (activeQuizTab !== 'logs') {
                        e.target.style.color = 'white';
                        e.target.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-code"></i>
                    </span>
                    <span>Agent Logs</span>
                  </a>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            {activeQuizTab === 'preview' && (
              <div className="content">
                <div className="columns">
                  <div className="column">
                    <h3 className="title is-4">{quizPreviewData.output.quiz.quiz_title}</h3>
                    <p className="subtitle is-6">{quizPreviewData.output.quiz.description}</p>
                    
                    <div className="columns is-mobile mb-4">
                      <div className="column">
                        <div className="field">
                          <label className="label">Difficulty</label>
                          <div className="control">
                            <span className={`tag ${getDifficultyColor(quizPreviewData.output.quiz.difficulty_level)}`}>
                              {quizPreviewData.output.quiz.difficulty_level}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="column">
                        <div className="field">
                          <label className="label">Total Questions</label>
                          <div className="control">
                            <span className="tag is-info">{quizPreviewData.output.questions?.length || 0} questions</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="field">
                      <label className="label">Questions</label>
                      <div className="content">
                        {quizPreviewData.output.questions?.map((question, index) => (
                          <div key={question.question_id} className="card mb-4">
                            <div className="card-content">
                              <div className="content">
                                <div className="is-flex is-align-items-center mb-2">
                                  <span className="tag is-primary mr-2">Q{index + 1}</span>
                                  <span className={`tag ${question.question_type === 'Multiple Choice' ? 'is-info' : question.question_type === 'Subjective' ? 'is-success' : 'is-warning'} mr-2`}>
                                    {question.question_type}
                                  </span>
                                  <span className="tag is-light">{question.points} pts</span>
                                </div>
                                <p className="has-text-weight-semibold mb-3">{question.question_text}</p>
                                
                                {question.question_type === 'Multiple Choice' && (
                                  <div className="content">
                                    <p className="has-text-weight-semibold mb-2">Choices:</p>
                                    {quizPreviewData.output.choices?.filter(choice => choice.question_id === question.question_id).map((choice, idx) => (
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
                                
                                {question.question_type === 'Subjective' && (
                                  <div className="content">
                                    <p className="has-text-weight-semibold mb-2">Expected Answer:</p>
                                    {quizPreviewData.output.answers?.filter(answer => answer.question_id === question.question_id).map((answer) => (
                                      <div key={answer.answer_id} className="box has-background-light">
                                        <p className="has-text-weight-semibold">{answer.answer_text}</p>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                
                                {question.question_type === 'Fill in the Blank' && (
                                  <div className="content">
                                    <p className="has-text-weight-semibold mb-2">Correct Answer:</p>
                                    {quizPreviewData.output.answers?.filter(answer => answer.question_id === question.question_id).map((answer) => (
                                      <span key={answer.answer_id} className="tag is-success is-medium">
                                        {answer.answer_text}
                                      </span>
                                    ))}
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
              </div>
            )}

            {activeQuizTab === 'logs' && (
              <div className="content">
                <div className="field">
                  <label className="label">Agent Processing Logs</label>
                  <p className="subtitle is-6 has-text-grey mb-4">
                    View the step-by-step processing logs from the AI agents
                  </p>
                  {quizPreviewData.log?.map((logEntry, index) => (
                    <LogCard key={index} logEntry={logEntry} index={index} />
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="field is-grouped is-grouped-right mt-5">
              <div className="control">
                <button 
                  className={`button is-warning ${creatingQuiz ? 'is-loading' : ''}`}
                  onClick={handleReGenerateQuiz}
                  disabled={creatingQuiz}
                >
                  <span className="icon">
                    <i className="fas fa-sync-alt"></i>
                  </span>
                  <span>Re-Generate</span>
                </button>
              </div>
              <div className="control">
                <button 
                  className={`button is-success ${creatingQuiz ? 'is-loading' : ''}`}
                  onClick={handleSubmitQuiz}
                  disabled={creatingQuiz}
                >
                  <span className="icon">
                    <i className="fas fa-save"></i>
                  </span>
                  <span>Submit Quiz</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-home-bg">
      <Header />
      <div className="container mt-4">
        {/* Page Header */}
        <div className="box home-overview-card">
          <div className="columns is-vcentered">
            <div className="column">
              <div className="is-size-4 has-text-weight-bold mb-2">All Courses</div>
              <div className="is-size-6 has-text-grey">View and manage all courses in the system</div>
            </div>
            <div className="column is-narrow">
              <button 
                className="button is-primary"
                onClick={() => setShowImportModal(true)}
              >
                <span className="icon">
                  <i className="fas fa-upload"></i>
                </span>
                <span>Import Document</span>
              </button>
            </div>
          </div>
        </div>

        {/* Search Bar */}
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

        {/* Courses Grid */}
        <div className="container mt-4 mb-6">
          {loading ? (
            <div className="box home-courses-card has-text-centered">
              <div className="is-size-5 has-text-grey">Loading courses...</div>
            </div>
          ) : (
            <div className="box home-courses-card">
              <div className="columns is-multiline">
                {filteredCourses.length > 0 ? (
                  filteredCourses.map((course) => (
                    <div className="column is-4" key={course.course_id}>
                      <div className="box home-course-row" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <div className="mb-3" style={{ flex: '1' }}>
                          <div className="is-flex is-justify-content-space-between is-align-items-center mb-2">
                            <div className="is-size-6 has-text-weight-bold">{course.course_name}</div>
                            <span className={`tag ${getDifficultyColor(course.difficulty_level)}`}>{course.difficulty_level}</span>
                          </div>
                          <div className="is-size-7 has-text-grey mb-2" style={{ minHeight: '3rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
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
                        <div className="is-flex is-justify-content-space-between is-align-items-center">
                          <span className="tag is-light">
                            <i className="fas fa-users mr-1"></i>
                            {course.enrolled_count || 0} enrolled
                          </span>
                          <button
                            className="button is-small is-info"
                            onClick={() => navigate(`/admin/course/${course.course_id}`)}
                          >
                            View Details
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
                        {searchTerm
                          ? 'Try adjusting your search criteria'
                          : 'No courses are available at the moment'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Import Document Modal */}
      <div className={`modal ${showImportModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={handleCloseModal}></div>
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
              Import Document to Create Course
            </p>
            <button 
              className="delete" 
              aria-label="close"
              onClick={handleCloseModal}
            ></button>
          </header>
          <section 
            className="modal-card-body" 
            style={{ backgroundColor: 'white', maxHeight: '70vh', overflowY: 'auto' }}
          >
            <div className="field">
              <label 
                className="label" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontWeight: '600' 
                }}
              >
                Upload PDF Document
              </label>
              <div className="control">
                <div className="file has-name is-fullwidth">
                  <label className="file-label">
                    <input 
                      className="file-input" 
                      type="file" 
                      accept=".pdf"
                      onChange={handleFileChange}
                    />
                    <span 
                      className="file-cta"
                      style={{
                        backgroundColor: 'var(--primary-yellow)',
                        borderColor: 'var(--medium-grey)',
                        color: 'var(--primary-black)'
                      }}
                    >
                      <span className="file-icon">
                        <i className="fas fa-upload"></i>
                      </span>
                      <span className="file-label">Choose PDF file...</span>
                    </span>
                    <span 
                      className="file-name"
                      style={{
                        backgroundColor: 'white',
                        borderColor: 'var(--medium-grey)',
                        color: 'var(--primary-black)'
                      }}
                    >
                      {selectedFile ? selectedFile.name : 'No file selected'}
                    </span>
                  </label>
                </div>
              </div>
              <p 
                className="help" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontSize: '0.875rem' 
                }}
              >
                Please upload a PDF document to generate course content. The AI will analyze the document and create structured lessons.
              </p>
            </div>

            {/* Course Configuration */}
            <div className="field">
              <label 
                className="label" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontWeight: '600' 
                }}
              >
                Course & Quiz Difficulty Level
              </label>
              <div className="control">
                <div className="select is-fullwidth">
                  <select 
                    value={difficulty} 
                    onChange={(e) => setDifficulty(e.target.value)}
                    style={{
                      backgroundColor: 'white',
                      borderColor: 'var(--medium-grey)',
                      color: 'var(--primary-black)'
                    }}
                  >
                    <option value="Casual">Casual - Basic concepts and fundamental understanding</option>
                    <option value="Regular">Regular - Intermediate concepts with moderate depth</option>
                    <option value="Intense">Intense - Advanced concepts and complex topics</option>
                  </select>
                </div>
              </div>
              <p 
                className="help" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontSize: '0.875rem' 
                }}
              >
                This difficulty level will be applied to both the course content and quiz questions.
              </p>
            </div>

            {/* Quiz Configuration */}
            <div className="field">
              <label 
                className="label" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontWeight: '600' 
                }}
              >
                Quiz Configuration
              </label>
              
              <div className="columns">
                <div className="column">
                  <div className="field">
                    <label className="label is-small">Total Questions</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="number" 
                        min="1" 
                        max="50"
                        value={numberOfQuestions}
                        onChange={(e) => handleNumberChange(setNumberOfQuestions, e.target.value, 10)}
                        onBlur={(e) => handleNumberBlur(setNumberOfQuestions, e.target.value, 10)}
                        style={{
                          backgroundColor: 'white',
                          borderColor: 'var(--medium-grey)',
                          color: 'var(--primary-black)'
                        }}
                      />
                    </div>
                  </div>
                </div>
                
                <div className="column">
                  <div className="field">
                    <label className="label is-small">Multiple Choice Questions</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="number" 
                        min="0" 
                        max={numberOfQuestions}
                        value={numberOfChoices}
                        onChange={(e) => handleNumberChange(setNumberOfChoices, e.target.value, 4)}
                        onBlur={(e) => handleNumberBlur(setNumberOfChoices, e.target.value, 4)}
                        style={{
                          backgroundColor: 'white',
                          borderColor: 'var(--medium-grey)',
                          color: 'var(--primary-black)'
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="columns">
                <div className="column">
                  <div className="field">
                    <label className="label is-small">Subjective Questions</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="number" 
                        min="0" 
                        max={numberOfQuestions}
                        value={numberOfSubjectiveQuestions}
                        onChange={(e) => handleNumberChange(setNumberOfSubjectiveQuestions, e.target.value, 2)}
                        onBlur={(e) => handleNumberBlur(setNumberOfSubjectiveQuestions, e.target.value, 2)}
                        style={{
                          backgroundColor: 'white',
                          borderColor: 'var(--medium-grey)',
                          color: 'var(--primary-black)'
                        }}
                      />
                    </div>
                  </div>
                </div>
                
                <div className="column">
                  <div className="field">
                    <label className="label is-small">Fill in the Blank Questions</label>
                    <div className="control">
                      <input 
                        className="input" 
                        type="number" 
                        min="0" 
                        max={numberOfQuestions}
                        value={numberOfFillInTheBlankQuestions}
                        onChange={(e) => handleNumberChange(setNumberOfFillInTheBlankQuestions, e.target.value, 2)}
                        onBlur={(e) => handleNumberBlur(setNumberOfFillInTheBlankQuestions, e.target.value, 2)}
                        style={{
                          backgroundColor: 'white',
                          borderColor: 'var(--medium-grey)',
                          color: 'var(--primary-black)'
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <p 
                className="help" 
                style={{ 
                  color: 'var(--primary-black)', 
                  fontSize: '0.875rem' 
                }}
              >
                Configure the number and types of questions for the quiz. The total of all question types should not exceed the total number of questions.
              </p>
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
              className={`button is-primary ${uploading ? 'is-loading' : ''}`}
              onClick={handleUploadDocument}
              disabled={!selectedFile || uploading}
              style={{
                backgroundColor: 'var(--primary-color)',
                borderColor: 'var(--primary-color)',
                color: 'white'
              }}
            >
              {uploading ? 'Processing...' : 'Upload & Generate Course'}
            </button>
            <button 
              className="button" 
              onClick={handleCloseModal}
              disabled={uploading}
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

export default AdminAllCourse; 