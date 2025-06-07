from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
from conn import db

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['username']  # Changed from username to email
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/hello')
@token_required
def hello(current_user):
    user = db.get_user_by_email(current_user)
    username = user['username'] if user else current_user
    return jsonify(message=f"Hello {username} from Flask!")

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email') or data.get('username')  # Support both email and username
    password = data.get('password')
    
    if not email or not password:
        return jsonify(success=False, message="Email and password are required"), 400
    
    # Authenticate user against database
    user = db.authenticate_user(email, password)
    
    if user:
        # Generate JWT token
        token = jwt.encode({
            'email': user['email'],
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'token': token,
            'username': user['username'],
            'email': user['email'],
            'full_name': user.get('full_name', user['username'])
        })
    
    return jsonify(success=False, message="Invalid credentials"), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    
    if not all([username, email, password]):
        return jsonify(success=False, message="Username, email, and password are required"), 400
    
    success, message = db.create_user(username, email, password, full_name)
    
    if success:
        return jsonify(success=True, message=message)
    else:
        return jsonify(success=False, message=message), 400

@app.route('/api/verify-token', methods=['POST'])
@token_required
def verify_token(current_user):
    user = db.get_user_by_email(current_user)
    return jsonify({
        'valid': True,
        'email': current_user,
        'username': user['username'] if user else current_user,
        'full_name': user.get('full_name') if user else current_user
    })

@app.route('/api/protected', methods=['GET'])
@token_required
def protected_route(current_user):
    user = db.get_user_by_email(current_user)
    username = user['username'] if user else current_user
    return jsonify({
        'message': f'This is a protected route! Hello {username}',
        'email': current_user,
        'username': username
    })

@app.route('/api/users', methods=['GET'])
@token_required
def get_users(current_user):
    """Get all users (protected route)"""
    users = db.get_all_users()
    # Remove sensitive data before sending
    safe_users = []
    for user in users:
        safe_user = {
            'username': user.get('username'),
            'email': user.get('email'),
            'full_name': user.get('full_name'),
            'created_at': user.get('created_at')
        }
        safe_users.append(safe_user)
    
    return jsonify(users=safe_users)

@app.route('/api/courses', methods=['GET'])
@token_required
def get_courses(current_user):
    """Get all courses (protected route)"""
    try:
        courses = db.get_all_courses()
        # Return courses with lesson count
        courses_with_details = []
        for course in courses:
            lessons = db.get_lessons_by_course_id(course['course_id'])
            course_data = {
                'course_id': course.get('course_id'),
                'course_name': course.get('course_name'),
                'description': course.get('description'),
                'total_hour': course.get('total_hour'),
                'difficulty_level': course.get('difficulty_level'),
                'status': course.get('status'),
                'create_at': course.get('create_at'),
                'lesson_count': len(lessons)
            }
            courses_with_details.append(course_data)
        
        return jsonify(courses=courses_with_details)
    except Exception as e:
        return jsonify(success=False, message=f"Error getting courses: {str(e)}"), 500

@app.route('/api/init-db', methods=['POST'])
def init_database():
    """Initialize database with sample data"""
    try:
        db.initialize_sample_data()
        return jsonify(success=True, message="Database initialized with sample data")
    except Exception as e:
        return jsonify(success=False, message=f"Error initializing database: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)
