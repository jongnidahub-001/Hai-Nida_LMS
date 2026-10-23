import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './AdminHomePage.css';

function AdminAllQuiz() {
  const { user, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [quizScores, setQuizScores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    // Redirect if not admin
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }

    fetchQuizScores();
  }, [user, navigate]);

  const fetchQuizScores = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/quiz-scores`, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setQuizScores(data.quiz_scores || []);
      } else {
        console.error('Failed to fetch quiz scores');
      }
    } catch (error) {
      console.error('Error fetching quiz scores:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredScores = quizScores.filter(score => 
    score.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    score.course_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // backend ส่งคะแนนทั้งหมดมาครั้งเดียว จึงแบ่งหน้าจากผลที่ค้นหาแล้ว
  const totalPages = Math.max(1, Math.ceil(filteredScores.length / itemsPerPage));
  const pagedScores = filteredScores.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  return (
    <div className="admin-home-bg">
      <Header />
      
      <div className="container mt-4">
        <div className="box admin-home-card">
          <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
            <div className="is-size-4 has-text-weight-bold">All Quiz Scores</div>
            <div className="field">
              <div className="control has-icons-left">
                <input
                  className="input is-small"
                  type="text"
                  placeholder="Search by username or course..."
                  value={searchTerm}
                  onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                />
                <span className="icon is-small is-left">
                  <i className="fas fa-search"></i>
                </span>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="has-text-centered">
              <div className="is-size-6">Loading quiz scores...</div>
            </div>
          ) : filteredScores.length === 0 ? (
            <div className="has-text-centered">
              <div className="is-size-6 has-text-grey">No quiz scores found</div>
            </div>
          ) : (
            <>
              <div className="table-container">
                <table className="table is-fullwidth is-hoverable">
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Course</th>
                      <th>Score</th>
                      <th>Status</th>
                      <th>Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagedScores.map((score) => (
                      <tr key={score.quiz_score_id}>
                        <td>{score.username}</td>
                        <td>{score.course_name}</td>
                        <td>
                          <span className="has-text-weight-bold">
                            {score.score} / {score.total_points}
                          </span>
                        </td>
                        <td>
                          <span className={`tag ${score.status === 'Completed' ? 'is-success' : 
                            (score.status === 'Not Attempted' ? 'is-warning' : 'is-light')}`}>
                            {score.status}
                          </span>
                        </td>
                        <td>{new Date(score.attempted_at).toLocaleDateString()}</td>
                        <td>
                          <button 
                            className="button is-small is-info"
                            onClick={() => navigate(`/admin/course/${score.course_id}`)}
                          >
                            View Course
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <nav className="pagination is-centered mt-4" role="navigation" aria-label="pagination">
                <button
                  className="pagination-previous"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <button
                  className="pagination-next"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                </button>
                <ul className="pagination-list">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <li key={page}>
                      <button
                        className={`pagination-link ${page === currentPage ? 'is-current' : ''}`}
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </button>
                    </li>
                  ))}
                </ul>
              </nav>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminAllQuiz; 