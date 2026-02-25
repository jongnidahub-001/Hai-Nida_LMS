import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlert } from '../contexts/AlertContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
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
const LessonExpander = ({ 
  lesson, 
  lessonContents, 
  courseInfo = null, 
  onLessonUpdate = null,
  getAuthHeader = null 
}) => {
  const { showAlert } = useAlert();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editPrompt, setEditPrompt] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regeneratedData, setRegeneratedData] = useState(null);
  const [showPreviewChanges, setShowPreviewChanges] = useState(false);

  const formatMarkdownContent = (content) => {
    if (!content) return '';
    
    // Basic markdown formatting for display (inline backticks -> bold to avoid grey boxes)
    // Order matters: match longest headers first (###### to #)
    return content
      .replace(/^######\s+(.*$)/gim, '<h6 class="title is-6 mt-3 mb-2">$1</h6>')
      .replace(/^#####\s+(.*$)/gim, '<h5 class="title is-5 mt-3 mb-2">$1</h5>')
      .replace(/^####\s+(.*$)/gim, '<h4 class="title is-5 mt-4 mb-2">$1</h4>')
      .replace(/^###\s+(.*$)/gim, '<h4 class="title is-5 mt-4 mb-2">$1</h4>')
      .replace(/^##\s+(.*$)/gim, '<h3 class="title is-4 mt-5 mb-3">$1</h3>')
      .replace(/^#\s+(.*$)/gim, '<h2 class="title is-3 mt-5 mb-3">$1</h2>')
      .replace(/`([^`]+)`/g, '<strong>$1</strong>')  // inline backticks -> bold (avoids grey code boxes)
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>');
  };

  const handleEditClick = (e) => {
    e.stopPropagation();
    setIsEditMode(true);
    setIsExpanded(true);
  };

  const handleRegenerateLesson = async () => {
    if (!editPrompt.trim() || !courseInfo || !getAuthHeader) return;
    
    setIsRegenerating(true);
    try {
      // Combine all current content for the API
      const currentContentText = lessonContents
        ?.map(c => c.content)
        .join('\n\n') || '';

      const response = await fetch(`${API_BASE_URL}/api/lesson/regenerate`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          course_name: courseInfo.course_name,
          course_description: courseInfo.description,
          difficulty_level: courseInfo.difficulty_level,
          lesson_id: lesson.lesson_id,
          lesson_order: lesson.lesson_order,
          lesson_title: lesson.lesson_title,
          duration_hours: lesson.duration_hours,
          what_you_will_learn: lesson.what_you_will_learn || [],
          current_content: currentContentText,
          user_prompt: editPrompt
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setRegeneratedData(data.data);
          setShowPreviewChanges(true);
        } else {
          showAlert('Failed to regenerate lesson. Please try again.', 'error');
        }
      } else {
        showAlert('Failed to regenerate lesson. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error regenerating lesson:', error);
      showAlert('Error regenerating lesson. Please try again.', 'error');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleSaveChanges = () => {
    if (onLessonUpdate && regeneratedData) {
      onLessonUpdate(lesson.lesson_id, regeneratedData);
    }
    setIsEditMode(false);
    setEditPrompt('');
    setRegeneratedData(null);
    setShowPreviewChanges(false);
  };

  const handleDiscardChanges = () => {
    setIsEditMode(false);
    setEditPrompt('');
    setRegeneratedData(null);
    setShowPreviewChanges(false);
  };

  // Use regenerated data if available for preview, otherwise use original
  const displayLesson = showPreviewChanges && regeneratedData ? regeneratedData.lesson : lesson;
  const displayContents = showPreviewChanges && regeneratedData ? regeneratedData.lesson_contents : lessonContents;

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
        onClick={() => !isEditMode && setIsExpanded(!isExpanded)}
        onMouseEnter={(e) => e.target.style.backgroundColor = '#f8f9fa'}
        onMouseLeave={(e) => e.target.style.backgroundColor = isExpanded ? '#f5f5f5' : 'white'}
      >
        <div className="card-header-title">
          <div className="is-flex is-align-items-center is-flex-grow-1">
            <span className="icon is-medium mr-3 has-text-info">
              <i className="fas fa-book"></i>
            </span>
            <div className="is-flex-grow-1">
              <p className="title is-6 mb-1">
                Lesson {displayLesson.lesson_order}: {displayLesson.lesson_title}
                {showPreviewChanges && (
                  <span className="tag is-warning is-light ml-2">Preview</span>
                )}
              </p>
              <p className="subtitle is-7 has-text-grey mb-0">
                <span className="icon is-small mr-1">
                  <i className="fas fa-clock"></i>
                </span>
                {displayLesson.duration_hours} hours
                {displayContents && displayContents.length > 0 && (
                  <>
                    <span className="mx-2">•</span>
                    <span className="icon is-small mr-1">
                      <i className="fas fa-file-alt"></i>
                    </span>
                    {displayContents.length} content item{displayContents.length !== 1 ? 's' : ''}
                  </>
                )}
              </p>
            </div>
            {/* Edit Button */}
            {courseInfo && onLessonUpdate && !isEditMode && (
              <button
                className="button is-small is-info is-outlined mr-3"
                onClick={handleEditClick}
                title="Edit Lesson"
              >
                <span className="icon is-small">
                  <i className="fas fa-edit"></i>
                </span>
                <span>Edit</span>
              </button>
            )}
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
        {/* Edit Mode UI */}
        {isEditMode && (
          <div className="notification is-info is-light mb-4">
            <div className="field">
              <label className="label">
                <span className="icon is-small mr-2">
                  <i className="fas fa-magic"></i>
                </span>
                Edit Prompt
              </label>
              <p className="help mb-2">
                Describe what changes you want to make to this lesson. The AI will regenerate the lesson based on your instructions.
              </p>
              <div className="control">
                <textarea
                  className="textarea"
                  placeholder="e.g., Make the content more beginner-friendly, add more practical examples, focus on real-world applications..."
                  value={editPrompt}
                  onChange={(e) => setEditPrompt(e.target.value)}
                  rows={3}
                  disabled={isRegenerating}
                />
              </div>
            </div>
            
            <div className="field is-grouped">
              <div className="control">
                <button
                  className={`button is-primary ${isRegenerating ? 'is-loading' : ''}`}
                  onClick={handleRegenerateLesson}
                  disabled={!editPrompt.trim() || isRegenerating}
                >
                  <span className="icon is-small">
                    <i className="fas fa-sync-alt"></i>
                  </span>
                  <span>Regenerate Lesson</span>
                </button>
              </div>
              
              {showPreviewChanges && (
                <>
                  <div className="control">
                    <button
                      className="button is-success"
                      onClick={handleSaveChanges}
                    >
                      <span className="icon is-small">
                        <i className="fas fa-check"></i>
                      </span>
                      <span>Save Changes</span>
                    </button>
                  </div>
                  <div className="control">
                    <button
                      className="button is-danger is-outlined"
                      onClick={handleDiscardChanges}
                    >
                      <span className="icon is-small">
                        <i className="fas fa-times"></i>
                      </span>
                      <span>Discard Changes</span>
                    </button>
                  </div>
                </>
              )}
              
              {!showPreviewChanges && (
                <div className="control">
                  <button
                    className="button is-light"
                    onClick={handleDiscardChanges}
                    disabled={isRegenerating}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-times"></i>
                    </span>
                    <span>Cancel</span>
                  </button>
                </div>
              )}
            </div>
            
            {showPreviewChanges && (
              <div className="notification is-warning is-light mt-3 mb-0">
                <span className="icon is-small mr-2">
                  <i className="fas fa-eye"></i>
                </span>
                <strong>Preview Mode:</strong> Review the changes below. Click "Save Changes" to apply or "Discard Changes" to revert.
              </div>
            )}
          </div>
        )}

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
              {displayLesson.what_you_will_learn?.map((item, idx) => (
                <li key={idx} className="mb-1">{item}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Lesson Content */}
        {displayContents && displayContents.length > 0 && (
          <div className="content">
            <h6 className="title is-6 mb-3 has-text-primary">
              <span className="icon is-small mr-2">
                <i className="fas fa-book-open"></i>
              </span>
              Lesson Content
            </h6>
            
            {displayContents.map((contentItem, index) => (
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

// QuestionExpander Component for Quiz Preview
const QuestionExpander = ({
  question,
  questionIndex,
  choices,
  answers,
  quizInfo = null,
  documentContent = '',
  onQuestionUpdate = null,
  getAuthHeader = null
}) => {
  const { showAlert } = useAlert();
  const [isEditMode, setIsEditMode] = useState(false);
  const [editPrompt, setEditPrompt] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regeneratedData, setRegeneratedData] = useState(null);
  const [showPreviewChanges, setShowPreviewChanges] = useState(false);

  const handleEditClick = (e) => {
    e.stopPropagation();
    setIsEditMode(true);
  };

  const handleRegenerateQuestion = async () => {
    if (!editPrompt.trim() || !quizInfo || !getAuthHeader) return;
    
    setIsRegenerating(true);
    try {
      // Format current choices and answer for the API
      const currentChoicesText = choices
        ?.map((c, idx) => `${idx + 1}. ${c.choice_text}${c.is_correct ? ' (correct)' : ''}`)
        .join('\n') || 'N/A';
      
      const currentAnswerText = answers
        ?.map(a => a.answer_text)
        .join(', ') || 'N/A';

      const response = await fetch(`${API_BASE_URL}/api/question/regenerate`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document_content: documentContent,
          quiz_title: quizInfo.quiz_title,
          quiz_description: quizInfo.description,
          difficulty_level: quizInfo.difficulty_level,
          question_id: question.question_id,
          question_type: question.question_type,
          question_text: question.question_text,
          points: question.points,
          current_choices: currentChoicesText,
          current_answer: currentAnswerText,
          user_prompt: editPrompt
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setRegeneratedData(data.data);
          setShowPreviewChanges(true);
        } else {
          showAlert('Failed to regenerate question. Please try again.', 'error');
        }
      } else {
        showAlert('Failed to regenerate question. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error regenerating question:', error);
      showAlert('Error regenerating question. Please try again.', 'error');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleSaveChanges = () => {
    if (onQuestionUpdate && regeneratedData) {
      onQuestionUpdate(question.question_id, regeneratedData);
    }
    setIsEditMode(false);
    setEditPrompt('');
    setRegeneratedData(null);
    setShowPreviewChanges(false);
  };

  const handleDiscardChanges = () => {
    setIsEditMode(false);
    setEditPrompt('');
    setRegeneratedData(null);
    setShowPreviewChanges(false);
  };

  // Use regenerated data if available for preview, otherwise use original
  const displayQuestion = showPreviewChanges && regeneratedData ? regeneratedData.question : question;
  const displayChoices = showPreviewChanges && regeneratedData ? regeneratedData.choices : choices;
  const displayAnswers = showPreviewChanges && regeneratedData ? regeneratedData.answers : answers;

  return (
    <div className="card mb-4">
      <div className="card-content">
        <div className="content">
          {/* Question Header */}
          <div className="is-flex is-align-items-center is-justify-content-space-between mb-2">
            <div className="is-flex is-align-items-center">
              <span className="tag is-primary mr-2">Q{questionIndex + 1}</span>
              <span className={`tag ${displayQuestion.question_type === 'Multiple Choice' ? 'is-info' : displayQuestion.question_type === 'Subjective' ? 'is-success' : 'is-warning'} mr-2`}>
                {displayQuestion.question_type}
              </span>
              <span className="tag is-light">{displayQuestion.points} pts</span>
              {showPreviewChanges && (
                <span className="tag is-warning is-light ml-2">Preview</span>
              )}
            </div>
            {/* Edit Button */}
            {quizInfo && onQuestionUpdate && !isEditMode && (
              <button
                className="button is-small is-info is-outlined"
                onClick={handleEditClick}
                title="Edit Question"
              >
                <span className="icon is-small">
                  <i className="fas fa-edit"></i>
                </span>
                <span>Edit</span>
              </button>
            )}
          </div>

          {/* Edit Mode UI */}
          {isEditMode && (
            <div className="notification is-info is-light mb-4">
              <div className="field">
                <label className="label">
                  <span className="icon is-small mr-2">
                    <i className="fas fa-magic"></i>
                  </span>
                  Edit Prompt
                </label>
                <p className="help mb-2">
                  Describe what changes you want to make to this question. The AI will regenerate the question based on your instructions.
                </p>
                <div className="control">
                  <textarea
                    className="textarea"
                    placeholder="e.g., Make the question harder, add more distractors, change to fill-in-the-blank format..."
                    value={editPrompt}
                    onChange={(e) => setEditPrompt(e.target.value)}
                    rows={3}
                    disabled={isRegenerating}
                  />
                </div>
              </div>
              
              <div className="field is-grouped">
                <div className="control">
                  <button
                    className={`button is-primary ${isRegenerating ? 'is-loading' : ''}`}
                    onClick={handleRegenerateQuestion}
                    disabled={!editPrompt.trim() || isRegenerating}
                  >
                    <span className="icon is-small">
                      <i className="fas fa-sync-alt"></i>
                    </span>
                    <span>Regenerate Question</span>
                  </button>
                </div>
                
                {showPreviewChanges && (
                  <>
                    <div className="control">
                      <button
                        className="button is-success"
                        onClick={handleSaveChanges}
                      >
                        <span className="icon is-small">
                          <i className="fas fa-check"></i>
                        </span>
                        <span>Save Changes</span>
                      </button>
                    </div>
                    <div className="control">
                      <button
                        className="button is-danger is-outlined"
                        onClick={handleDiscardChanges}
                      >
                        <span className="icon is-small">
                          <i className="fas fa-times"></i>
                        </span>
                        <span>Discard Changes</span>
                      </button>
                    </div>
                  </>
                )}
                
                {!showPreviewChanges && (
                  <div className="control">
                    <button
                      className="button is-light"
                      onClick={handleDiscardChanges}
                      disabled={isRegenerating}
                    >
                      <span className="icon is-small">
                        <i className="fas fa-times"></i>
                      </span>
                      <span>Cancel</span>
                    </button>
                  </div>
                )}
              </div>
              
              {showPreviewChanges && (
                <div className="notification is-warning is-light mt-3 mb-0">
                  <span className="icon is-small mr-2">
                    <i className="fas fa-eye"></i>
                  </span>
                  <strong>Preview Mode:</strong> Review the changes below. Click "Save Changes" to apply or "Discard Changes" to revert.
                </div>
              )}
            </div>
          )}

          {/* Question Text */}
          <p className="has-text-weight-semibold mb-3">{displayQuestion.question_text}</p>
          
          {/* Multiple Choice Options */}
          {displayQuestion.question_type === 'Multiple Choice' && displayChoices && (
            <div className="content">
              <p className="has-text-weight-semibold mb-2">Choices:</p>
              {displayChoices.map((choice, idx) => (
                <div key={choice.choice_id || idx} className="field">
                  <div className="control">
                    <label className="radio">
                      <input type="radio" name={`question_${displayQuestion.question_id}`} disabled />
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
          
          {/* Subjective Answer */}
          {displayQuestion.question_type === 'Subjective' && displayAnswers && (
            <div className="content">
              <p className="has-text-weight-semibold mb-2">Expected Answer:</p>
              {displayAnswers.map((answer, idx) => (
                <div key={answer.answer_id || idx} className="box has-background-light">
                  <p className="has-text-weight-semibold">{answer.answer_text}</p>
                </div>
              ))}
            </div>
          )}
          
          {/* Fill in the Blank Answer */}
          {displayQuestion.question_type === 'Fill in the Blank' && displayAnswers && (
            <div className="content">
              <p className="has-text-weight-semibold mb-2">Correct Answer:</p>
              {displayAnswers.map((answer, idx) => (
                <span key={answer.answer_id || idx} className="tag is-success is-medium mr-2">
                  {answer.answer_text}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function AdminAllCourse() {
  const { user, getAuthHeader } = useAuth();
  const { showAlert, showConfirm } = useAlert();
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

  // Track task_id when previewing from Background Task (to update status to 'generated' on quiz submit)
  const [currentPreviewTaskId, setCurrentPreviewTaskId] = useState(null);

  // Document filename for default course name (filename without ext + difficulty)
  const [previewDocumentName, setPreviewDocumentName] = useState(null);

  // Background tasks state
  const [activeMainTab, setActiveMainTab] = useState('courses'); // 'courses' or 'process'
  const [backgroundTasks, setBackgroundTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [taskStats, setTaskStats] = useState({ pending: 0, generating: 0, done: 0, generated: 0, error: 0 });
  
  // Toast notification state
  const [toasts, setToasts] = useState([]);
  const [previousTaskStatuses, setPreviousTaskStatuses] = useState({});

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
    fetchBackgroundTasks();
  }, [user, navigate]);

  // Poll for task updates when on Process tab or when there are active tasks
  useEffect(() => {
    const hasActiveTasks = taskStats.pending > 0 || taskStats.generating > 0;
    
    if (activeMainTab === 'process' || hasActiveTasks) {
      const interval = setInterval(() => {
        fetchBackgroundTasks();
      }, 5000); // Poll every 5 seconds
      
      return () => clearInterval(interval);
    }
  }, [activeMainTab, taskStats.pending, taskStats.generating]);

  // Check for task completions and show toast notifications
  useEffect(() => {
    backgroundTasks.forEach(task => {
      const prevStatus = previousTaskStatuses[task.task_id];
      
      // If task just completed (was generating, now done)
      if (prevStatus === 'generating' && task.status === 'done') {
        showToast(`✅ ${task.difficulty_level} course generated successfully!`, 'success');
      }
      // If task just failed
      if (prevStatus === 'generating' && task.status === 'error') {
        showToast(`❌ ${task.difficulty_level} course generation failed`, 'danger');
      }
    });
    
    // Update previous statuses
    const newStatuses = {};
    backgroundTasks.forEach(task => {
      newStatuses[task.task_id] = task.status;
    });
    setPreviousTaskStatuses(newStatuses);
  }, [backgroundTasks]);

  // Toast notification functions
  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Fetch background tasks
  const fetchBackgroundTasks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/background-tasks`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const tasks = data.tasks || [];
        setBackgroundTasks(tasks);
        
        // Calculate stats
        const stats = {
          pending: tasks.filter(t => t.status === 'pending').length,
          generating: tasks.filter(t => t.status === 'generating').length,
          done: tasks.filter(t => t.status === 'done').length,
          generated: tasks.filter(t => t.status === 'generated').length,
          error: tasks.filter(t => t.status === 'error').length
        };
        setTaskStats(stats);
      }
    } catch (error) {
      console.error('Error fetching background tasks:', error);
    }
  };

  const fetchCourses = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/courses`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      if (response.ok) {
        const data = await response.json();
        console.log(data);
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
      showAlert('Please select a PDF file', 'warning');
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
      showAlert(`Total question types (${totalQuestionTypes}) cannot exceed total questions (${totalQuestions})`, 'warning');
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

  // Helper: get filename without extension for default course name
  const getFileNameWithoutExt = (filename) => {
    if (!filename) return 'Untitled';
    const lastDot = filename.lastIndexOf('.');
    return lastDot > 0 ? filename.substring(0, lastDot) : filename;
  };

  const handleUploadDocument = async () => {
    if (!selectedFile) {
      showAlert('Please select a PDF file first', 'warning');
      return;
    }

    if (!validateQuizParameters()) {
      return;
    }

    setUploading(true);
    try {
      const base64Document = await convertToBase64(selectedFile);
      
      // Build quiz parameters
      const quizParams = {
        numberOfQuestions: typeof numberOfQuestions === 'number' ? numberOfQuestions : parseInt(numberOfQuestions) || 10,
        numberOfChoices: typeof numberOfChoices === 'number' ? numberOfChoices : parseInt(numberOfChoices) || 4,
        numberOfSubjectiveQuestions: typeof numberOfSubjectiveQuestions === 'number' ? numberOfSubjectiveQuestions : parseInt(numberOfSubjectiveQuestions) || 2,
        numberOfFillInTheBlankQuestions: typeof numberOfFillInTheBlankQuestions === 'number' ? numberOfFillInTheBlankQuestions : parseInt(numberOfFillInTheBlankQuestions) || 2
      };
      
      // NEW: Call batch create endpoint to generate all 3 difficulty levels
      const response = await fetch(`${API_BASE_URL}/api/background-tasks/batch-create`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          DocumentBased64: base64Document,
          document_name: selectedFile.name,
          quiz_params: quizParams
        })
      });

      if (response.ok) {
        const data = await response.json();
        setShowImportModal(false);
        setSelectedFile(null);
        resetModalForm();
        setActiveMainTab('process'); // Switch to Process tab
        fetchBackgroundTasks(); // Refresh tasks
        showToast(`🚀 Created ${data.tasks.length} generation tasks for all difficulty levels!`, 'success');
      } else {
        showToast('Failed to create tasks. Please try again.', 'danger');
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      showToast('Error processing document. Please try again.', 'danger');
    } finally {
      setUploading(false);
    }
  };

  // Handle preview task from Process tab
  const handlePreviewTask = async (task) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/background-tasks/${task.task_id}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const taskData = data.task;
        
        if (taskData.result_data) {
          const difficultyLevel = taskData.difficulty_level || taskData.result_data.output?.course?.difficulty_level || 'Regular';
          const defaultCourseName = `${getFileNameWithoutExt(taskData.document_name || '')} (${difficultyLevel})`;
          const resultWithDefaultName = {
            ...taskData.result_data,
            output: {
              ...taskData.result_data.output,
              course: {
                ...taskData.result_data.output.course,
                course_name: defaultCourseName
              }
            }
          };
          setPreviewDocumentName(taskData.document_name);
          setPreviewData(resultWithDefaultName);
          setCourseParams(taskData.result_data.quiz_params || taskData.quiz_params);
          setDocumentBase64(taskData.document_base64);
          setCurrentPreviewTaskId(task.task_id);
          setShowPreview(true);
        } else {
          showToast('No preview data available for this task', 'warning');
        }
      } else {
        showToast('Failed to load task preview', 'danger');
      }
    } catch (error) {
      console.error('Error loading task preview:', error);
      showToast('Error loading task preview', 'danger');
    }
  };

  // Handle delete task
  const handleDeleteTask = async (taskId) => {
    const confirmed = await showConfirm('Are you sure you want to delete this task?', { 
      title: 'Confirm Delete',
      confirmText: 'Delete',
      cancelText: 'Cancel',
      type: 'danger'
    });
    if (!confirmed) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/background-tasks/${taskId}`, {
        method: 'DELETE',
        headers: {
          ...getAuthHeader()
        }
      });
      
      if (response.ok) {
        showToast('Task deleted successfully', 'success');
        fetchBackgroundTasks();
      } else {
        showToast('Failed to delete task', 'danger');
      }
    } catch (error) {
      console.error('Error deleting task:', error);
      showToast('Error deleting task', 'danger');
    }
  };

  // Handle retry failed task
  const handleRetryTask = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/background-tasks/${taskId}/retry`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        showToast(`Task queued for retry: ${data.message}`, 'info');
        fetchBackgroundTasks();
      } else {
        const error = await response.json();
        showToast(error.detail || 'Failed to retry task', 'danger');
      }
    } catch (error) {
      console.error('Error retrying task:', error);
      showToast('Error retrying task', 'danger');
    }
  };

  // Get status badge component
  const getStatusBadge = (task) => {
    switch (task.status) {
      case 'pending':
        return (
          <span className="tag is-light">
            <span className="icon is-small mr-1">
              <i className="fas fa-clock"></i>
            </span>
            Queued
          </span>
        );
      case 'generating':
        return (
          <div>
            <span className="tag is-warning">
              <span className="icon is-small mr-1">
                <i className="fas fa-spinner fa-spin"></i>
              </span>
              Generating
            </span>
            {task.progress && (
              <div className="mt-1">
                <progress 
                  className="progress is-small is-warning" 
                  value={task.progress_percent || 0} 
                  max="100"
                  style={{ marginBottom: '2px' }}
                >
                  {task.progress_percent}%
                </progress>
                <span className="is-size-7 has-text-grey">{task.progress}</span>
              </div>
            )}
          </div>
        );
      case 'done':
        return (
          <span className="tag is-success">
            <span className="icon is-small mr-1">
              <i className="fas fa-check"></i>
            </span>
            Completed
          </span>
        );
      case 'generated':
        return (
          <span className="tag is-info">
            <span className="icon is-small mr-1">
              <i className="fas fa-database"></i>
            </span>
            Generated
          </span>
        );
      case 'error':
        return (
          <div>
            <span className="tag is-danger" title={task.error_message}>
              <span className="icon is-small mr-1">
                <i className="fas fa-exclamation-triangle"></i>
              </span>
              Failed
            </span>
            {task.retry_count > 0 && (
              <span className="is-size-7 has-text-grey ml-1">
                (Retry {task.retry_count}/{task.max_retries || 3})
              </span>
            )}
          </div>
        );
      default:
        return <span className="tag">{task.status}</span>;
    }
  };

  const handleReGenerate = async () => {
    if (!documentBase64) {
      showAlert('No document to regenerate from', 'warning');
      return;
    }
    
    if (!courseParams) {
      showAlert('No course parameters available for regeneration', 'warning');
      return;
    }
    
    setUploading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/create-course/preview`, {
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
        // Apply default course name when we have document name (from task flow)
        if (previewDocumentName && courseParams?.difficulty) {
          const defaultCourseName = `${getFileNameWithoutExt(previewDocumentName)} (${courseParams.difficulty})`;
          data.output = {
            ...data.output,
            course: {
              ...data.output.course,
              course_name: defaultCourseName
            }
          };
        }
        setPreviewData(data);
      } else {
        showAlert('Failed to regenerate course. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error regenerating course:', error);
      showAlert('Error regenerating course. Please try again.', 'error');
    } finally {
      setUploading(false);
    }
  };

  // Handler for updating course name in preview
  const handleCourseNameChange = (newName) => {
    if (!previewData) return;
    setPreviewData({
      ...previewData,
      output: {
        ...previewData.output,
        course: {
          ...previewData.output.course,
          course_name: newName
        }
      }
    });
  };

  // Handler for updating a single lesson after regeneration
  const handleLessonUpdate = (lessonId, regeneratedData) => {
    if (!previewData) return;
    
    // Update the lesson in previewData
    const updatedLessons = previewData.output.lessons.map(lesson => {
      if (lesson.lesson_id === lessonId) {
        return {
          ...lesson,
          lesson_title: regeneratedData.lesson.lesson_title,
          duration_hours: regeneratedData.lesson.duration_hours,
          description: regeneratedData.lesson.description,
          what_you_will_learn: regeneratedData.lesson.what_you_will_learn
        };
      }
      return lesson;
    });
    
    // Remove old lesson contents for this lesson and add new ones
    const otherContents = previewData.output.lesson_contents.filter(
      content => content.lesson_id !== lessonId
    );
    const newContents = [...otherContents, ...regeneratedData.lesson_contents];
    
    // Update previewData
    setPreviewData({
      ...previewData,
      output: {
        ...previewData.output,
        lessons: updatedLessons,
        lesson_contents: newContents
      }
    });
  };

  // Handler for updating a single question after regeneration
  const handleQuestionUpdate = (questionId, regeneratedData) => {
    if (!quizPreviewData) return;
    
    // Update the question in quizPreviewData
    const updatedQuestions = quizPreviewData.output.questions.map(question => {
      if (question.question_id === questionId) {
        return {
          ...question,
          question_text: regeneratedData.question.question_text,
          question_type: regeneratedData.question.question_type,
          points: regeneratedData.question.points
        };
      }
      return question;
    });
    
    // Remove old choices for this question and add new ones with generated IDs
    const otherChoices = quizPreviewData.output.choices.filter(
      choice => choice.question_id !== questionId
    );
    const newChoices = regeneratedData.choices.map((choice, idx) => ({
      choice_id: `${questionId}_choice_${idx}`,
      question_id: questionId,
      choice_text: choice.choice_text,
      is_correct: choice.is_correct
    }));
    
    // Remove old answers for this question and add new ones with generated IDs
    const otherAnswers = quizPreviewData.output.answers.filter(
      answer => answer.question_id !== questionId
    );
    const newAnswers = regeneratedData.answers.map((answer, idx) => ({
      answer_id: `${questionId}_answer_${idx}`,
      question_id: questionId,
      answer_text: answer.answer_text
    }));
    
    // Update quizPreviewData
    setQuizPreviewData({
      ...quizPreviewData,
      output: {
        ...quizPreviewData.output,
        questions: updatedQuestions,
        choices: [...otherChoices, ...newChoices],
        answers: [...otherAnswers, ...newAnswers]
      }
    });
  };

  const handleCreateQuiz = async () => {
    if (!documentBase64) {
      showAlert('No document to create quiz from', 'warning');
      return;
    }
    
    if (!courseParams) {
      showAlert('No course parameters available for quiz creation', 'warning');
      return;
    }
    
    setCreatingQuiz(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/create-quiz/preview`, {
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
        showAlert('Failed to create quiz. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error creating quiz:', error);
      showAlert('Error creating quiz. Please try again.', 'error');
    } finally {
      setCreatingQuiz(false);
    }
  };

  const handleReGenerateQuiz = async () => {
    if (!documentBase64) {
      showAlert('No document to regenerate quiz from', 'warning');
      return;
    }
    
    if (!courseParams) {
      showAlert('No course parameters available for quiz regeneration', 'warning');
      return;
    }
    
    setCreatingQuiz(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/create-quiz/preview`, {
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
        showAlert('Failed to regenerate quiz. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Error regenerating quiz:', error);
      showAlert('Error regenerating quiz. Please try again.', 'error');
    } finally {
      setCreatingQuiz(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quizPreviewData) {
      showAlert('No quiz data to submit', 'warning');
      return;
    }
    
    if (!previewData) {
      showAlert('No course data to submit. Please generate course first.', 'warning');
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

      const response = await fetch(`${API_BASE_URL}/api/create-quiz/submit`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          quiz_data: combinedData,
          task_id: currentPreviewTaskId || undefined
        })
      });

      if (response.ok) {
        const result = await response.json();
        showAlert('Course and Quiz saved to database successfully!', 'success');
        setShowQuizPreview(false);
        setQuizPreviewData(null);
        setPreviewData(null); // Clear course preview data too
        setPreviewDocumentName(null);
        setSelectedFile(null);
        setDocumentBase64(null);
        setCurrentPreviewTaskId(null);
        fetchCourses(); // Refresh courses list
        fetchBackgroundTasks(); // Refresh to show status 'Generated'
      } else {
        const errorData = await response.text();
        console.error('Failed to save quiz:', errorData);
        showAlert(`Failed to save quiz: ${errorData}`, 'error');
      }
    } catch (error) {
      console.error('Error saving quiz:', error);
      showAlert(`Error saving quiz: ${error.message}`, 'error');
    } finally {
      setCreatingQuiz(false);
    }
  };

  const filteredCourses = courses.filter(course =>
    course.course_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (course.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );
  console.log(filteredCourses);

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
                    setPreviewDocumentName(null);
                    setCurrentPreviewTaskId(null);
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
                    <div className="field">
                      <label className="label">Course Name</label>
                      <div className="control">
                        <input
                          className="input is-medium"
                          type="text"
                          value={previewData.output.course.course_name || ''}
                          onChange={(e) => handleCourseNameChange(e.target.value)}
                          placeholder="Enter course name"
                          style={{
                            backgroundColor: 'white',
                            borderColor: 'var(--medium-grey)',
                            color: 'var(--primary-black)'
                          }}
                        />
                      </div>
                    </div>
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
                              courseInfo={previewData.output.course}
                              onLessonUpdate={handleLessonUpdate}
                              getAuthHeader={getAuthHeader}
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
                        {quizPreviewData.output.questions?.map((question, index) => {
                          const questionChoices = quizPreviewData.output.choices?.filter(
                            choice => choice.question_id === question.question_id
                          );
                          const questionAnswers = quizPreviewData.output.answers?.filter(
                            answer => answer.question_id === question.question_id
                          );
                          
                          return (
                            <QuestionExpander
                              key={question.question_id}
                              question={question}
                              questionIndex={index}
                              choices={questionChoices}
                              answers={questionAnswers}
                              quizInfo={quizPreviewData.output.quiz}
                              documentContent={documentBase64}
                              onQuestionUpdate={handleQuestionUpdate}
                              getAuthHeader={getAuthHeader}
                            />
                          );
                        })}
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
      
      {/* Toast Notifications */}
      <div style={{ 
        position: 'fixed', 
        top: '80px', 
        right: '20px', 
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {toasts.map(toast => (
          <div 
            key={toast.id} 
            className={`notification is-${toast.type}`}
            style={{
              minWidth: '300px',
              animation: 'slideIn 0.3s ease-out',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}
          >
            <button className="delete" onClick={() => removeToast(toast.id)}></button>
            {toast.message}
          </div>
        ))}
      </div>
      
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>

      <div className="container mt-4">
        {/* Page Header */}
        <div className="box home-overview-card">
          <div className="columns is-vcentered">
            <div className="column">
              <div className="is-size-4 has-text-weight-bold mb-2">Course Management</div>
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

        {/* Main Tab Navigation */}
        <div className="tabs is-boxed mb-4">
          <ul>
            <li className={activeMainTab === 'courses' ? 'is-active' : ''}>
              <a onClick={() => setActiveMainTab('courses')}>
                <span className="icon"><i className="fas fa-book"></i></span>
                <span>Courses</span>
              </a>
            </li>
            <li className={activeMainTab === 'process' ? 'is-active' : ''}>
              <a onClick={() => setActiveMainTab('process')}>
                <span className="icon"><i className="fas fa-tasks"></i></span>
                <span>Process</span>
                {(taskStats.pending > 0 || taskStats.generating > 0) && (
                  <span className="tag is-warning is-rounded ml-2" style={{ minWidth: '24px' }}>
                    {taskStats.pending + taskStats.generating}
                  </span>
                )}
              </a>
            </li>
          </ul>
        </div>

        {/* Courses Tab Content */}
        {activeMainTab === 'courses' && (
          <>
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
                            {course.enrollment_count || 0} enrolled
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
          </>
        )}

        {/* Process Tab Content */}
        {activeMainTab === 'process' && (
          <div className="box">
            <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
              <div>
                <h2 className="title is-4 mb-1">Background Tasks</h2>
                <p className="subtitle is-6 has-text-grey">
                  Monitor course generation progress for all difficulty levels
                </p>
              </div>
              <div className="buttons">
                <button 
                  className={`button is-small is-light ${loadingTasks ? 'is-loading' : ''}`} 
                  onClick={fetchBackgroundTasks}
                >
                  <span className="icon"><i className="fas fa-sync-alt"></i></span>
                  <span>Refresh</span>
                </button>
              </div>
            </div>
            
            {/* Stats Summary */}
            <div className="columns is-multiline mb-4">
              <div className="column is-2">
                <div className="notification is-light" style={{ padding: '1rem' }}>
                  <p className="heading">Queued</p>
                  <p className="title is-4">{taskStats.pending}</p>
                </div>
              </div>
              <div className="column is-2">
                <div className="notification is-warning is-light" style={{ padding: '1rem' }}>
                  <p className="heading">Generating</p>
                  <p className="title is-4">{taskStats.generating}</p>
                </div>
              </div>
              <div className="column is-2">
                <div className="notification is-success is-light" style={{ padding: '1rem' }}>
                  <p className="heading">Completed</p>
                  <p className="title is-4">{taskStats.done}</p>
                </div>
              </div>
              <div className="column is-2">
                <div className="notification is-info is-light" style={{ padding: '1rem' }}>
                  <p className="heading">Generated</p>
                  <p className="title is-4">{taskStats.generated}</p>
                </div>
              </div>
              <div className="column is-2">
                <div className="notification is-danger is-light" style={{ padding: '1rem' }}>
                  <p className="heading">Failed</p>
                  <p className="title is-4">{taskStats.error}</p>
                </div>
              </div>
            </div>
            
            {loadingTasks && backgroundTasks.length === 0 ? (
              <div className="has-text-centered py-6">
                <span className="icon is-large"><i className="fas fa-spinner fa-spin fa-2x"></i></span>
                <p className="mt-3">Loading tasks...</p>
              </div>
            ) : backgroundTasks.length === 0 ? (
              <div className="notification is-light has-text-centered">
                <span className="icon is-large has-text-grey-light">
                  <i className="fas fa-inbox fa-3x"></i>
                </span>
                <p className="mt-3 is-size-5">No background tasks</p>
                <p className="has-text-grey">Upload a document to start generating courses for all difficulty levels.</p>
                <button 
                  className="button is-primary mt-4"
                  onClick={() => setShowImportModal(true)}
                >
                  <span className="icon"><i className="fas fa-upload"></i></span>
                  <span>Import Document</span>
                </button>
              </div>
            ) : (
              <div className="table-container">
                <table className="table is-fullwidth is-hoverable">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Difficulty</th>
                      <th style={{ width: '200px' }}>Status</th>
                      <th>Created</th>
                      <th style={{ width: '180px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {backgroundTasks.map(task => (
                      <tr key={task.task_id}>
                        <td>
                          <span className="has-text-weight-medium">{task.document_name}</span>
                        </td>
                        <td>
                          <span className={`tag ${getDifficultyColor(task.difficulty_level)}`}>
                            {task.difficulty_level}
                          </span>
                        </td>
                        <td>
                          {getStatusBadge(task)}
                        </td>
                        <td>
                          <span className="is-size-7">
                            {new Date(task.created_at).toLocaleDateString()}<br/>
                            <span className="has-text-grey">
                              {new Date(task.created_at).toLocaleTimeString()}
                            </span>
                          </span>
                        </td>
                        <td>
                          <div className="buttons are-small">
                            {task.status === 'done' && (
                              <button 
                                className="button is-primary is-small"
                                onClick={() => handlePreviewTask(task)}
                              >
                                <span className="icon"><i className="fas fa-eye"></i></span>
                                <span>Preview</span>
                              </button>
                            )}
                            {(task.status === 'done' || task.status === 'generated') && (
                              <button 
                                className="button is-danger is-small is-outlined"
                                onClick={() => handleDeleteTask(task.task_id)}
                                title="Delete task"
                              >
                                <span className="icon"><i className="fas fa-trash"></i></span>
                              </button>
                            )}
                            {task.status === 'error' && (
                              <>
                                <button 
                                  className="button is-warning is-small"
                                  onClick={() => handleRetryTask(task.task_id)}
                                  title={`Retry (${task.retry_count || 0}/${task.max_retries || 3})`}
                                >
                                  <span className="icon"><i className="fas fa-redo"></i></span>
                                  <span>Retry</span>
                                </button>
                                <button 
                                  className="button is-danger is-small is-outlined"
                                  onClick={() => handleDeleteTask(task.task_id)}
                                >
                                  <span className="icon"><i className="fas fa-trash"></i></span>
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {/* Help text */}
            <div className="notification is-info is-light mt-4">
              <div className="content is-small">
                <p><strong>How it works:</strong></p>
                <ul>
                  <li>When you upload a document, <strong>3 tasks</strong> are created automatically (Casual, Regular, Intense)</li>
                  <li>Tasks are processed in the background - you can navigate away and come back</li>
                  <li>Click <strong>Preview</strong> on completed tasks to review and edit the generated content</li>
                  <li>Failed tasks can be <strong>retried</strong> up to 3 times</li>
                  <li>Tasks older than 7 days are automatically cleaned up</li>
                </ul>
              </div>
            </div>
          </div>
        )}
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

            {/* Difficulty Levels Info Box */}
            <div className="notification is-info is-light">
              <div className="content">
                <p className="has-text-weight-bold mb-2">
                  <span className="icon"><i className="fas fa-magic"></i></span>
                  All 3 difficulty levels will be generated automatically:
                </p>
                <div className="tags are-medium">
                  <span className="tag is-success">
                    <span className="icon"><i className="fas fa-leaf"></i></span>
                    <span>Casual</span>
                  </span>
                  <span className="tag is-warning">
                    <span className="icon"><i className="fas fa-balance-scale"></i></span>
                    <span>Regular</span>
                  </span>
                  <span className="tag is-danger">
                    <span className="icon"><i className="fas fa-fire"></i></span>
                    <span>Intense</span>
                  </span>
                </div>
                <p className="is-size-7 mt-2 mb-0">
                  Tasks will run in the background. Check the <strong>Process</strong> tab to monitor progress and preview completed courses.
                </p>
              </div>
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
              <span className="icon">
                <i className="fas fa-rocket"></i>
              </span>
              <span>{uploading ? 'Creating Tasks...' : 'Generate All Levels'}</span>
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