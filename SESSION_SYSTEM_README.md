# Session System Implementation

This project now implements a complete session system with JWT authentication that requires users to log in before accessing the homepage.

## Features

### Backend (Flask + JWT)
- **JWT Token Authentication**: Uses PyJWT for secure token generation and validation
- **Protected Routes**: API endpoints that require valid authentication tokens
- **Token Expiration**: Tokens expire after 24 hours for security
- **CORS Support**: Allows frontend-backend communication

### Frontend (React + Context API)
- **Authentication Context**: Centralized state management for user authentication
- **Protected Routes**: Automatic redirection to login page for unauthenticated users
- **Session Persistence**: Login state persists across browser sessions using localStorage
- **Automatic Token Verification**: Validates stored tokens on app startup
- **Loading States**: User-friendly loading indicators during authentication

## How It Works

### Authentication Flow
1. **Login**: User enters credentials on `/login` page
2. **Token Generation**: Backend validates credentials and returns JWT token
3. **Token Storage**: Frontend stores token in localStorage
4. **Route Protection**: ProtectedRoute component checks authentication before allowing access
5. **API Requests**: All protected API calls include the JWT token in headers
6. **Auto-Login**: On page refresh, stored token is validated with backend

### Session Management
- **Login State**: Managed by React Context API
- **Token Validation**: Automatic verification on app startup
- **Session Expiry**: Tokens expire after 24 hours
- **Logout**: Clears stored token and redirects to login

## Usage

### Demo Credentials
- **Email**: admin@admin.com
- **Password**: admin

### Routes
- `/login` - Login page (accessible without authentication)
- `/home` - Home page (requires authentication)
- `/` - Redirects to `/home` 

### API Endpoints
- `POST /api/login` - User authentication
- `POST /api/verify-token` - Token validation
- `GET /api/hello` - Protected endpoint (requires authentication)
- `GET /api/protected` - Another protected endpoint

## Security Features

1. **JWT Tokens**: Secure, stateless authentication
2. **Token Expiration**: 24-hour token lifetime
3. **Route Protection**: Client-side route guarding
4. **API Protection**: Server-side endpoint protection
5. **Automatic Cleanup**: Invalid tokens are automatically removed

## File Structure

### Backend
- `app.py` - Flask server with JWT authentication
- `requirements.txt` - Python dependencies including PyJWT

### Frontend
- `src/contexts/AuthContext.js` - Authentication context provider
- `src/components/ProtectedRoute.js` - Route protection component
- `src/pages/LoginPage.js` - Login form with authentication
- `src/pages/HomePage.js` - Protected home page with logout
- `src/App.js` - Main app with routing and context provider

## Getting Started

1. **Install Backend Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**:
   ```bash  
   cd frontend
   npm install
   ```

3. **Start Backend Server**:
   ```bash
   cd backend
   python app.py
   ```

4. **Start Frontend Application**:
   ```bash
   cd frontend
   npm start
   ```

5. **Access Application**:
   - Open browser to http://localhost:3000
   - You'll be redirected to login page
   - Use demo credentials to access the protected homepage

## Technical Implementation

### JWT Token Structure
```javascript
{
  "username": "admin@admin.com",
  "exp": 1640995200  // Expiration timestamp
}
```

### Authentication Context Methods
- `login(username, password)` - Authenticate user
- `logout()` - Clear session and redirect
- `getAuthHeader()` - Get authorization header for API calls
- `isAuthenticated` - Current authentication status
- `user` - Current user information

### Protected Route Logic
```javascript
// Redirects to /login if not authenticated
return isAuthenticated ? children : <Navigate to="/login" replace />;
```

The system ensures that users cannot access the homepage or any protected content without proper authentication, providing a secure and user-friendly experience. 