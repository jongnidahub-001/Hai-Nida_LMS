import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import './LessonPage.css';
import Header from '../components/Header';

function LessonPage() {
  const { courseId, lessonId } = useParams();
  const { user, logout, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  
  const [courseData, setCourseData] = useState(null);
  const [currentLesson, setCurrentLesson] = useState(null);
  const [lessonContent, setLessonContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [navigationLoading, setNavigationLoading] = useState(false);
  const [error, setError] = useState(null);
  const [allLessons, setAllLessons] = useState([]);
  const [currentLessonIndex, setCurrentLessonIndex] = useState(0);
  const [markCompleteLoading, setMarkCompleteLoading] = useState(false);

  useEffect(() => {
    // Set navigation loading if this is a lesson change (not initial load)
    if (currentLesson && currentLesson.lesson_id.toString() !== lessonId) {
      setNavigationLoading(true);
      setLessonContent(null); // Clear previous content immediately
    }
    fetchCourseData();
  }, [courseId, lessonId]);

  useEffect(() => {
    if (currentLesson) {
      fetchLessonContent();
    }
  }, [currentLesson]);

  const fetchCourseData = async () => {
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
        setAllLessons(data.lessons || []);
        
        // Find current lesson and its index
        const lessons = data.lessons || [];
        const lessonIndex = lessons.findIndex(lesson => lesson.lesson_id.toString() === lessonId);
        setCurrentLessonIndex(lessonIndex);
        
        if (lessonIndex !== -1) {
          setCurrentLesson(lessons[lessonIndex]);
        }
      } else {
        setError('Failed to fetch course details');
      }
    } catch (error) {
      console.error('Error fetching course details:', error);
      setError('Error loading course details');
    }
  };

  const fetchLessonContent = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/lesson-content/${lessonId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Lesson content response:', data);
        
        if (data.success && data.content && Array.isArray(data.content)) {
          setLessonContent(data.content);
        } else {
          console.log('No valid lesson content found, using fallback');
          setLessonContent(generateFallbackContent());
        }
      } else {
        console.log('API call failed, using fallback');
        setLessonContent(generateFallbackContent());
      }
    } catch (error) {
      console.error('Error fetching lesson content:', error);
      // Use fallback content if API fails
      setLessonContent(generateFallbackContent());
    } finally {
      setLoading(false);
      setNavigationLoading(false); // Clear navigation loading when content is ready
    }
  };

  const generateFallbackContent = () => {
    if (!currentLesson) return [];
    
    // Return all content for the lesson in a single continuous flow
    return [
      {
        content_id: 'fallback-1',
        lesson_id: lessonId,
        content_order: 1,
        content: `<h2>Welcome to ${currentLesson.lesson_title}</h2><p>${currentLesson.description || 'This lesson will cover fundamental concepts and practical applications.'}</p>`,
        content_type: 'text'
      },
      {
        content_id: 'fallback-2',
        lesson_id: lessonId,
        content_order: 2,
        content: 'test.mp4',
        content_type: 'video'
      },
      {
        content_id: 'fallback-3',
        lesson_id: lessonId,
        content_order: 3,
        content: `<h3>Learning Objectives</h3>
        <p>By the end of this lesson, you will be able to:</p>
        <ul>
          ${currentLesson.what_you_will_learn ? 
            currentLesson.what_you_will_learn.map(item => `<li>${item}</li>`).join('') :
            `<li>Understand the core concepts presented in this lesson</li>
             <li>Apply the knowledge in practical scenarios</li>
             <li>Implement best practices in real-world projects</li>`
          }
        </ul>`,
        content_type: 'text'
      },
      {
        content_id: 'fallback-4',
        lesson_id: lessonId,
        content_order: 4,
        content: `<h3>Theoretical Foundation</h3>
        <p>Let's explore the fundamental theory behind ${currentLesson.lesson_title}. Understanding these concepts is crucial for building a solid foundation in this topic.</p>
        <h4>Key Concepts:</h4>
        <ul>
          <li><strong>Primary Principles:</strong> The core ideas that drive this field</li>
          <li><strong>Historical Context:</strong> How these concepts evolved over time</li>
          <li><strong>Modern Applications:</strong> Current use cases and implementations</li>
        </ul>`,
        content_type: 'text'
      },
      {
        content_id: 'fallback-5',
        lesson_id: lessonId,
        content_order: 5,
        content: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        content_type: 'video'
      },
      {
        content_id: 'fallback-6',
        lesson_id: lessonId,
        content_order: 6,
        content: `<h3>Hands-On Practice</h3>
        <p>Time to put theory into practice! This section contains step-by-step examples and interactive demonstrations.</p>
        <h4>Example 1: Basic Implementation</h4>
        <p>Let's start with a simple example that demonstrates the core concepts in action.</p>
        <p><strong>Duration:</strong> ${currentLesson.duration_hours} hours</p>
        <p><strong>Lesson:</strong> ${currentLesson.lesson_order} in the course sequence</p>`,
        content_type: 'text'
      },
      {
        content_id: 'fallback-7',
        lesson_id: lessonId,
        content_order: 7,
        content: `<h3>Practice Exercises</h3>
        <p>Test your understanding with these interactive exercises. Each exercise builds upon the concepts learned in this lesson.</p>
        <h4>Exercise 1: Basic Application</h4>
        <p>Apply the fundamental concepts to solve this practical problem.</p>
        <p><strong>Challenge:</strong> Implement a solution using the principles discussed. Consider edge cases and optimization opportunities.</p>`,
        content_type: 'text'
      },
      {
        content_id: 'fallback-8',
        lesson_id: lessonId,
        content_order: 8,
        content: `<h3>Summary and Additional Resources</h3>
        <p>Congratulations! You've completed this lesson. Here's what you've accomplished:</p>
        <ul>
          <li>✅ Mastered the theoretical foundations</li>
          <li>✅ Worked through practical examples</li>
          <li>✅ Completed hands-on exercises</li>
        </ul>
        <h4>Recommended Reading</h4>
        <ul>
          <li>Documentation and official guides</li>
          <li>Industry best practices and standards</li>
          <li>Case studies and real-world implementations</li>
        </ul>
        <h4>What's Next?</h4>
        <p>In the next lesson, we'll build upon these concepts and explore advanced topics. Make sure you're comfortable with the material before proceeding.</p>
        <div class="notification is-info is-light">
          <p><strong>Note:</strong> This is placeholder content. The actual lesson content should be loaded from the content collection in ChromaDB.</p>
        </div>`,
        content_type: 'text'
      }
    ];
  };

  const markLessonComplete = async () => {
    setMarkCompleteLoading(true);
    try {
      console.log('Marking lesson complete:', { lessonId, courseId });
      
      const response = await fetch(`http://localhost:5000/api/lesson-complete`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          lesson_id: lessonId,
          course_id: courseId
        })
      });
      
      console.log('Response status:', response.status);
      const responseData = await response.json();
      console.log('Response data:', responseData);
      
      if (response.ok) {
        // Update lesson status
        setCurrentLesson(prev => ({ ...prev, status: 'Complete' }));
        // Refresh course data to update progress
        fetchCourseData();
        console.log('Lesson marked as complete successfully');
      } else {
        console.error('Failed to mark lesson complete:', responseData);
        // Show error message to user
        alert(`Failed to mark lesson complete: ${responseData.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error marking lesson complete:', error);
      alert(`Error marking lesson complete: ${error.message}`);
    } finally {
      setMarkCompleteLoading(false);
    }
  };

  const navigateToLesson = (direction) => {
    const newIndex = direction === 'next' ? currentLessonIndex + 1 : currentLessonIndex - 1;
    if (newIndex >= 0 && newIndex < allLessons.length) {
      setNavigationLoading(true);
      setLessonContent(null); // Clear current content immediately
      const nextLesson = allLessons[newIndex];
      navigate(`/course/${courseId}/lesson/${nextLesson.lesson_id}`);
    }
  };

  const navigateToSpecificLesson = (lessonId) => {
    if (lessonId !== currentLesson?.lesson_id.toString()) {
      setNavigationLoading(true);
      setLessonContent(null); // Clear current content immediately
      navigate(`/course/${courseId}/lesson/${lessonId}`);
    }
  };

  // Helper function to detect if content is markdown
  const isMarkdownContent = (content) => {
    // Simple markdown detection - look for common markdown patterns
    const markdownPatterns = [
      /^#{1,6}\s/m,           // Headers
      /\*\*.*\*\*/,           // Bold
      /\*.*\*/,               // Italic
      /```[\s\S]*?```/,       // Code blocks
      /`.*`/,                 // Inline code
      /^\s*[\*\-\+]\s/m,      // Unordered lists
      /^\s*\d+\.\s/m,         // Ordered lists
      /\[.*\]\(.*\)/,         // Links
      /!\[.*\]\(.*\)/         // Images
    ];
    
    return markdownPatterns.some(pattern => pattern.test(content));
  };

  const renderVideoContent = (contentItem) => {
    const { content } = contentItem;
    const isUrl = content.startsWith('http');
    
    if (isUrl) {
      // External video URL (YouTube, Vimeo, etc.)
      return (
        <div className="video-container mb-5">
          <div className="video-wrapper">
            <iframe
              src={content}
              title={`Video content ${contentItem.content_order}`}
              frameBorder="0"
              allowFullScreen
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            ></iframe>
          </div>
        </div>
      );
    } else {
      // Local video file
      return (
        <div className="video-container mb-5">
          <div className="video-wrapper">
            <video controls className="lesson-video">
              <source src={`${process.env.PUBLIC_URL}/assets/video/${content}`} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      );
    }
  };

  const renderLessonContent = () => {
    // Check if we have content from the backend (array of content items)
    if (!lessonContent || !Array.isArray(lessonContent)) return null;

    // Sort content by content_order
    const sortedContent = [...lessonContent].sort((a, b) => 
      (a.content_order || 0) - (b.content_order || 0)
    );

    return sortedContent.map((contentItem, index) => {
      const key = contentItem.content_id || index;
      
      switch (contentItem.content_type) {
        case 'text':
          const isMarkdown = isMarkdownContent(contentItem.content);
          
          return (
            <div key={key} className="lesson-text-content mb-5">
              <div className="content">
                {isMarkdown ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw]}
                    components={{
                      // Custom styling for markdown elements
                      h1: ({children}) => <h1 className="title is-1">{children}</h1>,
                      h2: ({children}) => <h2 className="title is-2">{children}</h2>,
                      h3: ({children}) => <h3 className="title is-3">{children}</h3>,
                      h4: ({children}) => <h4 className="title is-4">{children}</h4>,
                      h5: ({children}) => <h5 className="title is-5">{children}</h5>,
                      h6: ({children}) => <h6 className="title is-6">{children}</h6>,
                      p: ({children}) => <p className="block">{children}</p>,
                      ul: ({children}) => <ul className="content">{children}</ul>,
                      ol: ({children}) => <ol className="content">{children}</ol>,
                      blockquote: ({children}) => (
                        <blockquote className="notification is-info is-light">
                          {children}
                        </blockquote>
                      ),
                      code: ({inline, children, ...props}) => 
                        inline ? 
                          <code className="tag is-light" {...props}>{children}</code> :
                          <pre className="notification is-dark"><code {...props}>{children}</code></pre>,
                      table: ({children}) => (
                        <div className="table-container">
                          <table className="table is-striped is-hoverable is-fullwidth">
                            {children}
                          </table>
                        </div>
                      ),
                      thead: ({children}) => <thead>{children}</thead>,
                      tbody: ({children}) => <tbody>{children}</tbody>,
                      tr: ({children}) => <tr>{children}</tr>,
                      th: ({children}) => <th>{children}</th>,
                      td: ({children}) => <td>{children}</td>
                    }}
                  >
                    {contentItem.content}
                  </ReactMarkdown>
                ) : (
                  <div dangerouslySetInnerHTML={{ __html: contentItem.content }} />
                )}
              </div>
            </div>
          );
        
        case 'video':
          return (
            <div key={key}>
              {renderVideoContent(contentItem)}
            </div>
          );
        
        case 'image':
          return (
            <div key={key} className="lesson-image-content mb-5">
              <figure className="image">
                <img src={contentItem.content} alt={`Lesson content ${contentItem.content_order}`} />
              </figure>
            </div>
          );
        
        case 'quiz':
          return (
            <div key={key} className="lesson-quiz-content mb-5">
              <div className="notification is-warning is-light">
                <h4 className="title is-5">Knowledge Check</h4>
                <p>{contentItem.content}</p>
                <div className="buttons mt-3">
                  <button className="button is-primary">Take Quiz</button>
                </div>
              </div>
            </div>
          );
        
        default:
          return (
            <div key={key} className="lesson-generic-content mb-5">
              <div className="content">
                <p>{contentItem.content}</p>
              </div>
            </div>
          );
      }
    });
  };

  if (loading) {
    return (
      <div className="lesson-page-bg">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4">Loading lesson...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !currentLesson) {
    return (
      <div className="lesson-page-bg">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4 has-text-danger">{error || 'Lesson not found'}</div>
            <button className="button is-primary mt-4" onClick={() => navigate(`/course/${courseId}`)}>
              Back to Course
            </button>
          </div>
        </div>
      </div>
    );
  }

  const canGoNext = currentLessonIndex < allLessons.length - 1;
  const canGoPrevious = currentLessonIndex > 0;

  return (
    <div className="lesson-page-bg">
      {/* Header */}
      <Header />

      {/* Breadcrumbs */}
      <div className="container mt-4">
        <nav className="breadcrumb" aria-label="breadcrumbs">
          <ul>
            <li><a href="#home" onClick={(e) => { e.preventDefault(); navigate('/home'); }}>Home</a></li>
            <li><a href="#courses" onClick={(e) => { e.preventDefault(); navigate('/courses'); }}>Courses</a></li>
            <li><a href="#course" onClick={(e) => { e.preventDefault(); navigate(`/course/${courseId}`); }}>{courseData?.course?.course_name}</a></li>
            <li><a href="#lesson">{currentLesson.lesson_title}</a></li>
          </ul>
        </nav>
      </div>

      {/* Lesson Content */}
      <div className="container mt-4 mb-6">
        <div className="columns">
          {/* Main Content */}
          <div className="column is-9">
            <div className="box lesson-content-card">
              {/* Lesson Header */}
              <div className="lesson-header mb-5">
                <div className="level">
                  <div className="level-left">
                    <div className="level-item">
                      <div>
                        <h1 className="title is-2">{currentLesson.lesson_title}</h1>
                        <div className="tags">
                          <span className="tag is-light">
                            <span className="icon"><i className="fas fa-clock"></i></span>
                            <span>{currentLesson.duration_hours} hours</span>
                          </span>
                          <span className="tag is-light">
                            <span className="icon"><i className="fas fa-list-ol"></i></span>
                            <span>Lesson {currentLesson.lesson_order} of {allLessons.length}</span>
                          </span>
                          <span className={`tag ${currentLesson.status === 'Complete' ? 'is-success' : currentLesson.status === 'In Progress' ? 'is-warning' : 'is-light'}`}>
                            {currentLesson.status || 'Not Started'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Lesson Description */}
              {currentLesson.description && (
                <div className="lesson-description mb-5">
                  <p className="is-size-5">{currentLesson.description}</p>
                </div>
              )}

              {/* Lesson Content */}
              <div className="lesson-content">
                {navigationLoading ? (
                  <div className="has-text-centered py-6">
                    <div className="is-size-4 mb-3">Loading lesson content...</div>
                    <progress className="progress is-warning" max="100">Loading...</progress>
                  </div>
                ) : (
                  renderLessonContent()
                )}
              </div>

              {/* Lesson Actions */}
              {!navigationLoading && (
                <div className="lesson-actions mt-6">
                  <div className="buttons">
                    {currentLesson.status !== 'Complete' && (
                      <button 
                        className={`button is-success is-medium ${markCompleteLoading ? 'is-loading' : ''}`}
                        onClick={markLessonComplete}
                        disabled={markCompleteLoading}
                      >
                        <span className="icon"><i className="fas fa-check"></i></span>
                        <span>Mark as Complete</span>
                      </button>
                    )}
                    
                    <button className="button is-light is-medium">
                      <span className="icon"><i className="fas fa-bookmark"></i></span>
                      <span>Bookmark</span>
                    </button>
                    
                    <button className="button is-light is-medium">
                      <span className="icon"><i className="fas fa-share"></i></span>
                      <span>Share</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="column is-3">
            <div className="box lesson-sidebar-card">
              <h4 className="title is-5 mb-4">Course Progress</h4>
              
              {/* Progress Bar */}
              <div className="mb-4">
                <progress 
                  className="progress is-primary" 
                  value={courseData?.progress_summary?.completed_lessons || 0} 
                  max={courseData?.progress_summary?.total_lessons || 1}
                >
                  {Math.round(((courseData?.progress_summary?.completed_lessons || 0) / (courseData?.progress_summary?.total_lessons || 1)) * 100)}%
                </progress>
                <p className="is-size-7 has-text-grey">
                  {courseData?.progress_summary?.completed_lessons || 0} of {courseData?.progress_summary?.total_lessons || 0} lessons completed
                </p>
              </div>

              {/* Lesson Navigation */}
              <h5 className="title is-6 mb-3">Lessons</h5>
              <div className="lesson-nav-list">
                {allLessons.map((lesson, index) => (
                  <div 
                    key={lesson.lesson_id}
                    className={`lesson-nav-item ${lesson.lesson_id.toString() === lessonId ? 'is-active' : ''} ${navigationLoading ? 'is-loading-disabled' : ''}`}
                    onClick={() => navigateToSpecificLesson(lesson.lesson_id)}
                  >
                    <div className="level is-mobile">
                      <div className="level-left">
                        <div className="level-item">
                          <span className="lesson-number">{lesson.lesson_order}</span>
                          <span className="lesson-title">{lesson.lesson_title}</span>
                        </div>
                      </div>
                      <div className="level-right">
                        <div className="level-item">
                          {lesson.status === 'Complete' && (
                            <span className="icon has-text-success">
                              <i className="fas fa-check-circle"></i>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="lesson-navigation-footer">
        <div className="container">
          <div className="level">
            <div className="level-left">
              {canGoPrevious && (
                <div className="level-item">
                  <button 
                    className={`button is-primary is-medium ${navigationLoading ? 'is-loading' : ''}`}
                    onClick={() => navigateToLesson('previous')}
                    disabled={navigationLoading}
                  >
                    <span className="icon"><i className="fas fa-chevron-left"></i></span>
                    <span>Previous</span>
                  </button>
                </div>
              )}
            </div>
            
            <div className="level-item">
              <div className="pagination-info">
                <span className="is-size-6">
                  Lesson {currentLessonIndex + 1} of {allLessons.length}
                </span>
              </div>
            </div>
            
            <div className="level-right">
              {canGoNext && (
                <div className="level-item">
                  <button 
                    className={`button is-primary is-medium ${navigationLoading ? 'is-loading' : ''}`}
                    onClick={() => navigateToLesson('next')}
                    disabled={navigationLoading}
                  >
                    <span>Next</span>
                    <span className="icon"><i className="fas fa-chevron-right"></i></span>
                  </button>
                </div>
              )}
              {!canGoNext && currentLesson.status === 'Complete' && !navigationLoading && (
                <div className="level-item">
                  <button 
                    className="button is-success is-medium"
                    onClick={() => navigate(`/course/${courseId}`)}
                  >
                    <span>Course Complete</span>
                    <span className="icon"><i className="fas fa-trophy"></i></span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LessonPage; 