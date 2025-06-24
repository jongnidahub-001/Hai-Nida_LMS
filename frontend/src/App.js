import React from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import FirstTimeLoginPage from './pages/FirstTimeLoginPage';
import HomePage from './pages/HomePage';
import AllCoursesPage from './pages/AllCoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import LessonPage from './pages/LessonPage';
import QuizPage from './pages/QuizPage';
import AdminHomePage from './pages/AdminHomePage';
import AdminAllCourse from './pages/AdminAllCourse';
import AdminCourseDetail from './pages/AdminCourseDetail';
import AdminAllQuiz from './pages/AdminAllQuiz';
import AdminUserDetail from './pages/AdminUserDetail';

function App() {
  return (
    <AuthProvider>
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

          {/* User Routes */}
          <Route 
            path="/home" 
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/courses" 
            element={
              <ProtectedRoute>
                <AllCoursesPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId" 
            element={
              <ProtectedRoute>
                <CourseDetailPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId/lesson/:lessonId" 
            element={
              <ProtectedRoute>
                <LessonPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/course/:courseId/quiz" 
            element={
              <ProtectedRoute>
                <QuizPage />
              </ProtectedRoute>
            } 
          />

          {/* Default Routes */}
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
