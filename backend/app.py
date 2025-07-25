from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import jwt
import datetime
from conn import db
import initialize_data
import os
from agent.create_course.agent_autogen import CreateCourse
from agent.create_quiz.agent_autogen import CreateCourse as CreateQuiz
from langchain_community.document_loaders import PyPDFLoader
import asyncio
import concurrent.futures
import uuid
import base64
from typing import Literal
from uuid import uuid4
from uuid import uuid4
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
#from typhoon_ocr import ocr_document

app = FastAPI(title="Learning Management System API", version="1.0.0")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#LLM
#from langchain_huggingface import HuggingFaceEmbeddings
#embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# vector_store = Chroma(
#     collection_name="vector",
#     embedding_function=embeddings,
#     persist_directory="./chroma_db",  # Where to save data locally, remove if not necessary
# )

# Configuration
SECRET_KEY = 'your-secret-key-change-in-production'

#Database
#db = DatabaseManager()

# Security
security = HTTPBearer()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "user"

class EnrollRequest(BaseModel):
    course_id: str

class LessonCompleteRequest(BaseModel):
    lesson_id: str
    course_id: str

class CoursePreviewRequest(BaseModel):
    DocumentBased64: str
    difficulty_level: Literal["Casual","Regular","Intense"]

class CourseSubmitRequest(BaseModel):
    course_data: Dict[str, Any]

class QuizPreviewRequest(BaseModel):
    DocumentBased64: str
    number_of_questions: int = 20
    number_of_choices: int = 10
    number_of_subjective_questions: int = 5
    number_of_fill_in_the_blank_questions: int = 5
    difficulty_level: Literal["Casual","Regular","Intense"]

class QuizCreateSubmitRequest(BaseModel):
    quiz_data: Dict[str, Any]

class QuizSubmitRequest(BaseModel):
    course_id: str
    quiz_id: str
    score: int
    total_points: int
    answers: List[Dict[str, Any]]

class QuizEvaluationRequest(BaseModel):
    question_id: str
    question_text: str
    correct_answer: str
    user_answer: str
    question_type: str

class UpdateRoleRequest(BaseModel):
    role: str

class AddUserRequest(BaseModel):
    email: str

class FirstTimeSetupRequest(BaseModel):
    username: str
    full_name: str
    new_password: str

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    course_id: str
    lesson_id: str
    message: str
    chat_history: List[ChatMessage] = []

# Authentication dependencies
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return current user email"""
    try:
        token = credentials.credentials
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user = data['email']
        return current_user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def verify_admin(current_user: str = Depends(verify_token)):
    """Verify user has admin role"""
    user = db.get_user_by_email(current_user)
    if not user or user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Basic routes
@app.get("/api/hello/test")
async def hello():
    return {"message": "Hello World!"}

@app.get("/api/hello")
async def hello(current_user: str = Depends(verify_token)):
    user = db.get_user_by_email(current_user)
    username = user['username'] if user else current_user
    return {"message": f"Hello {username} from FastAPI!"}

@app.post("/api/login")
async def login(request: LoginRequest):
    email = request.email or request.username
    password = request.password
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    # Authenticate user against database
    user = db.authenticate_user(email, password)
    
    if user:
        # Generate JWT token
        token = jwt.encode({
            'email': user['email'],
            'username': user['username'],
            'role': user.get('role', 'user'),
            'is_auth': user.get('is_auth', True),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')
        
        return {
            'success': True,
            'message': 'Login successful',
            'token': token,
            'username': user['username'],
            'email': user['email'],
            'role': user.get('role', 'user'),
            'full_name': user.get('full_name', user['username']),
            'is_auth': user.get('is_auth', True)
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.post("/api/register")
async def register(request: RegisterRequest):
    if not all([request.username, request.email, request.password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username, email, and password are required"
        )
    
    # Only allow 'user' role during registration
    if request.role != 'user':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified"
        )
    
    success, message = db.create_user(
        request.username, 
        request.email, 
        request.password, 
        request.full_name, 
        request.role, 
        True
    )
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

@app.post("/api/verify-token")
async def verify_token_endpoint(current_user: str = Depends(verify_token)):
    user = db.get_user_by_email(current_user)
    return {
        'valid': True,
        'email': current_user,
        'username': user['username'] if user else current_user,
        'role': user.get('role', 'user') if user else 'user',
        'full_name': user.get('full_name') if user else current_user,
        'is_auth': user.get('is_auth', True) if user else True
    }

@app.get("/api/protected")
async def protected_route(current_user: str = Depends(verify_token)):
    user = db.get_user_by_email(current_user)
    username = user['username'] if user else current_user
    return {
        'message': f'This is a protected route! Hello {username}',
        'email': current_user,
        'username': username
    }

@app.get("/api/users")
async def get_users(current_user: str = Depends(verify_token)):
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
    
    return {"users": safe_users}




@app.get("/api/courses")
async def get_courses(current_user: str = Depends(verify_token)):
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
        
        return {"courses": courses_with_details}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting courses: {str(e)}"
        )

@app.post("/api/init-db")
async def init_database():
    """Initialize database with sample data"""
    try:
        # # First, try to reset the database
        # if os.path.exists("./chroma_db"):
        #     import shutil
        #     shutil.rmtree("./chroma_db")
        
        # Create a new database instance
        global db
        from conn import DatabaseManager
        db = DatabaseManager()
        
        # Initialize sample data
        initialize_data.main()
        
        return {
            'success': True,
            'message': "Database initialized with sample data"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing database: {str(e)}"
        )

@app.get("/api/my-courses")
async def get_my_courses(current_user: str = Depends(verify_token)):
    """Get user's enrolled courses with progress"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
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
        
        return {"courses": courses_with_progress}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting enrolled courses: {str(e)}"
        )

