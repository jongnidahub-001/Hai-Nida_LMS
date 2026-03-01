import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './QuizPage.css';

function QuizResultPage() {
  const { courseId } = useParams();
  const { getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [courseName, setCourseName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [enrollModalLesson, setEnrollModalLesson] = useState(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollSuccess, setEnrollSuccess] = useState(false);
  const [enrollError, setEnrollError] = useState(null);

  useEffect(() => {
    fetchQuizResult();
  }, [courseId]);

  const goToLesson = (courseId, lessonId) => {
    navigate(`/course/${courseId}/lesson/${lessonId}`);
  };

  const handleRecommendedLessonClick = async (l) => {
    // Same course - user already enrolled (they took the quiz)
    if (l.course_id === courseId) {
      goToLesson(l.course_id, l.lesson_id);
      return;
    }
    // Different course - check enrollment
    try {
      const res = await fetch(`${API_BASE_URL}/api/course-progress/${l.course_id}`, {
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
      });
      if (!res.ok) {
        goToLesson(l.course_id, l.lesson_id);
        return;
      }
      const data = await res.json();
      if (data.enrollment) {
        goToLesson(l.course_id, l.lesson_id);
        return;
      }
      setEnrollError(null);
      setEnrollSuccess(false);
      setEnrollModalLesson(l);
    } catch (e) {
      console.error('Error checking enrollment:', e);
      goToLesson(l.course_id, l.lesson_id);
    }
  };

  const handleEnrollConfirm = async () => {
    if (!enrollModalLesson) return;
    setEnrolling(true);
    setEnrollError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/enroll`, {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_id: enrollModalLesson.course_id })
      });
      const data = await res.json();
      if (data.success) {
        setEnrollSuccess(true);
        setTimeout(() => {
          goToLesson(enrollModalLesson.course_id, enrollModalLesson.lesson_id);
          setEnrollModalLesson(null);
          setEnrollSuccess(false);
        }, 1500);
      } else {
        setEnrollError(data.message || data.detail || 'Unable to enroll');
      }
    } catch (e) {
      console.error('Error enrolling:', e);
      setEnrollError('An error occurred. Please try again.');
    } finally {
      setEnrolling(false);
    }
  };

  const handleEnrollModalClose = () => {
    if (!enrolling) {
      setEnrollModalLesson(null);
      setEnrollSuccess(false);
      setEnrollError(null);
    }
  };

  const handleFallbackRedirect = () => {
    if (enrollModalLesson) {
      goToLesson(enrollModalLesson.course_id, enrollModalLesson.lesson_id);
      setEnrollModalLesson(null);
      setEnrollSuccess(false);
    }
  };

  const fetchQuizResult = async () => {
    try {
      const [resultRes, courseRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/quiz-result/${courseId}`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
        fetch(`${API_BASE_URL}/api/course/${courseId}`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        })
      ]);

      if (!resultRes.ok) {
        setError('Failed to load quiz result');
        return;
      }
      const resultData = await resultRes.json();
      if (!resultData.attempted) {
        setError('You have not taken this quiz yet');
        return;
      }
      setResult(resultData);

      if (courseRes.ok) {
        const courseData = await courseRes.json();
        setCourseName(courseData.course?.course_name || '');
      }
    } catch (e) {
      console.error('Error fetching quiz result:', e);
      setError('Error loading quiz result');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="quiz-page">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4">Loading quiz result...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="quiz-page">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4 has-text-danger">{error || 'Quiz result not found'}</div>
            <button className="button is-primary mt-4" onClick={() => navigate(`/course/${courseId}`)}>
              Back to Course
            </button>
          </div>
        </div>
      </div>
    );
  }

  const score = result.score;
  const totalPoints = result.total_points;
  const percentage = totalPoints > 0 ? (score / totalPoints) * 100 : 0;
  const analysis = result.analysis || {};

  return (
    <div className="quiz-page">
      <Header />
      <div className="container">
        <div className="box quiz-complete-card">
          <h2 className="title is-2 has-text-centered mb-6">Quiz Result</h2>
          {courseName && <p className="has-text-centered has-text-grey mb-4">{courseName}</p>}
          
          {/* Quiz score at top */}
          <div className="quiz-score-top mb-6">
            <div className="has-text-centered mb-4">
              <div className="score-circle">
                <span className="score-percentage">{Math.round(percentage)}%</span>
                <span className="score-fraction">{score}/{totalPoints}</span>
              </div>
            </div>
            <p className="is-size-5 has-text-centered">
              {percentage >= 70 ? 
                "Congratulations! You've passed the quiz!" :
                "You didn't pass the quiz. Review the course material and try again."}
            </p>
          </div>

          <div className="quiz-complete-layout">
            <div className="quiz-complete-right quiz-complete-right-full">
              {analysis && (analysis.strengths?.length || analysis.weaknesses?.length || 
                analysis.intensive_lessons?.length || analysis.related_lessons_for_improvement?.length || 
                analysis.related_lessons?.length || ('intensive_lessons' in analysis)) ? (
                <div className="quiz-analysis">
                  {analysis.strengths?.length > 0 && (
                    <div className="quiz-analysis-card quiz-analysis-strength mb-4">
                      <h4 className="title is-5">
                        <span className="icon has-text-success"><i className="fas fa-check-circle"></i></span>
                        Strength
                      </h4>
                      <ul className="mb-0">
                        {analysis.strengths.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {analysis.weaknesses?.length > 0 && (
                    <div className="quiz-analysis-card quiz-analysis-weakness mb-4">
                      <h4 className="title is-5">
                        <span className="icon has-text-danger"><i className="fas fa-exclamation-circle"></i></span>
                        Weakness
                      </h4>
                      <ul className="mb-0">
                        {analysis.weaknesses.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {'intensive_lessons' in analysis && (
                    <div className="quiz-analysis-recommendations mb-4">
                      <h4 className="title is-5 mb-3">
                        <span className="icon has-text-warning"><i className="fas fa-layer-group"></i></span>
                        Intensive Lessons
                      </h4>
                      <p className="subtitle is-6 has-text-grey mb-2">Same topic, different difficulty level</p>
                      {analysis.intensive_lessons?.length > 0 ? (
                        <div className="quiz-recommendation-cards">
                          {analysis.intensive_lessons.map((l, i) => (
                            <div
                              key={`int-${i}`}
                              role="button"
                              tabIndex={0}
                              className="quiz-recommendation-card"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleRecommendedLessonClick(l)}
                              onKeyDown={(e) => e.key === 'Enter' && handleRecommendedLessonClick(l)}
                            >
                              <div className="quiz-recommendation-card-body">
                                <div className="quiz-recommendation-number">{i + 1}</div>
                                <div className="quiz-recommendation-content">
                                  <div className="quiz-recommendation-lesson">{l.lesson_title}</div>
                                  <div className="quiz-recommendation-course">{l.course_name}</div>
                                </div>
                                <span className="icon quiz-recommendation-arrow"><i className="fas fa-chevron-right"></i></span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="has-text-grey is-size-7">No lessons found with the same topic in other difficulty levels.</p>
                      )}
                    </div>
                  )}
                  {analysis.related_lessons_for_improvement?.length > 0 && (
                    <div className="quiz-analysis-recommendations mb-4">
                      <h4 className="title is-5 mb-3">
                        <span className="icon has-text-info"><i className="fas fa-book-open"></i></span>
                        Related Lessons for Improvement
                      </h4>
                      <p className="subtitle is-6 has-text-grey mb-2">Other lessons to strengthen your knowledge</p>
                      <div className="quiz-recommendation-cards">
                        {analysis.related_lessons_for_improvement.map((l, i) => (
                          <div
                            key={`rel-${i}`}
                            role="button"
                            tabIndex={0}
                            className="quiz-recommendation-card"
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleRecommendedLessonClick(l)}
                            onKeyDown={(e) => e.key === 'Enter' && handleRecommendedLessonClick(l)}
                          >
                            <div className="quiz-recommendation-card-body">
                              <div className="quiz-recommendation-number">{i + 1}</div>
                              <div className="quiz-recommendation-content">
                                <div className="quiz-recommendation-lesson">{l.lesson_title}</div>
                                <div className="quiz-recommendation-course">{l.course_name}</div>
                              </div>
                              <span className="icon quiz-recommendation-arrow"><i className="fas fa-chevron-right"></i></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {!analysis.intensive_lessons?.length && !analysis.related_lessons_for_improvement?.length && analysis.related_lessons?.length > 0 && (
                    <div className="quiz-analysis-recommendations">
                      <h4 className="title is-5 mb-3">
                        <span className="icon has-text-info"><i className="fas fa-book-open"></i></span>
                        Recommendation
                      </h4>
                      <div className="quiz-recommendation-cards">
                        {analysis.related_lessons.map((l, i) => (
                          <div
                            key={i}
                            role="button"
                            tabIndex={0}
                            className="quiz-recommendation-card"
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleRecommendedLessonClick(l)}
                            onKeyDown={(e) => e.key === 'Enter' && handleRecommendedLessonClick(l)}
                          >
                            <div className="quiz-recommendation-card-body">
                              <div className="quiz-recommendation-number">{i + 1}</div>
                              <div className="quiz-recommendation-content">
                                <div className="quiz-recommendation-lesson">{l.lesson_title}</div>
                                <div className="quiz-recommendation-course">{l.course_name}</div>
                              </div>
                              <span className="icon quiz-recommendation-arrow"><i className="fas fa-chevron-right"></i></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="quiz-analysis-placeholder">
                  <p className="has-text-grey">Analysis was not saved for this quiz attempt.</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="buttons is-centered mt-5">
            <button 
              className="button is-primary"
              onClick={() => navigate(`/course/${courseId}`)}
            >
              Back to Course
            </button>
          </div>
        </div>
      </div>

      {/* Enroll confirmation modal */}
      <div className={`modal ${enrollModalLesson ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={handleEnrollModalClose}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header className="modal-card-head" style={{ backgroundColor: 'white', borderBottom: '1px solid #eee' }}>
            <p className="modal-card-title" style={{ fontWeight: 'bold' }}>
              <span className="icon has-text-warning mr-2"><i className="fas fa-info-circle"></i></span>
              Notice
            </p>
            <button className="delete" aria-label="close" onClick={handleEnrollModalClose} disabled={enrolling}></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            {!enrollSuccess ? (
              <>
                <p className="mb-4">You are not enrolled in this course. Do you want to enroll?</p>
                {enrollModalLesson && (
                  <div className="box is-shadowless mb-4" style={{ backgroundColor: '#f9f9f9' }}>
                    <p className="mb-1"><strong>{enrollModalLesson.lesson_title}</strong></p>
                    <p className="is-size-7 has-text-grey">{enrollModalLesson.course_name}</p>
                  </div>
                )}
                {enrollError && (
                  <p className="has-text-danger mb-3">{enrollError}</p>
                )}
              </>
            ) : (
              <>
                <p className="mb-3">
                  <span className="icon has-text-success mr-2"><i className="fas fa-check-circle"></i></span>
                  Enrollment successful! The system is redirecting...
                </p>
                <p className="has-text-grey is-size-7 mb-3">If not redirected, click the button below</p>
                <button
                  className="button is-primary is-fullwidth"
                  onClick={handleFallbackRedirect}
                >
                  <span className="icon"><i className="fas fa-external-link-alt"></i></span>
                  <span>Go to Lesson</span>
                </button>
              </>
            )}
          </section>
          {!enrollSuccess && (
            <footer className="modal-card-foot" style={{ backgroundColor: 'white', borderTop: '1px solid #eee', gap: '12px' }}>
              <button
                className={`button is-primary ${enrolling ? 'is-loading' : ''}`}
                onClick={handleEnrollConfirm}
                disabled={enrolling}
              >
                Enroll
              </button>
              <button className="button is-light" onClick={handleEnrollModalClose} disabled={enrolling}>
                Cancel
              </button>
            </footer>
          )}
        </div>
      </div>
    </div>
  );
}

export default QuizResultPage;
