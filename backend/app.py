from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
from conn import db
import initialize_data
import os
from agent.create_course.agent_autogen import CreateCourse
from langchain_community.document_loaders import PyPDFLoader
import asyncio
import concurrent.futures
import uuid
import base64

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

# Role-based access control decorator
def admin_required(f):
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
            current_user = data['email']
            
            # Get user and check role
            user = db.get_user_by_email(current_user)
            if not user or user.get('role') != 'admin':
                return jsonify({'message': 'Admin access required!'}), 403
                
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
            'role': user.get('role', 'user'),  # Include role in token
            'is_auth': user.get('is_auth', True),  # Include auth status in token
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'token': token,
            'username': user['username'],
            'email': user['email'],
            'role': user.get('role', 'user'),
            'full_name': user.get('full_name', user['username']),
            'is_auth': user.get('is_auth', True)
        })
    
    return jsonify(success=False, message="Invalid credentials"), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    role = data.get('role', 'user')  # Default to 'user' role
    
    if not all([username, email, password]):
        return jsonify(success=False, message="Username, email, and password are required"), 400
    
    # Only allow 'user' role during registration
    if role != 'user':
        return jsonify(success=False, message="Invalid role specified"), 400
    
    success, message = db.create_user(username, email, password, full_name, role, True)
    
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
        'role': user.get('role', 'user') if user else 'user',
        'full_name': user.get('full_name') if user else current_user,
        'is_auth': user.get('is_auth', True) if user else True
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
        # First, try to reset the database
        if os.path.exists("./chroma_db"):
            import shutil
            shutil.rmtree("./chroma_db")
        
        # Create a new database instance
        global db
        db = DatabaseManager()
        
        # Initialize sample data
        initialize_data.main()
        
        return jsonify({
            'success': True, 
            'message': "Database initialized with sample data"
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f"Error initializing database: {str(e)}"
        }), 500

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

        # If all lessons are complete, update enrollment status
        if (enrollment and
            progress_summary['completed_lessons'] == progress_summary['total_lessons'] and
            progress_summary['total_lessons'] > 0 and
            enrollment['status'] != 'Complete'):
            db.update_enrollment_status(
                user_id,
                course_id,
                "Complete",
                datetime.datetime.now().isoformat()
            )
            # Refresh enrollment object
            enrollment = db.get_enrollment(user_id, course_id)

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
        
        print(f"Mark lesson complete request: lesson_id={lesson_id}, course_id={course_id}, user={current_user}")
        
        if not lesson_id or not course_id:
            return jsonify(success=False, message="Lesson ID and Course ID are required"), 400
        
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        user_id = user['user_id']
        
        # Check if user is enrolled in the course
        enrollment = db.get_enrollment(user_id, course_id)
        if not enrollment:
            print(f"User {user_id} not enrolled in course {course_id}")
            return jsonify(success=False, message="You must be enrolled in this course to mark lessons complete"), 400
        
        # Verify lesson exists and belongs to the course
        lesson = db.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify(success=False, message="Lesson not found"), 404
        
        if lesson['course_id'] != course_id:
            return jsonify(success=False, message="Lesson does not belong to this course"), 400
        
        # Create or update progress
        success, result = db.create_progress(user_id, course_id, lesson_id, "Complete")
        
        print(f"Progress creation result: success={success}, result={result}")
        
        if success:
            # Check if all lessons are completed
            progress_summary = db.get_course_progress_summary(user_id, course_id)
            if (progress_summary['completed_lessons'] == progress_summary['total_lessons'] and 
                progress_summary['total_lessons'] > 0):
                # Update course enrollment status to Complete
                db.update_enrollment_status(
                    user_id, 
                    course_id, 
                    "Complete",
                    datetime.datetime.now().isoformat()
                )
                print(f"Course {course_id} marked as complete for user {user_id}")
            
            return jsonify(success=True, message="Lesson marked as complete")
        else:
            return jsonify(success=False, message=result), 400
            
    except Exception as e:
        print(f"Error in mark_lesson_complete: {str(e)}")
        return jsonify(success=False, message=f"Error marking lesson complete: {str(e)}"), 500