@app.post("/api/enroll")
async def enroll_course(request: EnrollRequest, current_user: str = Depends(verify_token)):
    """Enroll user in a course"""
    try:
        if not request.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course ID is required"
            )
        
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        success, result = db.create_enrollment(user['user_id'], request.course_id)
        
        if success:
            return {"success": True, "message": "Successfully enrolled in course"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enrolling in course: {str(e)}"
        )

@app.get("/api/course-progress/{course_id}")
async def get_course_progress(course_id: str, current_user: str = Depends(verify_token)):
    """Get detailed progress for a specific course"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = user['user_id']
        
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
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

        return {
            'course': course,
            'enrollment': enrollment,
            'lessons': lessons_with_progress,
            'progress_summary': progress_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting course progress: {str(e)}"
        )

@app.get("/api/course-content/{course_id}")
async def get_course_content(course_id: str, current_user: str = Depends(verify_token)):
    """Get detailed course content from ChromaDB"""
    try:
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
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
            
            return {
                'success': True,
                'course_content': course_content
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error querying course content: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting course content: {str(e)}"
        )

@app.get("/api/lesson-content/{lesson_id}")
async def get_lesson_content(lesson_id: str, current_user: str = Depends(verify_token)):
    """Get detailed lesson content from ChromaDB"""
    try:
        # Get lesson details to verify it exists
        lesson = db.get_lesson_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Get lesson content from the content collection
        content_items = db.get_content_by_lesson_id(lesson_id)
        
        if content_items:
            # Sort content by content_order
            content_items.sort(key=lambda x: x.get('content_order', 0))
            
            return {
                'success': True,
                'content': content_items,
                'lesson': lesson
            }
        else:
            # No content found for this lesson
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No content found for this lesson"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting lesson content: {str(e)}"
        )

@app.post("/api/lesson-complete")
async def mark_lesson_complete(request: LessonCompleteRequest, current_user: str = Depends(verify_token)):
    """Mark a lesson as complete"""
    try:
        print(f"Mark lesson complete request: lesson_id={request.lesson_id}, course_id={request.course_id}, user={current_user}")
        
        if not request.lesson_id or not request.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lesson ID and Course ID are required"
            )
        
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = user['user_id']
        
        # Check if user is enrolled in the course
        enrollment = db.get_enrollment(user_id, request.course_id)
        if not enrollment:
            print(f"User {user_id} not enrolled in course {request.course_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must be enrolled in this course to mark lessons complete"
            )
        
        # Verify lesson exists and belongs to the course
        lesson = db.get_lesson_by_id(request.lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        if lesson['course_id'] != request.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lesson does not belong to this course"
            )
        
        # Create or update progress
        success, result = db.create_progress(user_id, request.course_id, request.lesson_id, "Complete")
        
        print(f"Progress creation result: success={success}, result={result}")
        
        if success:
            # Check if all lessons are completed
            progress_summary = db.get_course_progress_summary(user_id, request.course_id)
            if (progress_summary['completed_lessons'] == progress_summary['total_lessons'] and 
                progress_summary['total_lessons'] > 0):
                # Update course enrollment status to Complete
                db.update_enrollment_status(
                    user_id, 
                    request.course_id, 
                    "Complete",
                    datetime.datetime.now().isoformat()
                )
                print(f"Course {request.course_id} marked as complete for user {user_id}")
            
            return {"success": True, "message": "Lesson marked as complete"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in mark_lesson_complete: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking lesson complete: {str(e)}"
        )

@app.post("/api/create-course/preview")
async def preview_course_with_agent(request: CoursePreviewRequest, current_user: str = Depends(verify_token)):
    """Generate course preview using AI agent from document content (no database save)"""
    try:
        document_content = request.DocumentBased64
        
        _id = uuid.uuid4()

        with open(f"./temp/{_id}.pdf", "wb") as f:
            f.write(base64.b64decode(document_content))
        
        loader = PyPDFLoader(f"./temp/{_id}.pdf")
        docs = loader.lazy_load()
        text = ""
        for doc in docs:
            text += doc.page_content

        # Initialize the CreateCourse agent
        course_creator = CreateCourse()

        # Generate course data using the agent - properly handle async
        result = await course_creator.create_course(text, request.difficulty_level)

        final_output = None
        log = []
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ", i.source)
            if i.source == "Expert_Agent":
                final_output = i.content.dict()
                print("Content: ", final_output)
                log.append({
                    'agent': i.source,
                    'content': final_output
                })
            else:
                print("Content: ", i.content)
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
            os.remove(f"./temp/{_id}.pdf")
            return output
        else:
            print("No valid output generated from agent")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No valid output generated from agent"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in preview_course_with_agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating course preview: {str(e)}"
        )

@app.post("/api/create-course/submit")
async def submit_course_to_database(request: CourseSubmitRequest, current_user: str = Depends(verify_token)):
    """Submit generated course data to database"""
    try:
        course_data = request.course_data
        
        if not course_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course data is required"
            )
        
        # Extract course, lessons, and lesson contents from the submitted data
        course_info = course_data.get('course')
        lessons_info = course_data.get('lessons', [])
        lesson_contents_info = course_data.get('lesson_contents', [])
        
        if not course_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course data provided"
            )
        
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create course: {course_result}"
            )
        
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
        
        return {
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
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving course to database: {str(e)}"
        )

@app.post("/api/create-quiz/preview")
async def preview_quiz_with_agent(request: QuizPreviewRequest, current_user: str = Depends(verify_token)):
    """Generate quiz preview using AI agent from document content (no database save)"""
    try:
        document_content = request.DocumentBased64
        
        _id = uuid.uuid4()

        with open(f"./temp/{_id}.pdf", "wb") as f:
            f.write(base64.b64decode(document_content))
        
        loader = PyPDFLoader(f"./temp/{_id}.pdf")
        docs = loader.load()
        text = ""
        for doc in docs:
            text += doc.page_content

        # Initialize the CreateQuiz agent
        quiz_creator = CreateQuiz()

        # Generate quiz data using the agent - properly handle async
        result = await quiz_creator.create_quiz(
            document_content=text,
            number_of_questions=request.number_of_questions,
            number_of_choices=request.number_of_choices,
            number_of_subjective_questions=request.number_of_subjective_questions,
            number_of_fill_in_the_blank_questions=request.number_of_fill_in_the_blank_questions,
            difficulty_level=request.difficulty_level
        )

        final_output = None
        log = []
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ", i.source)
            if i.source == "Expert_Agent":
                final_output = i.content.dict()
                print("Content: ", final_output)
                log.append({
                    'agent': i.source,
                    'content': final_output
                })
            else:
                print("Content: ", i.content)
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
            print(output)
            return output
        else:
            print("No valid output generated from agent")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No valid output generated from agent"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in preview_quiz_with_agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz preview: {str(e)}"
        )

@app.post("/api/create-quiz/submit")
async def submit_quiz_to_database(request: QuizCreateSubmitRequest, current_user: str = Depends(verify_token)):
    """Submit generated quiz data to database (also creates course if it doesn't exist)"""

    try:

        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")
        quiz_data = request.quiz_data
        #print(f"Received quiz_data: {quiz_data}")

        
        if not quiz_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz data is required"
            )
        
        
        # Extract all data from the submitted data
        course_info = quiz_data.get('course')
        lessons_info = quiz_data.get('lessons', [])
        lesson_contents_info = quiz_data.get('lesson_contents', [])
        quiz_info = quiz_data.get('quiz')
        questions_info = quiz_data.get('questions', [])
        choices_info = quiz_data.get('choices', [])
        answers_info = quiz_data.get('answers', [])
        
        if not quiz_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid quiz data provided"
            )
        
        course_created = False
        lessons_created = 0
        contents_created = 0
        
        # Generate new UUIDs for all entities
        new_course_id = str(uuid4())
        new_quiz_id = str(uuid4())
        
        # Create lesson ID mapping (old_lesson_id -> new_lesson_id)
        lesson_id_mapping = {}
        for lesson in lessons_info:
            lesson_id_mapping[lesson['lesson_id']] = str(uuid4())
        
        # Create question ID mapping (old_question_id -> new_question_id)
        question_id_mapping = {}
        for question in questions_info:
            question_id_mapping[question['question_id']] = str(uuid4())
        
        # Create course if provided and doesn't exist
        if course_info:
            existing_course = db.get_course_by_id(new_course_id)
            if not existing_course:
                course_success, course_result = db.create_course(
                    course_id=new_course_id,
                    course_name=course_info['course_name'],
                    description=course_info['description'],
                    total_hour=course_info['total_hour'],
                    difficulty_level=course_info['difficulty_level'],
                    status=course_info['status'],
                    learning_objectives=course_info.get('learning_objectives', []),
                    prerequisites=course_info.get('prerequisites', [])
                )
                
                if course_success:
                    course_created = True
                    print(f"Course created with new ID: {new_course_id}")
                else:
                    print(f"Warning: Failed to create course: {course_result}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create course: {course_result}"
                    )
        
        # Create lessons if provided
        for lesson in lessons_info:
            new_lesson_id = lesson_id_mapping[lesson['lesson_id']]
            lesson_success, lesson_result = db.create_lesson(
                lesson_id=new_lesson_id,
                course_id=new_course_id,
                lesson_title=lesson['lesson_title'],
                duration_hours=lesson['duration_hours'],
                lesson_order=lesson['lesson_order'],
                description=lesson['description'],
                what_you_will_learn=lesson.get('what_you_will_learn', [])
            )
            print("--------------------------------")
            print(lesson_success,lesson_result)
            print("--------------------------------")
            if lesson_success:
                lessons_created += 1
                print(f"Lesson created with new ID: {new_lesson_id} ,Course ID: {new_course_id}")
            else:
                print(f"Warning: Failed to create lesson {lesson['lesson_title']}: {lesson_result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Failed to create lesson {lesson['lesson_title']}: {lesson_result}"
                )
        
        
        # Create lesson contents if provided
        for content in lesson_contents_info:
            old_lesson_id = content['lesson_id']
            new_lesson_id = lesson_id_mapping.get(old_lesson_id)
            
            if new_lesson_id:
                content_success, content_result = db.create_content(
                    lesson_id=new_lesson_id,
                    content_order=content['content_order'],
                    content_type=content['content_type'],
                    content=content['content']
                )
                
                #create vector for each course
                #course_id, content_vector
                db.add_vector(new_course_id, new_lesson_id, content['content'])
                print(f"Vector created for lesson {new_lesson_id}")
    
                        
                if content_success:
                    contents_created += 1
                else:
                    print(f"Warning: Failed to create content for lesson {new_lesson_id}: {content_result}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create content for lesson {new_lesson_id}: {content_result}"
                    )
            else:
                print(f"Warning: Could not find lesson mapping for {old_lesson_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find lesson mapping for {old_lesson_id}"
                )
        # Create quiz in database
        quiz_success, quiz_result = db.create_quiz(
            quiz_id=new_quiz_id,
            course_id=new_course_id,
            quiz_title=quiz_info['quiz_title'],
            status=quiz_info['status'],
            description=quiz_info['description'],
            difficulty_level=quiz_info['difficulty_level']
        )
        
        if not quiz_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create quiz: {quiz_result}"
            )
        
        print(f"Quiz created with new ID: {new_quiz_id}")
        
        # Create questions in database
        created_questions = []
        for question in questions_info:
            old_question_id = question['question_id']
            new_question_id = question_id_mapping[old_question_id]
            
            question_success, question_result = db.create_question(
                question_id=new_question_id,
                quiz_id=new_quiz_id,
                question_text=question['question_text'],
                question_type=question['question_type'],
                points=question['points']
            )
            
            if question_success:
                created_questions.append({
                    **question,
                    'question_id': new_question_id,
                    'quiz_id': new_quiz_id
                })
                print(f"Question created with new ID: {new_question_id}")
            else:
                print(f"Warning: Failed to create question {question['question_text']}: {question_result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Failed to create question {question['question_text']}: {question_result}"
                )
        
        # Create choices in database
        created_choices = []
        for choice in choices_info:
            old_question_id = choice['question_id']
            new_question_id = question_id_mapping.get(old_question_id)
            
            if new_question_id:
                new_choice_id = str(uuid4())
                choice_success, choice_result = db.create_choice(
                    choice_id=new_choice_id,
                    question_id=new_question_id,
                    choice_text=choice['choice_text'],
                    is_correct=choice['is_correct']
                )
                
                if choice_success:
                    created_choices.append({
                        **choice,
                        'choice_id': new_choice_id,
                        'question_id': new_question_id
                    })
                    print(f"Choice created with new ID: {new_choice_id}")
                else:
                    print(f"Warning: Failed to create choice for question {new_question_id}: {choice_result}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create choice for question {new_question_id}: {choice_result}"
                    )
            else:
                print(f"Warning: Could not find question mapping for {old_question_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find question mapping for {old_question_id}"
                )
        
        # Create answers in database
        created_answers = []
        for answer in answers_info:
            old_question_id = answer['question_id']
            new_question_id = question_id_mapping.get(old_question_id)
            
            if new_question_id:
                new_answer_id = str(uuid4())
                answer_success, answer_result = db.create_answer(
                    answer_id=new_answer_id,
                    question_id=new_question_id,
                    correct_answer=answer['answer_text']
                )
                
                if answer_success:
                    created_answers.append({
                        **answer,
                        'answer_id': new_answer_id,
                        'question_id': new_question_id
                    })
                    print(f"Answer created with new ID: {new_answer_id}")
                else:
                    print(f"Warning: Failed to create answer for question {new_question_id}: {answer_result}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create answer for question {new_question_id}: {answer_result}"
                    )
            else:
                print(f"Warning: Could not find question mapping for {old_question_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find question mapping for {old_question_id}"
                )
        

        

        return {
            'success': True,
            'message': 'Quiz and course data saved to database successfully',
            'results': {
                'course_created': course_created,
                'lessons_created': lessons_created,
                'contents_created': contents_created,
                'quiz_created': True,
                'questions_created': len(created_questions),
                'choices_created': len(created_choices),
                'answers_created': len(created_answers),
                'total_lessons': len(lessons_info),
                'total_contents': len(lesson_contents_info),
                'total_questions': len(questions_info),
                'total_choices': len(choices_info),
                'total_answers': len(answers_info),
                'quiz_id': new_quiz_id,
                'course_id': new_course_id,
                'new_ids': {
                    'course_id': new_course_id,
                    'quiz_id': new_quiz_id,
                    'lesson_id_mapping': lesson_id_mapping,
                    'question_id_mapping': question_id_mapping
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving quiz to database: {str(e)}"
        )

# Quiz routes
@app.get("/api/quiz/{course_id}")
async def get_quiz(course_id: str, current_user: str = Depends(verify_token)):
    try:
        # Get quiz for the course
        quiz = db.get_quiz_by_course_id(course_id)
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='No quiz found for this course'
            )
        
        # Check if user has already taken the quiz
        user_id = db.get_user_by_email(current_user)['user_id']
        existing_score = db.get_quiz_score(user_id, course_id, quiz[0]['quiz_id'])
        if existing_score:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='You have already taken this quiz'
            )
        
        return {
            'success': True,
            'quiz': quiz[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/quiz/{quiz_id}/questions")
async def get_quiz_questions(quiz_id: str, current_user: str = Depends(verify_token)):
    try:
        questions = db.get_questions_by_quiz_id(quiz_id)
        return {
            'success': True,
            'questions': questions
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/question/{question_id}/choices")
async def get_question_choices(question_id: str, current_user: str = Depends(verify_token)):
    try:
        choices = db.get_choices_by_question_id(question_id)
        return {
            'success': True,
            'choices': choices
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/question/{question_id}/answer")
async def get_question_answer(question_id: str, current_user: str = Depends(verify_token)):
    try:
        answer = db.get_answer_by_question_id(question_id)
        return {
            'success': True,
            'answer': answer
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/quiz/submit")
async def submit_quiz(request: QuizSubmitRequest, current_user: str = Depends(verify_token)):
    try:
        print(f"Received quiz submission request: {request}")
        print(f"Current user: {current_user}")
        
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = user['user_id']
        print(f"User ID: {user_id}")
        
        # Validate required fields
        print(f"Validating fields - course_id: {request.course_id}, quiz_id: {request.quiz_id}, score: {request.score}, total_points: {request.total_points}, answers: {request.answers}")
        
        if not all([request.course_id, request.quiz_id, request.score is not None, 
                   request.total_points is not None, request.answers]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Missing required fields'
            )
        
        print(f"Creating quiz score with: user_id={user_id}, course_id={request.course_id}, quiz_id={request.quiz_id}, score={request.score}, total_points={request.total_points}")
        # Create quiz score
        success, result = db.create_quiz_score(
            user_id,
            request.course_id,
            request.quiz_id,
            request.score,
            request.total_points,
            request.answers
        )
        
        print(f"Quiz score creation result: success={success}, result={result}")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
        
        return {
            'success': True,
            'message': 'Quiz submitted successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in submit_quiz: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/quiz-score/{course_id}")
async def get_quiz_score_for_course(course_id: str, current_user: str = Depends(verify_token)):
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = user['user_id']
        quizzes = db.get_quiz_by_course_id(course_id)
        if not quizzes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quiz found for this course"
            )
        
        quiz_id = quizzes[0]['quiz_id']
        score_record = db.get_quiz_score(user_id, course_id, quiz_id)
        
        if not score_record:
            return {
                "success": True,
                "attempted": False,
                "score": None,
                "total_points": None,
                "status": "Not Attempted"
            }
        
        return {
            "success": True,
            "attempted": True,
            "score": score_record['score'],
            "total_points": score_record['total_points'],
            "status": "Completed"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Data retrieval endpoints
@app.get("/api/user/{email}")
async def get_user_by_email_api(email: str, current_user: str = Depends(verify_token)):
    try:
        user = db.get_user_by_email(email)
        if user:
            # Remove sensitive data
            if 'password' in user:
                del user['password']
            return {"success": True, "user": user}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/course/{course_id}")
async def get_course_by_id_api(course_id: str, current_user: str = Depends(verify_token)):
    try:
        course = db.get_course_by_id(course_id)
        if course:
            return {"success": True, "course": course}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/course/{course_id}/lessons")
async def get_lessons_by_course_id_api(course_id: str, current_user: str = Depends(verify_token)):
    try:
        lessons = db.get_lessons_by_course_id(course_id)
        return {"success": True, "lessons": lessons}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/lesson/{lesson_id}")
async def get_lesson_by_id_api(lesson_id: str, current_user: str = Depends(verify_token)):
    try:
        lesson = db.get_lesson_by_id(lesson_id)
        if lesson:
            return {"success": True, "lesson": lesson}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Admin routes
@app.get("/api/admin/users")
async def get_all_users_admin(current_user: str = Depends(verify_admin)):
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
        
        return {
            'success': True,
            'users': safe_users
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/courses")
async def get_all_courses_admin(current_user: str = Depends(verify_admin)):
    """Get all courses (admin only)"""
    try:
        courses = db.get_all_courses()
        courses_with_details = []
        for course in courses:
            lessons = db.get_lessons_by_course_id(course['course_id'])
            enrollments = db.get_enrollments_by_course(course['course_id'])
            course_data = {
                'course_id': course.get('course_id'),
                'course_name': course.get('course_name'),
                'description': course.get('description'),
                'total_hour': course.get('total_hour'),
                'difficulty_level': course.get('difficulty_level'),
                'status': course.get('status'),
                'create_at': course.get('create_at'),
                'lesson_count': len(lessons),
                'enrollment_count': len(enrollments)
            }
            print(course_data)
            courses_with_details.append(course_data)

        return {
            'success': True,
            'courses': courses_with_details
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/courses/{course_id}")
async def get_course_details_admin(course_id: str, current_user: str = Depends(verify_admin)):
    """Get course details with enrolled users (admin only)"""
    try:
        # Get course details
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Course not found'
            )

        # Get enrolled users
        enrollments = db.get_enrollments_by_course_id(course_id)

        #print(enrollments)

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

        return {
            'success': True,
            'course': course,
            'enrolled_users': enrolled_users
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/quiz-scores")
async def get_all_quiz_scores_admin(current_user: str = Depends(verify_admin)):
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
        
        return {
            'success': True,
            'quiz_scores': all_scores
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/courses/{course_id}/lessons")
async def get_course_lessons_admin(course_id: str, current_user: str = Depends(verify_admin)):
    """Get course lessons and lesson contents (admin only)"""
    try:
        # Get course to verify it exists
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Course not found'
            )
        
        # Get lessons for this course
        lessons = db.get_lessons_by_course_id(course_id)
        
        # Get lesson contents for all lessons
        lesson_contents = []
        for lesson in lessons:
            contents = db.get_content_by_lesson_id(lesson['lesson_id'])
            lesson_contents.extend(contents)

        return {
            'success': True,
            'lessons': lessons,
            'lesson_contents': lesson_contents
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/courses/{course_id}/quiz")
async def get_course_quiz_admin(course_id: str, current_user: str = Depends(verify_admin)):
    """Get course quiz with questions, choices, and answers (admin only)"""
    try:
        # Get course to verify it exists
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Course not found'
            )
        

        # Get quiz for this course
        quiz_data = db.get_quiz_by_course_id(course_id)
        if not quiz_data or len(quiz_data) == 0:
            return {
                'success': True,
                'quiz': None,
                'questions': [],
                'choices': [],
                'answers': []
            }

        quiz = quiz_data[0]
        quiz_id = quiz['quiz_id']

        # Get questions for this quiz
        questions = db.get_questions_by_quiz_id(quiz_id)
        
        # Get choices and answers for all questions
        choices = []
        answers = []
        
        for question in questions:
            question_id = question['question_id']
            
            # Get choices for this question
            question_choices = db.get_choices_by_question_id(question_id)
            choices.extend(question_choices)
            
            # Get answer for this question
            question_answer = db.get_answer_by_question_id(question_id)
            if question_answer:
                answers.append(question_answer)

        return {
            'success': True,
            'quiz': quiz,
            'questions': questions,
            'choices': choices,
            'answers': answers
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/admin/user/{user_id}")
async def get_user_details_admin(user_id: str, current_user: str = Depends(verify_admin)):
    """Get detailed user information (admin only)"""
    try:
        # Get user details
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )


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
        #print(courses)
        #print("Line 1721")
        for course in courses:
            quiz = db.get_quiz_by_course_id(course['course_id'])
            if quiz and len(quiz) > 0:
                quiz_score = db.get_quiz_score_by_user_and_quiz(user_id, quiz[0]['quiz_id'])

                #print(quiz_score)
                if quiz_score:
                    quiz_data = {
                        'course_id': course['course_id'],
                        'course_name': course['course_name'],
                        'quiz_id': quiz[0]['quiz_id'],
                        'score': quiz_score['score'],
                        'total_points': quiz_score['total_points'],
                        'status': 'Completed',
                        'attempted_at': quiz_score['taken_at'],
                        'answers': quiz_score.get('answers', [])
                    }
                    #print(quiz_data['answers'])
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

        print({
            'success': True,
            'user': safe_user,
            'enrolled_courses': enrolled_courses,
            'quiz_results': quiz_results
        })
        return {
            'success': True,
            'user': safe_user,
            'enrolled_courses': enrolled_courses,
            'quiz_results': quiz_results
        }
    except HTTPException:
        raise
    except Exception as e:
        print("Error in get_user_details_admin: ", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/admin/add-user")
async def add_user_admin(request: AddUserRequest, current_user: str = Depends(verify_admin)):
    """Add a new user with default password (admin only)"""
    try:
        if not request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        # Create user with default password and is_auth=False
        success, message = db.create_user(
            username=request.email.split('@')[0],  # Use email prefix as temporary username
            email=request.email,
            password='haionetime1234',  # Default password
            full_name=request.email.split('@')[0],  # Use email prefix as temporary full name
            role='user',
            is_auth=False  # User needs to complete first-time setup
        )
        
        if success:
            return {
                'success': True,
                'message': 'User added successfully'
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/first-time-setup")
async def first_time_setup(request: FirstTimeSetupRequest, current_user: str = Depends(verify_token)):
    """Complete first-time user setup"""
    try:
        if not all([request.username, request.full_name, request.new_password]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required"
            )
        
        # Get current user
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is in first-time setup mode
        if user.get('is_auth', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already completed setup"
            )
        
        # Update user profile
        success, message = db.update_user_profile(
            user['user_id'],
            request.username,
            request.full_name,
            request.new_password
        )
        
        if success:
            return {
                'success': True,
                'message': 'Profile updated successfully'
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Role management endpoints
@app.put("/api/users/role/{email}")
async def update_user_role(email: str, request: UpdateRoleRequest, current_user: str = Depends(verify_admin)):
    """Update a user's role (admin only)"""
    try:
        if not request.role or request.role not in ['user', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role specified"
            )
        
        user = db.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user's role
        success, message = db.update_user_role(email, request.role)
        
        if success:
            return {
                "success": True,
                "message": f"User role updated to {request.role}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/users/me/role")
async def get_my_role(current_user: str = Depends(verify_token)):
    """Get current user's role"""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            'success': True,
            'role': user.get('role', 'user')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/api/admin/courses/{course_id}")
async def delete_course_admin(course_id: str, current_user: str = Depends(verify_admin)):
    """Delete a course and all related data (admin only)"""
    try:
        # Verify course exists
        course = db.get_course_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start deletion process - order matters due to foreign key constraints
        
        # 1. Get quiz for this course
        quiz_data = db.get_quiz_by_course_id(course_id)
        quiz_deleted = False
        questions_deleted = 0
        choices_deleted = 0
        answers_deleted = 0
        quiz_scores_deleted = 0
        
        if quiz_data and len(quiz_data) > 0:
            quiz = quiz_data[0]
            quiz_id = quiz['quiz_id']
            
            # Delete quiz scores first
            try:
                quiz_scores = db.get_quiz_scores_by_quiz_id(quiz_id)
                for score in quiz_scores:
                    success, _ = db.delete_quiz_score(score['quiz_score_id'])
                    if success:
                        quiz_scores_deleted += 1
            except Exception as e:
                print(f"Warning: Error deleting quiz scores: {str(e)}")
            
            # Get questions for this quiz
            questions = db.get_questions_by_quiz_id(quiz_id)
            
            for question in questions:
                question_id = question['question_id']
                
                # Delete choices for this question
                try:
                    choices = db.get_choices_by_question_id(question_id)
                    for choice in choices:
                        success, _ = db.delete_choice(choice['choice_id'])
                        if success:
                            choices_deleted += 1
                except Exception as e:
                    print(f"Warning: Error deleting choices for question {question_id}: {str(e)}")
                
                # Delete answers for this question
                try:
                    answer = db.get_answer_by_question_id(question_id)
                    if answer:
                        success, _ = db.delete_answer(answer['answer_id'])
                        if success:
                            answers_deleted += 1
                except Exception as e:
                    print(f"Warning: Error deleting answer for question {question_id}: {str(e)}")
                
                # Delete the question
                try:
                    success, _ = db.delete_question(question_id)
                    if success:
                        questions_deleted += 1
                except Exception as e:
                    print(f"Warning: Error deleting question {question_id}: {str(e)}")
            
            # Delete the quiz
            try:
                success, _ = db.delete_quiz(quiz_id)
                if success:
                    quiz_deleted = True
            except Exception as e:
                print(f"Warning: Error deleting quiz {quiz_id}: {str(e)}")
        
        # 2. Delete lesson contents and lessons
        lessons = db.get_lessons_by_course_id(course_id)
        lessons_deleted = 0
        contents_deleted = 0
        
        for lesson in lessons:
            lesson_id = lesson['lesson_id']
            
            # Delete lesson contents
            try:
                contents = db.get_content_by_lesson_id(lesson_id)
                for content in contents:
                    success, _ = db.delete_content(content['content_id'])
                    if success:
                        contents_deleted += 1
            except Exception as e:
                print(f"Warning: Error deleting contents for lesson {lesson_id}: {str(e)}")
            
            # Delete the lesson
            try:
                success, _ = db.delete_lesson(lesson_id)
                if success:
                    lessons_deleted += 1
            except Exception as e:
                print(f"Warning: Error deleting lesson {lesson_id}: {str(e)}")
        
        # 3. Delete user progress for this course
        progress_deleted = 0
        try:
            # Get all progress records for this course
            enrollments = db.get_enrollments_by_course_id(course_id)
            for enrollment in enrollments:
                user_id = enrollment['user_id']
                progress_records = db.get_progress_by_user_and_course(user_id, course_id)
                for progress in progress_records:
                    success, _ = db.delete_progress(progress['progress_id'])
                    if success:
                        progress_deleted += 1
        except Exception as e:
            print(f"Warning: Error deleting progress records: {str(e)}")
        
        # 4. Delete enrollments for this course
        enrollments_deleted = 0
        try:
            enrollments = db.get_enrollments_by_course_id(course_id)
            for enrollment in enrollments:
                success, _ = db.delete_enrollment(enrollment['enrollment_id'])
                if success:
                    enrollments_deleted += 1
        except Exception as e:
            print(f"Warning: Error deleting enrollments: {str(e)}")
        
        # 5. Finally, delete the course
        course_deleted = False
        try:
            success, message = db.delete_course(course_id)
            if success:
                course_deleted = True
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete course: {message}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting course: {str(e)}"
            )
        
        # 6. Delete vector for this course

        db.delete_vector(course_id, course_id)
        print(f"Vector deleted for course {course_id}")
        
        return {
            'success': True,
            'message': f'Course "{course["course_name"]}" and all related data deleted successfully',
            'deletion_summary': {
                'course_deleted': course_deleted,
                'lessons_deleted': lessons_deleted,
                'contents_deleted': contents_deleted,
                'quiz_deleted': quiz_deleted,
                'questions_deleted': questions_deleted,
                'choices_deleted': choices_deleted,
                'answers_deleted': answers_deleted,
                'quiz_scores_deleted': quiz_scores_deleted,
                'enrollments_deleted': enrollments_deleted,
                'progress_deleted': progress_deleted
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting course: {str(e)}"
        )
    

@app.post("/api/chat-completion")
async def chat_completion(request: ChatRequest, current_user: str = Depends(verify_token)):
    """Chat with AI about course content"""
    try:
        # Validate inputs
        if not request.course_id or not request.message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course ID and message are required"
            )
        
        # Verify course exists
        course = db.get_course_by_id(request.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Get user and verify they have access (enrolled or admin)
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is enrolled in the course or is an admin
        if user.get('role') != 'admin':
            enrollment = db.get_enrollment(user['user_id'], request.course_id)
            if not enrollment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be enrolled in this course to chat about it"
                )
        
        # Get course content from vector database
        try:
            print(request.lesson_id)
            documents = db.get_content_by_lesson_id(request.lesson_id)
            # documents = db.get_vector(request.course_id)
            
            if not documents:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No course content found for this course"
                )
            
            #print(documents)
            
            # Combine all document content
            lesson_content = ""
            for result in documents:
                if isinstance(result, dict) and 'content' in result:
                    lesson_content += result['content'] + "\n\n"
                elif isinstance(result, str):
                    lesson_content += result + "\n\n"
            
            # Initialize AI agent
            agent = CreateCourse()
            
            # Format chat history for the AI agent
            chat_history_text = ""
            if request.chat_history:
                chat_history_text = "\n\n--- Previous Conversation ---\n"
                for msg in request.chat_history:
                    role_name = "Student" if msg.role == "user" else "Teacher"
                    chat_history_text += f"{role_name}: {msg.content}\n"
                chat_history_text += "--- End of Previous Conversation ---\n\n"
            
            # Get AI response based on course content and chat history
            ai_response = await agent.question_answer(lesson_content, request.message, chat_history_text)
            
            # Extract text content from AI response
            response_text = ai_response
            if hasattr(ai_response, 'content'):
                response_text = ai_response.content
            elif hasattr(ai_response, 'text'):
                response_text = ai_response.text
            elif not isinstance(ai_response, str):
                response_text = str(ai_response)
                
            
            # Create current timestamp
            current_timestamp = datetime.datetime.now().isoformat()
            print(f"User message: {request.message}")
            print(f"AI response type: {type(ai_response)}")
            print(f"AI response text: {response_text}")

            # Create updated chat history
            updated_history = list(request.chat_history)
            updated_history.append(ChatMessage(
                role="user", 
                content=request.message, 
                timestamp=current_timestamp
            ))
            updated_history.append(ChatMessage(
                role="assistant", 
                content=response_text, 
                timestamp=current_timestamp
            ))
            
            return {
                'success': True,
                'course_id': request.course_id,
                'course_name': course['course_name'],
                'user_message': request.message,
                'ai_response': response_text,
                'timestamp': current_timestamp,
                'chat_history': updated_history
            }
            
        except Exception as e:
            print(f"Error in AI chat: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing chat request: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chat completion: {str(e)}"
        )

@app.post("/api/quiz/evaluate-answer")
async def evaluate_quiz_answer(request: QuizEvaluationRequest, current_user: str = Depends(verify_token)):
    """Evaluate a single quiz answer using AI agent"""
    try:
        if not all([request.question_id, request.question_text, request.correct_answer, request.user_answer]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required for evaluation"
            )
        print(request)
        # Initialize the AI agent
        agent = CreateCourse()
        
        # Evaluate the answer using the AI agent
        print("call evaluate")
        evaluation_result = await agent.evaluate(
            question=request.question_text,
            model_answer=request.correct_answer,
            user_answer=request.user_answer
        )
        print(evaluation_result)
        
        return {
            'success': True,
            'is_correct': evaluation_result,
            'question_id': request.question_id,
            'question_type': request.question_type
        }
        
    except Exception as e:
        print(f"Error evaluating answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating answer: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, debug=True) 