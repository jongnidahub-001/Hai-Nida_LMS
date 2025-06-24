import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from '../components/Header';
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

  useEffect(() => {
    fetchQuiz();
  }, [courseId]);

  const fetchQuiz = async () => {
    try {
      // Fetch quiz for the course
      const quizResponse = await fetch(`http://localhost:5000/api/quiz/${courseId}`, {
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
          const questionsResponse = await fetch(`http://localhost:5000/api/quiz/${quizData.quiz.quiz_id}/questions`, {
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
                  if (question.question_type === 'choices') {
                    const choicesResponse = await fetch(`http://localhost:5000/api/question/${question.question_id}/choices`, {
                      headers: {
                        ...getAuthHeader(),
                        'Content-Type': 'application/json'
                      }
                    });
                    if (choicesResponse.ok) {
                      const choicesData = await choicesResponse.json();
                      return { ...question, choices: choicesData.choices };
                    }
                  } else {
                    const answerResponse = await fetch(`http://localhost:5000/api/question/${question.question_id}/answer`, {
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
    
    try {
      // Calculate score
      let totalScore = 0;
      let totalPoints = 0;
      
      questions.forEach(question => {
        totalPoints += question.points || 1;
        
        if (question.question_type === 'choices') {
          const selectedChoice = question.choices.find(c => c.choice_id === answers[question.question_id]);
          if (selectedChoice?.is_correct) {
            totalScore += question.points || 1;
          }
        } else if (question.question_type === 'fill') {
          // For fill in the blank, do exact match
          if (answers[question.question_id]?.toLowerCase() === question.correct_answer?.toLowerCase()) {
            totalScore += question.points || 1;
          }
        }
        // Subjective questions are not auto-graded
      });
      
      // Submit quiz score
      const response = await fetch('http://localhost:5000/api/quiz/submit', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          course_id: courseId,
          quiz_id: quiz.quiz_id,
          score: totalScore,
          total_points: totalPoints,
          answers: answers
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setScore({
          score: totalScore,
          total_points: totalPoints,
          percentage: (totalScore / totalPoints) * 100
        });
        setQuizCompleted(true);
      } else {
        setError(data.message || 'Failed to submit quiz');
      }
    } catch (error) {
      console.error('Error submitting quiz:', error);
      setError('Error submitting quiz. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderQuestion = (question) => {
    switch (question.question_type) {
      case 'choices':
        return (
          <div className="choices">
            {question.choices?.map(choice => (
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
        return null;
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
            
            <div className="has-text-centered mb-6">
              <div className="score-circle">
                <span className="score-percentage">{Math.round(score.percentage)}%</span>
                <span className="score-fraction">{score.score}/{score.total_points}</span>
              </div>
            </div>
            
            <div className="content has-text-centered">
              <p className="is-size-5 mb-4">
                {score.percentage >= 70 ? 
                  "Congratulations! You've passed the quiz!" :
                  "You didn't pass the quiz. Review the course material and try again later."}
              </p>
              
              <div className="buttons is-centered">
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
                >
                  Previous Question
                </button>
              )}
              
              {currentQuestion < questions.length - 1 ? (
                <button 
                  className="button is-primary"
                  onClick={() => setCurrentQuestion(prev => prev + 1)}
                >
                  Next Question
                </button>
              ) : (
                <button 
                  className={`button is-success ${submitting ? 'is-loading' : ''}`}
                  onClick={handleSubmit}
                  disabled={submitting}
                >
                  Submit Quiz
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default QuizPage; 