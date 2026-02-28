import React from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AlertProvider } from './contexts/AlertContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import FirstTimeLoginPage from './pages/FirstTimeLoginPage';
import HomePage from './pages/HomePage';
import AllCoursesPage from './pages/AllCoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import LessonPage from './pages/LessonPage';
import QuizPage from './pages/QuizPage';
import QuizResultPage from './pages/QuizResultPage';
import AdminHomePage from './pages/AdminHomePage';
import AdminAllCourse from './pages/AdminAllCourse';
import AdminCourseDetail from './pages/AdminCourseDetail';
import AdminAllQuiz from './pages/AdminAllQuiz';
import AdminUserDetail from './pages/AdminUserDetail';
import AdminGeminiSettings from './pages/AdminGeminiSettings';

/** Redirects "/" and "*" based on auth state and user role */
function DefaultRedirect() {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="is-flex is-justify-content-center is-align-items-center" style={{ minHeight: '100vh' }}>
        <div className="has-text-centered">
          <div className="is-size-4">Loading...</div>
          <progress className="progress is-primary" max="100" style={{ width: '200px' }}></progress>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect based on role and first-time setup status
  if (user?.role === 'admin') {
    return <Navigate to="/admin" replace />;
  }
  // First-time users must complete setup before accessing dashboard
  if (user && !user.is_auth) {
    return <Navigate to="/first-time-setup" replace />;
  }
  return <Navigate to="/home" replace />;
}

function App() {
  return (
    <AuthProvider>
      <AlertProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route 
            path="/first-time-setup" 
            element={
              <ProtectedRoute>
                <FirstTimeLoginPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Admin Routes */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute>
                <AdminHomePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/courses" 
            element={
              <ProtectedRoute>
                <AdminAllCourse />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/course/:courseId" 
            element={
              <ProtectedRoute>
                <AdminCourseDetail />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/quizzes" 
            element={
              <ProtectedRoute>
                <AdminAllQuiz />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/user/:userId" 
            element={
              <ProtectedRoute>
                <AdminUserDetail />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/settings" 
            element={
              <ProtectedRoute>
                <AdminGeminiSettings />
              </ProtectedRoute>
            } 
          />

          {/* User Routes - require full auth (first-time setup completed) */}
          <Route 
            path="/home" 
            element={
              <ProtectedRoute requireFullAuth>
                <HomePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/courses"
            element={
              <ProtectedRoute requireFullAuth>
                <AllCoursesPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId" 
            element={
              <ProtectedRoute requireFullAuth>
                <CourseDetailPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId/lesson/:lessonId" 
            element={
              <ProtectedRoute requireFullAuth>
                <LessonPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId/quiz" 
            element={
              <ProtectedRoute requireFullAuth>
                <QuizPage />
              </ProtectedRoute>
            }
          />
          <Route 
            path="/course/:courseId/quiz-result" 
            element={
              <ProtectedRoute requireFullAuth>
                <QuizResultPage />
              </ProtectedRoute>
            }
          />

          {/* Default Routes - redirect based on role (admin -> /admin, student -> /home) */}
          <Route path="/" element={<DefaultRedirect />} />
          <Route path="*" element={<DefaultRedirect />} />
        </Routes>
      </Router>
      </AlertProvider>
    </AuthProvider>
  );
}

export default App;
