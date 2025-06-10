from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
from conn import db
import initialize_data

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
            current_user = data['email']  # Use email to match get_user_by_email calls
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
        initialize_data.main()
        return jsonify(success=True, message="Database initialized with sample data")
    except Exception as e:
        return jsonify(success=False, message=f"Error initializing database: {str(e)}"), 500

@app.route('/api/my-courses', methods=['GET'])
@token_required
def get_my_courses(current_user):
    """Get user's enrolled courses with progress"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        user_id = user['user_id']
        enrollments = db.get_enrollments_by_user(user_id)
        
        courses_with_progress = []
        for enrollment in enrollments:
            course = db.get_course_by_id(enrollment['course_id'])
            if course:
                progress_summary = db.get_course_progress_summary(user_id, enrollment['course_id'])
                
                course_data = {
                    'course_id': course['course_id'],
                    'course_name': course['course_name'],
                    'description': course['description'],
                    'total_hour': course['total_hour'],
                    'difficulty_level': course['difficulty_level'],
                    'status': course['status'],
                    'enrollment_status': enrollment['status'],
                    'enroll_date': enrollment['enroll_date'],
                    'complete_date': enrollment.get('complete_date'),
                    'progress': progress_summary
                }
                courses_with_progress.append(course_data)
        
        return jsonify(courses=courses_with_progress)
    except Exception as e:
        return jsonify(success=False, message=f"Error getting enrolled courses: {str(e)}"), 500

@app.route('/api/enroll', methods=['POST'])
@token_required
def enroll_course(current_user):
    """Enroll user in a course"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify(success=False, message="Course ID is required"), 400
        
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        success, result = db.create_enrollment(user['user_id'], course_id)
        
        if success:
            return jsonify(success=True, message="Successfully enrolled in course")
        else:
            return jsonify(success=False, message=result), 400
            
    except Exception as e:
        return jsonify(success=False, message=f"Error enrolling in course: {str(e)}"), 500

@app.route('/api/course-progress/<course_id>', methods=['GET'])
@token_required
def get_course_progress(current_user, course_id):
    """Get detailed progress for a specific course"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        user_id = user['user_id']
        
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            return jsonify(success=False, message="Course not found"), 404
        
        # Get enrollment status (allow viewing even if not enrolled)
        enrollment = db.get_enrollment(user_id, course_id)
        
        # Get lessons with progress
        lessons = db.get_lessons_by_course_id(course_id)
        lessons_with_progress = []
        
        for lesson in lessons:
            progress = db.get_progress(user_id, course_id, lesson['lesson_id']) if enrollment else None
            lesson_data = {
                'lesson_id': lesson['lesson_id'],
                'lesson_title': lesson['lesson_title'],
                'duration_hours': lesson['duration_hours'],
                'lesson_order': lesson['lesson_order'],
                'description': lesson['description'],
                'what_you_will_learn': lesson.get('what_you_will_learn', []),
                'status': progress['status'] if progress else 'Not Started'
            }
            lessons_with_progress.append(lesson_data)
        
        # Sort by lesson order
        lessons_with_progress.sort(key=lambda x: x['lesson_order'])
        
        # Get progress summary (only if enrolled)
        progress_summary = db.get_course_progress_summary(user_id, course_id) if enrollment else {
            'progress_percentage': 0,
            'completed_lessons': 0,
            'total_lessons': len(lessons)
        }
        
        return jsonify({
            'course': course,
            'enrollment': enrollment,
            'lessons': lessons_with_progress,
            'progress_summary': progress_summary
        })
        
    except Exception as e:
        return jsonify(success=False, message=f"Error getting course progress: {str(e)}"), 500

@app.route('/api/course-content/<course_id>', methods=['GET'])
@token_required
def get_course_content(current_user, course_id):
    """Get detailed course content from ChromaDB"""
    try:
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            return jsonify(success=False, message="Course not found"), 404
        
        # Get actual course content from database
        try:
            course_content = {
                'learning_objectives': course.get('learning_objectives', []),
                'prerequisites': course.get('prerequisites', []),
                'course_outline': f"This comprehensive course covers all aspects of {course['course_name']}, structured to take you from foundational concepts to advanced applications.",
                'estimated_completion_time': course.get('total_hour', 0),
                'difficulty_level': course.get('difficulty_level', 'Beginner'),
                'target_audience': f"Students and professionals interested in {course['course_name']}"
            }
            
            return jsonify({
                'success': True,
                'course_content': course_content
            })
            
        except Exception as e:
            return jsonify(success=False, message=f"Error querying course content: {str(e)}"), 500
        
    except Exception as e:
        return jsonify(success=False, message=f"Error getting course content: {str(e)}"), 500

@app.route('/api/lesson-content/<lesson_id>', methods=['GET'])
@token_required
def get_lesson_content(current_user, lesson_id):
    """Get detailed lesson content from ChromaDB"""
    try:
        # Get lesson details to verify it exists
        lesson = db.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify(success=False, message="Lesson not found"), 404
        
        # Get lesson content from the content collection
        content_items = db.get_content_by_lesson_id(lesson_id)
        
        if content_items:
            # Sort content by content_order
            content_items.sort(key=lambda x: x.get('content_order', 0))
            
            return jsonify({
                'success': True,
                'content': content_items,
                'lesson': lesson
            })
        else:
            # No content found for this lesson
            return jsonify(success=False, message="No content found for this lesson"), 404
        
    except Exception as e:
        return jsonify(success=False, message=f"Error getting lesson content: {str(e)}"), 500

@app.route('/api/lesson-complete', methods=['POST'])
@token_required
def mark_lesson_complete(current_user):
    """Mark a lesson as complete"""
    try:
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        course_id = data.get('course_id')
        
        if not lesson_id or not course_id:
            return jsonify(success=False, message="Lesson ID and Course ID are required"), 400
        
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        user_id = user['user_id']
        
        # Create or update progress
        success, result = db.create_progress(user_id, course_id, lesson_id, "Complete")
        
        if success:
            return jsonify(success=True, message="Lesson marked as complete")
        else:
            return jsonify(success=False, message=result), 400
            
    except Exception as e:
        return jsonify(success=False, message=f"Error marking lesson complete: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)