@app.route('/api/create-course/preview', methods=['POST','GET'])
@token_required
def preview_course_with_agent(current_user):
    """Generate course preview using AI agent from document content (no database save)"""
    try:
        data = request.get_json()
        document_content = data.get('DocumentBased64')
        
        # if not document_content:
        #     return jsonify(success=False, message="Document content is required"), 400
        _id = uuid.uuid4()

        with open(f"./temp/{_id}.pdf", "wb") as f:
            f.write(base64.b64decode(document_content))
        
        loader = PyPDFLoader(f"./temp/{_id}.pdf")
        docs = loader.load()
        text = ""
        for doc in docs:
            text += doc.page_content

    
        # Initialize the CreateCourse agent
        course_creator = CreateCourse()

        # Generate course data using the agent
        # Handle async operation properly in Flask context
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            print(f"Found event loop: {loop}, running: {loop.is_running()}")
            if loop.is_running():
                # If loop is already running, we need to run in a new thread
                print("Event loop is running, using ThreadPoolExecutor")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, course_creator.create_course(text))
                    result = future.result()
            else:
                # If no loop is running, use run_until_complete
                print("Event loop exists but not running, using run_until_complete")
                result = loop.run_until_complete(course_creator.create_course(text))
        except RuntimeError as e:
            # If no event loop exists, create a new one
            print(f"No event loop found, creating new one. Error: {e}")
            result = asyncio.run(course_creator.create_course(text))

        final_output = None
        log = []
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ",i.source)
            if i.source == "Expert_Agent":
                final_output = i.content.dict()
                print("Content: ",final_output)
                log.append({
                    'agent': i.source,
                    'content': final_output
                })
            else:
                print("Content: ",i.content)
                log.append({
                    'agent': i.source,
                    'content': i.content
                })
            print("--------------------------------")

        if final_output:
            output = {
                'log': log,
                'output': final_output
            }
            return output
        else:
            return jsonify(success=False, message="No valid output generated from agent"), 500
        
    except Exception as e:
        print(f"Error in preview_course_with_agent: {str(e)}")
        return jsonify(success=False, message=f"Error generating course preview: {str(e)}"), 500

@app.route('/api/create-course/submit', methods=['POST'])
@token_required
def submit_course_to_database(current_user):
    """Submit generated course data to database"""
    try:
        data = request.get_json()
        course_data = data.get('course_data')
        
        if not course_data:
            return jsonify(success=False, message="Course data is required"), 400
        
        # Extract course, lessons, and lesson contents from the submitted data
        course_info = course_data.get('course')
        lessons_info = course_data.get('lessons', [])
        lesson_contents_info = course_data.get('lesson_contents', [])
        
        if not course_info:
            return jsonify(success=False, message="Invalid course data provided"), 400
        
        # Create course in database
        course_success, course_result = db.create_course(
            course_info['course_id'],
            course_info['course_name'],
            course_info['description'],
            course_info['total_hour'],
            course_info['difficulty_level'],
            course_info['status'],
            course_info.get('learning_objectives', []),
            course_info.get('prerequisites', [])
        )
        
        if not course_success:
            return jsonify(success=False, message=f"Failed to create course: {course_result}"), 500
        
        # Create lessons in database
        created_lessons = []
        for lesson in lessons_info:
            lesson_success, lesson_result = db.create_lesson(
                lesson['lesson_id'],
                lesson['course_id'],
                lesson['lesson_title'],
                lesson['duration_hours'],
                lesson['lesson_order'],
                lesson.get('what_you_will_learn', [])
            )
            
            if lesson_success:
                created_lessons.append(lesson)
            else:
                print(f"Warning: Failed to create lesson {lesson['lesson_title']}: {lesson_result}")
        
        # Create lesson contents in database
        created_contents = []
        for content in lesson_contents_info:
            content_success, content_result = db.create_content(
                lesson_id=content['lesson_id'],
                content_order=content['content_order'],
                content_type=content['content_type'],
                content=content['content']
            )
            
            if content_success:
                created_contents.append(content)
            else:
                print(f"Warning: Failed to create content for lesson {content['lesson_id']}: {content_result}")
        
        return jsonify({
            'success': True,
            'message': 'Course saved to database successfully',
            'results': {
                'course_created': True,
                'lessons_created': len(created_lessons),
                'contents_created': len(created_contents),
                'total_lessons': len(lessons_info),
                'total_contents': len(lesson_contents_info),
                'course_id': course_info['course_id']
            }
        })
        
    except Exception as e:
        return jsonify(success=False, message=f"Error saving course to database: {str(e)}"), 500

