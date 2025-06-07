# Flask Authentication API with ChromaDB

This Flask application provides JWT-based authentication using ChromaDB as a persistent vector database for user management.

## Features

- JWT-based authentication
- User registration and login
- Password hashing with bcrypt
- Persistent storage with ChromaDB
- CORS enabled for frontend integration

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

Run the initialization script to create sample users:

```bash
python init_db.py
```

Or use the API endpoint:

```bash
curl -X POST http://localhost:5000/api/init-db
```

### 3. Run the Application

```bash
python app.py
```

The server will start on `http://localhost:5000`.

## API Endpoints

### Authentication

- **POST** `/api/login` - User login
  ```json
  {
    "email": "admin@admin.com",
    "password": "admin"
  }
  ```

- **POST** `/api/register` - User registration
  ```json
  {
    "username": "newuser",
    "email": "user@example.com",
    "password": "password123",
    "full_name": "New User"
  }
  ```

- **POST** `/api/verify-token` - Verify JWT token (requires Authorization header)

### Protected Routes

- **GET** `/api/hello` - Hello message (requires authentication)
- **GET** `/api/protected` - Protected route example
- **GET** `/api/users` - Get all users (requires authentication)

### Database Management

- **POST** `/api/init-db` - Initialize database with sample data

## Sample Users

After running the initialization script, you can login with:

- **Email**: `admin@admin.com`, **Password**: `admin`
- **Email**: `user1@example.com`, **Password**: `password123`
- **Email**: `user2@example.com`, **Password**: `password456`

## Authentication Headers

For protected routes, include the JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Database Storage

ChromaDB data is persisted in the `./chroma_db` directory. The database will be automatically created when the application starts.

## Environment Variables

- `SECRET_KEY`: JWT secret key (default: 'your-secret-key-change-in-production')

**Note**: Change the secret key in production! 