import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './QuizPage.css';

function QuizPage() {
  const { courseId } = useParams();
  const { user, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [quizCompleted, setQuizCompleted] = useState(false);
  const [score, setScore] = useState(null);
  const [evaluatingAnswers, setEvaluatingAnswers] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    fetchQuiz();
  }, [courseId]);

  const fetchQuiz = async () => {
    try {
      // Fetch quiz for the course
      const quizResponse = await fetch(`${API_BASE_URL}/api/quiz/${courseId}`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (quizResponse.ok) {
        const quizData = await quizResponse.json();
        if (quizData.success && quizData.quiz) {
          setQuiz(quizData.quiz);
          
          // Fetch questions for the quiz
          const questionsResponse = await fetch(`${API_BASE_URL}/api/quiz/${quizData.quiz.quiz_id}/questions`, {
            headers: {
              ...getAuthHeader(),
              'Content-Type': 'application/json'
            }
          });
          
          if (questionsResponse.ok) {
            const questionsData = await questionsResponse.json();
            if (questionsData.success) {
              // For each question, fetch its choices or answer
              const questionsWithDetails = await Promise.all(
                questionsData.questions.map(async (question) => {
                  if (question.question_type === 'choices' || question.question_type === 'Multiple Choice') {
                    const choicesResponse = await fetch(`${API_BASE_URL}/api/question/${question.question_id}/choices`, {
                      headers: {
                        ...getAuthHeader(),
                        'Content-Type': 'application/json'
                      }
                    });
                    
                    if (choicesResponse.ok) {
                      const choicesData = await choicesResponse.json();
                      return { ...question, choices: choicesData.choices || [] };
                    } else {
                      console.error('Failed to fetch choices for question:', question.question_id);
                      return { ...question, choices: [] };
                    }
                  } else {
                    const answerResponse = await fetch(`${API_BASE_URL}/api/question/${question.question_id}/answer`, {
                      headers: {
                        ...getAuthHeader(),
                        'Content-Type': 'application/json'
                      }
                    });
                    if (answerResponse.ok) {
                      const answerData = await answerResponse.json();
                      return { ...question, correct_answer: answerData.answer?.correct_answer };
                    }
                  }
                  return question;
                })
              );
              setQuestions(questionsWithDetails);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error fetching quiz:', error);
      setError('Error loading quiz');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    setEvaluatingAnswers(true);
    
    try {
      const authHeader = getAuthHeader();
      
      // Build evaluation tasks - run all AI evaluations IN PARALLEL (single pass, no duplicate calls)
      const evalTasks = Object.entries(answers).map(([questionId, answer]) => {
        const question = questions.find(q => q.question_id.toString() === questionId.toString());
        if (!question) {
          return Promise.resolve({ questionId, answer, isCorrect: false, type: 'unknown' });
        }
        
        if (question.question_type === 'choices' || question.question_type === 'Multiple Choice') {
          const selectedChoice = question.choices.find(c => c.choice_id === answer);
          return Promise.resolve({
            questionId,
            answer,
            isCorrect: selectedChoice?.is_correct || false,
            type: question.question_type
          });
        }
        
        if ((question.question_type === 'fill' || question.question_type === 'Fill in the Blank' ||
             question.question_type === 'subjective' || question.question_type === 'Subjective') &&
            answer && answer.trim() !== '') {
          return fetch(`${API_BASE_URL}/api/quiz/evaluate-answer`, {
            method: 'POST',
            headers: { ...authHeader, 'Content-Type': 'application/json' },
            body: JSON.stringify({
              question_id: question.question_id,
              question_text: question.question_text,
              correct_answer: question.correct_answer,
              user_answer: answer,
              question_type: question.question_type
            })
          })
            .then(async (res) => {
              if (res.ok) {
                const data = await res.json();
                return { questionId, answer, isCorrect: data.success && data.is_correct, type: question.question_type };
              }
              if (question.question_type === 'fill' || question.question_type === 'Fill in the Blank') {
                return {
                  questionId,
                  answer,
                  isCorrect: answer.toLowerCase() === question.correct_answer?.toLowerCase(),
                  type: question.question_type
                };
              }
              return { questionId, answer, isCorrect: false, type: question.question_type };
            })
            .catch(() => {
              if (question.question_type === 'fill' || question.question_type === 'Fill in the Blank') {
                return {
                  questionId,
                  answer,
                  isCorrect: answer?.toLowerCase() === question.correct_answer?.toLowerCase(),
                  type: question.question_type
                };
              }
              return { questionId, answer, isCorrect: false, type: question.question_type };
            });
        }
        
        return Promise.resolve({ questionId, answer, isCorrect: false, type: question.question_type || 'unknown' });
      });
      
      const results = await Promise.all(evalTasks);
      
      setEvaluatingAnswers(false);
      
      const answersArray = results.map(({ questionId, answer, isCorrect, type }) => ({
        question_id: questionId,
        answer,
        type,
        result: isCorrect
      }));
      
      const totalPoints = questions.reduce((s, q) => s + (q.points || 1), 0);
      const totalScore = results.reduce((s, r) => 
        s + (r.isCorrect ? (questions.find(q => q.question_id.toString() === r.questionId)?.points || 1) : 0), 0);
      
      const submissionData = {
        course_id: courseId,
        quiz_id: quiz.quiz_id,
        score: totalScore,
        total_points: totalPoints,
        answers: answersArray
      };
      
      console.log('Submitting quiz data:', submissionData);
      
      // Submit quiz score
      const response = await fetch(`${API_BASE_URL}/api/quiz/submit`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(submissionData)
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        setError(`Failed to submit quiz: ${response.status} ${errorText}`);
        return;
      }
      
      const data = await response.json();
      
      if (data.success) {
        setScore({
          score: totalScore,
          total_points: totalPoints,
          percentage: (totalScore / totalPoints) * 100
        });
        setAnalysis(data.analysis || null);
        setQuizCompleted(true);
      } else {
        setError(data.message || 'Failed to submit quiz');
      }
    } catch (error) {
      console.error('Error submitting quiz:', error);
      setError('Error submitting quiz. Please try again.');
    } finally {
      setSubmitting(false);
      setEvaluatingAnswers(false);
    }
  };

  const renderQuestion = (question) => {
    switch (question.question_type) {
      case 'choices':
      case 'Multiple Choice':
        if (!question.choices || question.choices.length === 0) {
          return (
            <div className="choices">
              <div className="notification is-warning">
                <p>No choices available for this question. Please check the quiz data.</p>
              </div>
            </div>
          );
        }
        
        return (
          <div className="choices">
            {question.choices.map(choice => (
              <div key={choice.choice_id} className="field">
                <div className="control">
                  <label className="radio">
                    <input
                      type="radio"
                      name={`question_${question.question_id}`}
                      value={choice.choice_id}
                      checked={answers[question.question_id] === choice.choice_id}
                      onChange={() => handleAnswerChange(question.question_id, choice.choice_id)}
                    />
                    {' '}{choice.choice_text}
                  </label>
                </div>
              </div>
            ))}
          </div>
        );
      
      case 'subjective':
      case 'Subjective':
        return (
          <div className="field">
            <div className="control">
              <textarea
                className="textarea"
                placeholder="Type your answer here..."
                value={answers[question.question_id] || ''}
                onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
              />
            </div>
          </div>
        );
      
      case 'fill':
      case 'Fill in the Blank':
        return (
          <div className="field">
            <div className="control">
              <input
                className="input"
                type="text"
                placeholder="Type your answer here..."
                value={answers[question.question_id] || ''}
                onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
              />
            </div>
          </div>
        );
      
      default:
        return (
          <div className="field">
            <div className="control">
              <p className="has-text-danger">Unknown question type: {question.question_type}</p>
              <input
                className="input"
                type="text"
                placeholder="Type your answer here..."
                value={answers[question.question_id] || ''}
                onChange={(e) => handleAnswerChange(question.question_id, e.target.value)}
              />
            </div>
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="quiz-page">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4">Loading quiz...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !quiz) {
    return (
      <div className="quiz-page">
        <Header />
        <div className="container">
          <div className="has-text-centered" style={{ paddingTop: '200px' }}>
            <div className="is-size-4 has-text-danger">{error || 'Quiz not found'}</div>
            <button className="button is-primary mt-4" onClick={() => navigate(`/course/${courseId}`)}>
              Back to Course
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (quizCompleted) {
    return (
      <div className="quiz-page">
        <Header />
        <div className="container">
          <div className="box quiz-complete-card">
            <h2 className="title is-2 has-text-centered mb-6">Quiz Completed!</h2>
            
            <div className="quiz-complete-layout">
              <div className="quiz-complete-left">
                <div className="has-text-centered mb-4">
                  <div className="score-circle">
                    <span className="score-percentage">{Math.round(score.percentage)}%</span>
                    <span className="score-fraction">{score.score}/{score.total_points}</span>
                  </div>
                </div>
                <p className="is-size-5 has-text-centered">
                  {score.percentage >= 70 ? 
                    "Congratulations! You've passed the quiz!" :
                    "You didn't pass the quiz. Review the course material and try again later."}
                </p>
              </div>
              
              <div className="quiz-complete-right">
                {analysis && (analysis.strengths?.length || analysis.weaknesses?.length || analysis.related_lessons?.length) > 0 ? (
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
                    {analysis.related_lessons?.length > 0 && (
                      <div className="quiz-analysis-recommendations">
                        <h4 className="title is-5 mb-3">
                          <span className="icon has-text-info"><i className="fas fa-book-open"></i></span>
                          Recommendation
                        </h4>
                        <div className="quiz-recommendation-cards">
                          {analysis.related_lessons.map((l, i) => (
                            <a
                              key={i}
                              href={`/course/${l.course_id}/lesson/${l.lesson_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="quiz-recommendation-card"
                            >
                              <div className="quiz-recommendation-card-body">
                                <div className="quiz-recommendation-number">{i + 1}</div>
                                <div className="quiz-recommendation-content">
                                  <div className="quiz-recommendation-lesson">{l.lesson_title}</div>
                                  <div className="quiz-recommendation-course">{l.course_name}</div>
                                </div>
                                <span className="icon quiz-recommendation-arrow"><i className="fas fa-chevron-right"></i></span>
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="quiz-analysis-placeholder">
                    <p className="has-text-grey">Analysis will appear here when available.</p>
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
      </div>
    );
  }

  return (
    <div className="quiz-page">
      <Header />
      
      <div className="container">
        <div className="box quiz-card">
          <div className="quiz-header">
            <h2 className="title is-2">{quiz.quiz_title}</h2>
            <p className="subtitle is-5">{quiz.description}</p>
            
            <div className="progress-container">
              <progress 
                className="progress is-primary" 
                value={currentQuestion + 1} 
                max={questions.length}
              ></progress>
              <p className="has-text-centered mt-2">
                Question {currentQuestion + 1} of {questions.length}
              </p>
            </div>
          </div>
          
          <div className="quiz-content">
            {questions[currentQuestion] && (
              <div className="question-card">
                <div className="question-header">
                  <span className="tag is-info">
                    {questions[currentQuestion].question_type.charAt(0).toUpperCase() + 
                     questions[currentQuestion].question_type.slice(1)}
                  </span>
                  <span className="tag is-light">
                    {questions[currentQuestion].points || 1} points
                  </span>
                </div>
                
                <h3 className="title is-4 mt-4">
                  {questions[currentQuestion].question_text}
                </h3>
                
                <div className="question-content mt-4">
                  {renderQuestion(questions[currentQuestion])}
                </div>
              </div>
            )}
          </div>
          
          <div className="quiz-navigation mt-6">
            <div className="buttons is-centered">
              {currentQuestion > 0 && (
                <button 
                  className="button is-light"
                  onClick={() => setCurrentQuestion(prev => prev - 1)}
                  disabled={submitting}
                >
                  Previous Question
                </button>
              )}
              
              {currentQuestion < questions.length - 1 ? (
                <button 
                  className="button is-primary"
                  onClick={() => setCurrentQuestion(prev => prev + 1)}
                  disabled={submitting}
                >
                  Next Question
                </button>
              ) : (
                <button 
                  className={`button is-success ${submitting ? 'is-loading' : ''}`}
                  onClick={handleSubmit}
                  disabled={submitting}
                >
                  {evaluatingAnswers ? 'Evaluating Answers...' : 'Submit Quiz'}
                </button>
              )}
            </div>
            
            {evaluatingAnswers && (
              <div className="evaluation-message">
                <p>AI is evaluating your answers, please wait...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default QuizPage; 