# Quiz routes
@app.route('/api/quiz/<course_id>', methods=['GET'])
@token_required
def get_quiz(current_user, course_id):
    try:
        # Get quiz for the course
        quiz = db.get_quiz_by_course_id(course_id)
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'No quiz found for this course'
            }), 404
        
        # Check if user has already taken the quiz
        user_id = db.get_user_by_email(current_user)['user_id']
        existing_score = db.get_quiz_score(user_id, course_id, quiz[0]['quiz_id'])
        if existing_score:
            return jsonify({
                'success': False,
                'message': 'You have already taken this quiz'
            }), 400
        
        return jsonify({
            'success': True,
            'quiz': quiz[0]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/quiz/<quiz_id>/questions', methods=['GET'])
@token_required
def get_quiz_questions(current_user, quiz_id):
    try:
        questions = db.get_questions_by_quiz_id(quiz_id)
        return jsonify({
            'success': True,
            'questions': questions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/question/<question_id>/choices', methods=['GET'])
@token_required
def get_question_choices(current_user, question_id):
    try:
        choices = db.get_choices_by_question_id(question_id)
        return jsonify({
            'success': True,
            'choices': choices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/question/<question_id>/answer', methods=['GET'])
@token_required
def get_question_answer(current_user, question_id):
    try:
        answer = db.get_answer_by_question_id(question_id)
        return jsonify({
            'success': True,
            'answer': answer
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/quiz/submit', methods=['POST'])
@token_required
def submit_quiz(current_user):
    try:
        data = request.get_json()
        user_id = db.get_user_by_email(current_user)['user_id']
        
        # Validate required fields
        required_fields = ['course_id', 'quiz_id', 'score', 'total_points', 'answers']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Create quiz score
        success, result = db.create_quiz_score(
            user_id,
            data['course_id'],
            data['quiz_id'],
            data['score'],
            data['total_points'],
            data['answers']
        )
        
        if not success:
            return jsonify({
                'success': False,
                'message': result
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Quiz submitted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/quiz-score/<course_id>', methods=['GET'])
@token_required
def get_quiz_score_for_course(current_user, course_id):
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        user_id = user['user_id']
        quizzes = db.get_quiz_by_course_id(course_id)
        if not quizzes:
            return jsonify(success=False, message="No quiz found for this course"), 404
        quiz_id = quizzes[0]['quiz_id']
        score_record = db.get_quiz_score(user_id, course_id, quiz_id)
        if not score_record:
            return jsonify(success=True, attempted=False, score=None, total_points=None, status="Not Attempted")
        return jsonify(success=True, attempted=True, score=score_record['score'], total_points=score_record['total_points'], status="Completed")
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

# Data retrieval endpoints
@app.route('/api/user/<email>', methods=['GET'])
@token_required
def get_user_by_email_api(current_user, email):
    try:
        user = db.get_user_by_email(email)
        if user:
            # Remove sensitive data
            if 'password' in user:
                del user['password']
            return jsonify({"success": True, "user": user})
        return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/course/<course_id>', methods=['GET'])
@token_required
def get_course_by_id_api(current_user, course_id):
    try:
        course = db.get_course_by_id(course_id)
        if course:
            return jsonify({"success": True, "course": course})
        return jsonify({"success": False, "message": "Course not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/course/<course_id>/lessons', methods=['GET'])
@token_required
def get_lessons_by_course_id_api(current_user, course_id):
    try:
        lessons = db.get_lessons_by_course_id(course_id)
        return jsonify({"success": True, "lessons": lessons})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/lesson/<lesson_id>', methods=['GET'])
@token_required
def get_lesson_by_id_api(current_user, lesson_id):
    try:
        lesson = db.get_lesson_by_id(lesson_id)
        if lesson:
            return jsonify({"success": True, "lesson": lesson})
        return jsonify({"success": False, "message": "Lesson not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/lesson/<lesson_id>/content', methods=['GET'])
@token_required
def get_content_by_lesson_id_api(current_user, lesson_id):
    try:
        content = db.get_content_by_lesson_id(lesson_id)
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/enrollment/<user_id>/<course_id>', methods=['GET'])
@token_required
def get_enrollment_api(current_user, user_id, course_id):
    try:
        enrollment = db.get_enrollment(user_id, course_id)
        if enrollment:
            return jsonify({"success": True, "enrollment": enrollment})
        return jsonify({"success": False, "message": "Enrollment not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/enrollments/user/<user_id>', methods=['GET'])
@token_required
def get_enrollments_by_user_api(current_user, user_id):
    try:
        enrollments = db.get_enrollments_by_user(user_id)
        return jsonify({"success": True, "enrollments": enrollments})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/enrollments/course/<course_id>', methods=['GET'])
@token_required
def get_enrollments_by_course_api(current_user, course_id):
    try:
        enrollments = db.get_enrollments_by_course(course_id)
        return jsonify({"success": True, "enrollments": enrollments})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/progress/<user_id>/<course_id>/<lesson_id>', methods=['GET'])
@token_required
def get_progress_api(current_user, user_id, course_id, lesson_id):
    try:
        progress = db.get_progress(user_id, course_id, lesson_id)
        if progress:
            return jsonify({"success": True, "progress": progress})
        return jsonify({"success": False, "message": "Progress not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/progress/<user_id>/<course_id>', methods=['GET'])
@token_required
def get_progress_by_user_course_api(current_user, user_id, course_id):
    try:
        progress = db.get_progress_by_user_course(user_id, course_id)
        return jsonify({"success": True, "progress": progress})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/course/<course_id>/progress-summary/<user_id>', methods=['GET'])
@token_required
def get_course_progress_summary_api(current_user, course_id, user_id):
    try:
        summary = db.get_course_progress_summary(user_id, course_id)
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/quiz/course/<course_id>', methods=['GET'])
@token_required
def get_quiz_by_course_id_api(current_user, course_id):
    try:
        quiz = db.get_quiz_by_course_id(course_id)
        return jsonify({"success": True, "quiz": quiz})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/quiz/<quiz_id>/questions', methods=['GET'])
@token_required
def get_questions_by_quiz_id_api(current_user, quiz_id):
    try:
        questions = db.get_questions_by_quiz_id(quiz_id)
        return jsonify({"success": True, "questions": questions})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/question/<question_id>/choices', methods=['GET'])
@token_required
def get_choices_by_question_id_api(current_user, question_id):
    try:
        choices = db.get_choices_by_question_id(question_id)
        return jsonify({"success": True, "choices": choices})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/question/<question_id>/answer', methods=['GET'])
@token_required
def get_answer_by_question_id_api(current_user, question_id):
    try:
        answer = db.get_answer_by_question_id(question_id)
        if answer:
            return jsonify({"success": True, "answer": answer})
        return jsonify({"success": False, "message": "Answer not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/quiz-score/<user_id>/<course_id>/<quiz_id>', methods=['GET'])
@token_required
def get_quiz_score_api(current_user, user_id, course_id, quiz_id):
    try:
        score = db.get_quiz_score(user_id, course_id, quiz_id)
        if score:
            return jsonify({"success": True, "score": score})
        return jsonify({"success": False, "message": "Score not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/quiz-scores/<user_id>/<course_id>', methods=['GET'])
@token_required
def get_quiz_scores_by_user_course_api(current_user, user_id, course_id):
    try:
        scores = db.get_quiz_scores_by_user_course(user_id, course_id)
        return jsonify({"success": True, "scores": scores})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# New role-related endpoints
@app.route('/api/users/role/<email>', methods=['PUT'])
@admin_required
def update_user_role(current_user, email):
    """Update a user's role (admin only)"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role or new_role not in ['user', 'admin']:
            return jsonify(success=False, message="Invalid role specified"), 400
        
        user = db.get_user_by_email(email)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        # Update user's role
        user['role'] = new_role
        
        # Update in database
        success, message = db.update_user_role(email, new_role)
        
        if success:
            return jsonify(success=True, message=f"User role updated to {new_role}")
        else:
            return jsonify(success=False, message=message), 400
            
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route('/api/users/roles', methods=['GET'])
@admin_required
def get_users_by_role(current_user):
    """Get users by role (admin only)"""
    try:
        role = request.args.get('role')
        if not role or role not in ['user', 'admin']:
            return jsonify(success=False, message="Invalid role specified"), 400
        
        users = db.get_users_by_role(role)
        # Remove sensitive data
        safe_users = []
        for user in users:
            safe_user = {
                'username': user.get('username'),
                'email': user.get('email'),
                'full_name': user.get('full_name'),
                'role': user.get('role'),
                'created_at': user.get('created_at')
            }
            safe_users.append(safe_user)
        
        return jsonify(users=safe_users)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route('/api/users/me/role', methods=['GET'])
@token_required
def get_my_role(current_user):
    """Get current user's role"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        return jsonify({
            'success': True,
            'role': user.get('role', 'user')
        })
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users_admin(current_user):
    """Get all users (admin only)"""
    try:
        users = db.get_all_users()
        # Remove sensitive data before sending
        safe_users = []
        for user in users:
            safe_user = {
                'user_id': user.get('user_id'),
                'username': user.get('username'),
                'email': user.get('email'),
                'full_name': user.get('full_name'),
                'role': user.get('role'),
                'is_auth': user.get('is_auth', True),
                'created_at': user.get('created_at')
            }
            safe_users.append(safe_user)
        
        return jsonify({
            'success': True,
            'users': safe_users
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/courses', methods=['GET'])
@admin_required
def get_all_courses_admin(current_user):
    """Get all courses (admin only)"""
    try:
        courses = db.get_all_courses()
        return jsonify({
            'success': True,
            'courses': courses
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/courses/<course_id>', methods=['GET'])
@admin_required
def get_course_details_admin(current_user, course_id):
    """Get course details with enrolled users (admin only)"""
    try:
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            return jsonify({
                'success': False,
                'message': 'Course not found'
            }), 404

        # Get enrolled users
        enrollments = db.get_enrollments_by_course_id(course_id)
        enrolled_users = []
        
        for enrollment in enrollments:
            user = db.get_user_by_id(enrollment['user_id'])
            if user:
                # Get user's progress for this course
                progress_summary = db.get_course_progress_summary(user['user_id'], course_id)
                
                # Get user's quiz score for this course
                quiz = db.get_quiz_by_course_id(course_id)
                quiz_score = None
                quiz_status = 'No Quiz'
                quiz_total_points = None
                
                if quiz and len(quiz) > 0:
                    quiz_score_data = db.get_quiz_score_by_user_and_quiz(user['user_id'], quiz[0]['quiz_id'])
                    if quiz_score_data:
                        quiz_score = quiz_score_data.get('score')
                        quiz_total_points = quiz_score_data.get('total_points')
                        quiz_status = 'Completed'
                    else:
                        quiz_status = 'Not Attempted'
                
                enrolled_user = {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'enrollment_status': enrollment['status'],
                    'progress_percentage': progress_summary.get('progress_percentage', 0),
                    'completed_lessons': progress_summary.get('completed_lessons', 0),
                    'total_lessons': progress_summary.get('total_lessons', 0),
                    'quiz_status': quiz_status,
                    'quiz_score': quiz_score,
                    'quiz_total_points': quiz_total_points
                }
                enrolled_users.append(enrolled_user)

        return jsonify({
            'success': True,
            'course': course,
            'enrolled_users': enrolled_users
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/quiz-scores', methods=['GET'])
@admin_required
def get_all_quiz_scores_admin(current_user):
    """Get all quiz scores (admin only)"""
    try:
        # Get all courses
        courses = db.get_all_courses()
        all_scores = []
        
        for course in courses:
            # Get quiz for this course
            quiz = db.get_quiz_by_course_id(course['course_id'])
            if quiz:
                # Get all quiz scores for this quiz
                quiz_scores = db.get_quiz_scores_by_quiz_id(quiz[0]['quiz_id'])
                
                for score in quiz_scores:
                    user = db.get_user_by_id(score['user_id'])
                    if user:
                        score_data = {
                            'quiz_score_id': score['quiz_score_id'],
                            'user_id': user['user_id'],
                            'username': user['username'],
                            'email': user['email'],
                            'course_id': course['course_id'],
                            'course_name': course['course_name'],
                            'score': score['score'],
                            'total_points': score['total_points'],
                            'status': score['status'],
                            'attempted_at': score['attempted_at']
                        }
                        all_scores.append(score_data)
        
        # Sort by attempted_at in descending order (most recent first)
        all_scores.sort(key=lambda x: x['attempted_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'quiz_scores': all_scores
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/user/<user_id>', methods=['GET'])
@admin_required
def get_user_details_admin(current_user, user_id):
    """Get detailed user information (admin only)"""
    try:
        # Get user details
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Get user's enrolled courses
        enrollments = db.get_enrollments_by_user(user_id)
        enrolled_courses = []
        
        for enrollment in enrollments:
            course = db.get_course_by_id(enrollment['course_id'])
            if course:
                # Get progress for this course
                progress_summary = db.get_course_progress_summary(user_id, enrollment['course_id'])
                
                # Get lessons count
                lessons = db.get_lessons_by_course_id(enrollment['course_id'])
                
                course_data = {
                    'course_id': course['course_id'],
                    'course_name': course['course_name'],
                    'description': course['description'],
                    'total_hour': course['total_hour'],
                    'difficulty_level': course['difficulty_level'],
                    'enrollment_status': enrollment['status'],
                    'enroll_date': enrollment['enroll_date'],
                    'progress_percentage': progress_summary.get('progress_percentage', 0),
                    'completed_lessons': progress_summary.get('completed_lessons', 0),
                    'total_lessons': progress_summary.get('total_lessons', 0),
                    'lesson_count': len(lessons)
                }
                enrolled_courses.append(course_data)

        # Get user's quiz results
        quiz_results = []
        courses = db.get_all_courses()
        
        for course in courses:
            quiz = db.get_quiz_by_course_id(course['course_id'])
            if quiz and len(quiz) > 0:
                quiz_score = db.get_quiz_score_by_user_and_quiz(user_id, quiz[0]['quiz_id'])
                if quiz_score:
                    quiz_data = {
                        'course_id': course['course_id'],
                        'course_name': course['course_name'],
                        'quiz_id': quiz[0]['quiz_id'],
                        'score': quiz_score['score'],
                        'total_points': quiz_score['total_points'],
                        'status': quiz_score['status'],
                        'attempted_at': quiz_score['attempted_at']
                    }
                    quiz_results.append(quiz_data)

        # Remove sensitive data from user
        safe_user = {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'created_at': user['created_at']
        }

        return jsonify({
            'success': True,
            'user': safe_user,
            'enrolled_courses': enrolled_courses,
            'quiz_results': quiz_results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/add-user', methods=['POST'])
@admin_required
def add_user_admin(current_user):
    """Add a new user with default password (admin only)"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify(success=False, message="Email is required"), 400
        
        # Create user with default password and is_auth=False
        success, message = db.create_user(
            username=email.split('@')[0],  # Use email prefix as temporary username
            email=email,
            password='haionetime1234',  # Default password
            full_name=email.split('@')[0],  # Use email prefix as temporary full name
            role='user',
            is_auth=False  # User needs to complete first-time setup
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'User added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/first-time-setup', methods=['POST'])
@token_required
def first_time_setup(current_user):
    """Complete first-time user setup"""
    try:
        data = request.get_json()
        username = data.get('username')
        full_name = data.get('full_name')
        new_password = data.get('new_password')
        
        if not all([username, full_name, new_password]):
            return jsonify(success=False, message="All fields are required"), 400
        
        # Get current user
        user = db.get_user_by_email(current_user)
        if not user:
            return jsonify(success=False, message="User not found"), 404
        
        # Check if user is in first-time setup mode
        if user.get('is_auth', True):
            return jsonify(success=False, message="User has already completed setup"), 400
        
        # Update user profile
        success, message = db.update_user_profile(
            user['user_id'],
            username,
            full_name,
            new_password
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
