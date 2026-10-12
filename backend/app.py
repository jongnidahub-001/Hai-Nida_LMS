from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import jwt
import datetime
from conn import db
import os
import sys
from agent.create_course.agent_autogen import CreateCourse
from agent.create_quiz.agent_autogen import CreateCourse as CreateQuiz
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from document_chunking import needs_chunking, map_reduce_compress_document, ChunkConfig
import asyncio
import concurrent.futures
import uuid
import base64
from typing import Literal
from uuid import uuid4
import httpx
from gemini_config import (
    get_gemini_model, set_gemini_model, get_gemini_api_key, set_gemini_api_key,
    get_model_for_role, set_model_for_role, get_all_role_models, VALID_ROLES
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
from contextlib import asynccontextmanager
import threading
import time
#from typhoon_ocr import ocr_document

# Global flag for background task processor
background_task_processor_running = False
background_task_thread = None

app = FastAPI(title="Learning Management System API", version="1.0.0")


# Add CORS middleware
# In production, set CORS_ORIGINS to allowed domains (comma-separated), e.g. "https://app.example.com,https://admin.example.com"
_cors_origins = os.environ.get("CORS_ORIGINS", "*").strip().split(",") if os.environ.get("CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
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
# อ่านจาก environment (.env.prod บน server) ถ้าไม่ตั้งจะใช้ค่า default สำหรับ dev เท่านั้น
SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'

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
    task_id: Optional[str] = None  # Optional: when provided, update background task status to 'generated' on success

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

class UpdateGeminiVersionRequest(BaseModel):
    model: str

class UpdateGeminiApiKeyRequest(BaseModel):
    api_key: str

class UpdateGeminiRoleModelRequest(BaseModel):
    role: str  # "planner", "writer", or "grader"
    model: str

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    course_id: str
    lesson_id: str
    message: str
    chat_history: List[ChatMessage] = []

class LessonRegenerateRequest(BaseModel):
    course_name: str
    course_description: str
    difficulty_level: str
    lesson_id: str
    lesson_order: int
    lesson_title: str
    duration_hours: int
    what_you_will_learn: List[str]
    current_content: str
    user_prompt: str

class QuestionRegenerateRequest(BaseModel):
    document_content: str
    quiz_title: str
    quiz_description: str
    difficulty_level: str
    question_id: str
    question_type: str
    question_text: str
    points: int
    current_choices: str
    current_answer: str
    user_prompt: str

# Background Task Request Models
class BatchCourseUploadRequest(BaseModel):
    DocumentBased64: str
    document_name: str
    quiz_params: Dict[str, Any]  # numberOfQuestions, numberOfChoices, etc.

class RetryTaskRequest(BaseModel):
    task_id: str

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

@app.get("/api/recommendation-courses")
async def get_recommendation_courses(current_user: str = Depends(verify_token)):
    """Get user's saved recommendation courses (from quiz submit). Returns full course objects."""
    try:
        user = db.get_user_by_email(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_id = user['user_id']
        course_ids = db.get_recommendation_courses(user_id)
        if not course_ids:
            return {"courses": [], "has_recommendations": False}
        courses_with_details = []
        seen = set()
        for cid in course_ids:
            if cid in seen:
                continue
            seen.add(cid)
            course = db.get_course_by_id(cid)
            if course:
                lessons = db.get_lessons_by_course_id(cid)
                courses_with_details.append({
                    'course_id': course.get('course_id'),
                    'course_name': course.get('course_name'),
                    'description': course.get('description'),
                    'total_hour': course.get('total_hour'),
                    'difficulty_level': course.get('difficulty_level'),
                    'status': course.get('status'),
                    'create_at': course.get('create_at'),
                    'lesson_count': len(lessons)
                })
        return {"courses": courses_with_details, "has_recommendations": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendation courses: {str(e)}"
        )

@app.post("/api/init-db")
async def init_database():
    """Initialize database and admin user only (no mock courses/users)"""
    try:
        global db
        from conn import DatabaseManager
        db = DatabaseManager()
        
        _ensure_admin_exists()
        
        return {
            'success': True,
            'message': "Database initialized with admin user"
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
                
                # Include quiz status for each course (single API, no extra calls)
                quiz_status = {'attempted': False, 'status': 'No Quiz', 'score': None, 'total_points': None}
                quizzes = db.get_quiz_by_course_id(enrollment['course_id'])
                if quizzes:
                    score_record = db.get_quiz_score(user_id, enrollment['course_id'], quizzes[0]['quiz_id'])
                    if score_record:
                        quiz_status = {
                            'attempted': True,
                            'status': 'Completed',
                            'score': score_record['score'],
                            'total_points': score_record['total_points']
                        }
                    else:
                        quiz_status = {'attempted': False, 'status': 'Not Attempted', 'score': None, 'total_points': None}
                
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
                    'progress': progress_summary,
                    'quiz_status': quiz_status
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

        # Compress document if it exceeds context window (Map-Reduce chunking)
        text = await prepare_document_for_agent(text)

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
                log_entry = {'agent': i.source, 'content': final_output}
            else:
                print("Content: ", i.content)
                log_entry = {'agent': i.source, 'content': i.content}
            # Include stage info if available (new pipeline)
            if hasattr(i, 'stage'):
                log_entry['stage'] = i.stage
            if hasattr(i, 'token_usage') and i.token_usage:
                log_entry['token_usage'] = i.token_usage
            log.append(log_entry)
            print("--------------------------------")

        if final_output:
            # Calculate total token usage across all agents
            total_tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            for entry in log:
                if entry.get('token_usage'):
                    total_tokens['prompt_tokens'] += entry['token_usage'].get('prompt_tokens', 0)
                    total_tokens['completion_tokens'] += entry['token_usage'].get('completion_tokens', 0)
                    total_tokens['total_tokens'] += entry['token_usage'].get('total_tokens', 0)
            
            output = {
                'log': log,
                'output': final_output,
                'total_token_usage': total_tokens,
            }
            os.remove(f"./temp/{_id}.pdf")
            return output
        else:
            print("No valid output generated from agent")
            os.remove(f"./temp/{_id}.pdf")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No valid output generated from agent"
            )
        
    except HTTPException:
        os.remove(f"./temp/{_id}.pdf")
        raise
    except Exception as e:
        print(f"Error in preview_course_with_agent: {str(e)}")
        os.remove(f"./temp/{_id}.pdf")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating course preview: {str(e)}"
        )

@app.post("/api/lesson/regenerate")
async def regenerate_lesson(request: LessonRegenerateRequest, current_user: str = Depends(verify_token)):
    """Regenerate a single lesson based on user's edit prompt"""
    try:
        # Initialize the CreateCourse agent
        course_creator = CreateCourse()
        
        # Call the regenerate lesson method
        result = await course_creator.regenerate_lesson(
            course_name=request.course_name,
            course_description=request.course_description,
            difficulty_level=request.difficulty_level,
            lesson_title=request.lesson_title,
            lesson_order=request.lesson_order,
            duration_hours=request.duration_hours,
            what_you_will_learn=request.what_you_will_learn,
            current_content=request.current_content,
            user_prompt=request.user_prompt
        )
        
        # Convert result to dict for response
        regenerated_data = {
            'lesson': {
                'lesson_id': request.lesson_id,
                'lesson_order': request.lesson_order,
                'lesson_title': result.lesson.lesson_title,
                'duration_hours': result.lesson.duration_hours,
                'description': result.lesson.description,
                'what_you_will_learn': result.lesson.what_you_will_learn
            },
            'lesson_contents': [
                {
                    'lesson_id': request.lesson_id,
                    'content_order': content.content_order,
                    'content_type': content.content_type,
                    'content': content.content
                }
                for content in result.lesson_contents
            ]
        }
        
        return {
            'success': True,
            'message': 'Lesson regenerated successfully',
            'data': regenerated_data
        }
        
    except Exception as e:
        print(f"Error in regenerate_lesson: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating lesson: {str(e)}"
        )

@app.post("/api/question/regenerate")
async def regenerate_question(request: QuestionRegenerateRequest, current_user: str = Depends(verify_token)):
    """Regenerate a single quiz question based on user's edit prompt"""
    _id = None
    try:
        # Extract text from document if it's base64 encoded PDF
        document_text = request.document_content
        if request.document_content and len(request.document_content) > 100:
            try:
                _id = uuid.uuid4()
                with open(f"./temp/{_id}.pdf", "wb") as f:
                    f.write(base64.b64decode(request.document_content))
                
                loader = PyPDFLoader(f"./temp/{_id}.pdf")
                docs = loader.lazy_load()
                document_text = ""
                for doc in docs:
                    document_text += doc.page_content
            except Exception as e:
                print(f"Error extracting PDF text, using raw content: {str(e)}")
                document_text = request.document_content
        
        # Initialize the CreateQuiz agent
        quiz_creator = CreateQuiz()
        
        # Call the regenerate question method
        result = await quiz_creator.regenerate_question(
            document_content=document_text,
            quiz_title=request.quiz_title,
            quiz_description=request.quiz_description,
            difficulty_level=request.difficulty_level,
            question_type=request.question_type,
            question_text=request.question_text,
            points=request.points,
            current_choices=request.current_choices,
            current_answer=request.current_answer,
            user_prompt=request.user_prompt
        )
        
        # Convert result to dict for response
        regenerated_data = {
            'question': {
                'question_id': request.question_id,
                'question_text': result.question.question_text,
                'question_type': result.question.question_type,
                'points': result.question.points
            },
            'choices': [
                {
                    'choice_text': choice.choice_text,
                    'is_correct': choice.is_correct
                }
                for choice in result.choices
            ] if result.choices else [],
            'answers': [
                {
                    'answer_text': answer.answer_text
                }
                for answer in result.answers
            ] if result.answers else []
        }
        
        # Cleanup temp file
        if _id and os.path.exists(f"./temp/{_id}.pdf"):
            os.remove(f"./temp/{_id}.pdf")
        
        return {
            'success': True,
            'message': 'Question regenerated successfully',
            'data': regenerated_data
        }
        
    except Exception as e:
        # Cleanup temp file on error
        if _id and os.path.exists(f"./temp/{_id}.pdf"):
            os.remove(f"./temp/{_id}.pdf")
        print(f"Error in regenerate_question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating question: {str(e)}"
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
                lesson_id=lesson['lesson_id'],
                course_id=lesson['course_id'],
                lesson_title=lesson['lesson_title'],
                duration_hours=lesson['duration_hours'],
                lesson_order=lesson['lesson_order'],
                description=lesson.get('description', ''),
                what_you_will_learn=lesson.get('what_you_will_learn', [])
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

        # Compress document if it exceeds context window (Map-Reduce chunking)
        text = await prepare_document_for_agent(text)

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
                log_entry = {'agent': i.source, 'content': final_output}
            else:
                print("Content: ", i.content)
                log_entry = {'agent': i.source, 'content': i.content}
            if hasattr(i, 'stage') and i.stage:
                log_entry['stage'] = i.stage
            if hasattr(i, 'token_usage') and i.token_usage:
                log_entry['token_usage'] = i.token_usage
            log.append(log_entry)
            print("--------------------------------")

        if final_output:
            # Calculate total token usage across all agents
            total_tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            for entry in log:
                if entry.get('token_usage'):
                    total_tokens['prompt_tokens'] += entry['token_usage'].get('prompt_tokens', 0)
                    total_tokens['completion_tokens'] += entry['token_usage'].get('completion_tokens', 0)
                    total_tokens['total_tokens'] += entry['token_usage'].get('total_tokens', 0)
            
            output = {
                'log': log,
                'output': final_output,
                'total_token_usage': total_tokens,
            }
            print(output)
            os.remove(f"./temp/{_id}.pdf")
            return output
        else:
            print("No valid output generated from agent")
            os.remove(f"./temp/{_id}.pdf")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No valid output generated from agent"
            )
        
    except HTTPException:
        os.remove(f"./temp/{_id}.pdf")
        raise
    except Exception as e:
        print(f"Error in preview_quiz_with_agent: {str(e)}")
        os.remove(f"./temp/{_id}.pdf")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz preview: {str(e)}"
        )

@app.post("/api/create-quiz/submit")
async def submit_quiz_to_database(request: QuizCreateSubmitRequest, current_user: str = Depends(verify_token)):
    """Submit generated quiz data to database (also creates course if it doesn't exist)"""

    try:
        task_id_to_update = request.task_id
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
        
        # Create lessons in parallel
        async def create_lesson_task(lesson):
            new_lesson_id = lesson_id_mapping[lesson['lesson_id']]
            return await asyncio.to_thread(
                db.create_lesson,
                lesson_id=new_lesson_id,
                course_id=new_course_id,
                lesson_title=lesson['lesson_title'],
                duration_hours=lesson['duration_hours'],
                lesson_order=lesson['lesson_order'],
                description=lesson['description'],
                what_you_will_learn=lesson.get('what_you_will_learn', [])
            ), new_lesson_id, lesson['lesson_title']

        if lessons_info:
            lesson_results = await asyncio.gather(*[create_lesson_task(l) for l in lessons_info])
            for (lesson_success, lesson_result), new_lesson_id, title in lesson_results:
                if lesson_success:
                    lessons_created += 1
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create lesson {title}: {lesson_result}"
                    )

        # Create lesson contents and vectors in parallel
        async def create_content_task(content):
            old_lesson_id = content['lesson_id']
            new_lesson_id = lesson_id_mapping.get(old_lesson_id)
            if not new_lesson_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find lesson mapping for {old_lesson_id}"
                )
            content_success, content_result = await asyncio.to_thread(
                db.create_content,
                lesson_id=new_lesson_id,
                content_order=content['content_order'],
                content_type=content['content_type'],
                content=content['content']
            )
            await asyncio.to_thread(db.add_vector, new_course_id, new_lesson_id, content['content'])
            return content_success, content_result, new_lesson_id

        if lesson_contents_info:
            content_results = await asyncio.gather(*[create_content_task(c) for c in lesson_contents_info])
            for content_success, content_result, new_lesson_id in content_results:
                if content_success:
                    contents_created += 1
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create content for lesson {new_lesson_id}: {content_result}"
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
        
        # Create questions in parallel
        created_questions = []
        async def create_question_task(question):
            old_question_id = question['question_id']
            new_question_id = question_id_mapping[old_question_id]
            success, result = await asyncio.to_thread(
                db.create_question,
                question_id=new_question_id,
                quiz_id=new_quiz_id,
                question_text=question['question_text'],
                question_type=question['question_type'],
                points=question['points']
            )
            return success, result, question, new_question_id

        if questions_info:
            question_results = await asyncio.gather(*[create_question_task(q) for q in questions_info])
            for success, result, question, new_question_id in question_results:
                if success:
                    created_questions.append({**question, 'question_id': new_question_id, 'quiz_id': new_quiz_id})
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create question {question['question_text']}: {result}"
                    )

        # Create choices in parallel
        created_choices = []
        async def create_choice_task(choice):
            old_question_id = choice['question_id']
            new_question_id = question_id_mapping.get(old_question_id)
            if not new_question_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find question mapping for {old_question_id}"
                )
            new_choice_id = str(uuid4())
            success, result = await asyncio.to_thread(
                db.create_choice,
                choice_id=new_choice_id,
                question_id=new_question_id,
                choice_text=choice['choice_text'],
                is_correct=choice['is_correct']
            )
            return success, result, choice, new_choice_id, new_question_id

        if choices_info:
            choice_results = await asyncio.gather(*[create_choice_task(c) for c in choices_info])
            for success, result, choice, new_choice_id, new_question_id in choice_results:
                if success:
                    created_choices.append({**choice, 'choice_id': new_choice_id, 'question_id': new_question_id})
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create choice for question {new_question_id}: {result}"
                    )

        # Create answers in parallel
        created_answers = []
        async def create_answer_task(answer):
            old_question_id = answer['question_id']
            new_question_id = question_id_mapping.get(old_question_id)
            if not new_question_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Warning: Could not find question mapping for {old_question_id}"
                )
            new_answer_id = str(uuid4())
            success, result = await asyncio.to_thread(
                db.create_answer,
                answer_id=new_answer_id,
                question_id=new_question_id,
                correct_answer=answer['answer_text']
            )
            return success, result, answer, new_answer_id, new_question_id

        if answers_info:
            answer_results = await asyncio.gather(*[create_answer_task(a) for a in answers_info])
            for success, result, answer, new_answer_id, new_question_id in answer_results:
                if success:
                    created_answers.append({**answer, 'answer_id': new_answer_id, 'question_id': new_question_id})
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Warning: Failed to create answer for question {new_question_id}: {result}"
                    )
        

        

        # Update background task status to 'generated' if task_id was provided (from Background Task flow)
        if task_id_to_update:
            db.update_background_task(task_id_to_update, status="generated")

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

async def _analyze_quiz_and_recommend(
    quiz_id: str,
    course_id: str,
    answers: List[Dict[str, Any]],
    score: int,
    total_points: int
) -> Dict[str, Any]:
    """
    Use AI to analyze quiz performance (strengths/weaknesses) and recommend lessons.
    Returns {
      strengths: [], weaknesses: [],
      intensive_lessons: [{ lesson_title, course_name, lesson_id, course_id }] - same title, diff difficulty (max 3),
      related_lessons_for_improvement: [{ ... }] - other lessons for improvement (max 3)
    }
    """
    strengths, weaknesses = [], []
    intensive_lessons = []
    related_lessons_for_improvement = []
    try:
        questions = db.get_questions_by_quiz_id(quiz_id)
        if not questions:
            return {
                'strengths': strengths, 'weaknesses': weaknesses,
                'intensive_lessons': intensive_lessons,
                'related_lessons_for_improvement': related_lessons_for_improvement
            }
        q_by_id = {str(q.get('question_id')): q for q in questions}
        correct_items = []
        incorrect_items = []
        for a in answers:
            qid = str(a.get('question_id', ''))
            q = q_by_id.get(qid)
            if not q:
                continue
            text = q.get('question_text', '') or ''
            is_correct = a.get('result', False)
            if is_correct:
                correct_items.append(text)
            else:
                incorrect_items.append(text)
        if not correct_items and not incorrect_items:
            return {
                'strengths': strengths, 'weaknesses': weaknesses,
                'intensive_lessons': intensive_lessons,
                'related_lessons_for_improvement': related_lessons_for_improvement
            }
        prompt = f"""You are an educational analyst. Analyze this quiz result and provide feedback.

Quiz score: {score}/{total_points}

Questions answered CORRECTLY:
{chr(10).join('- ' + t for t in correct_items[:20]) if correct_items else '(none)'}

Questions answered INCORRECTLY:
{chr(10).join('- ' + t for t in incorrect_items[:20]) if incorrect_items else '(none)'}

Respond with a JSON object only (no markdown, no explanation). Write all strengths and weaknesses in ENGLISH:
{{
  "strengths": ["list", "of", "2-5 short phrases in English describing topics/concepts the learner grasped well"],
  "weaknesses": ["list", "of", "2-5 short phrases in English describing topics to improve or review"]
}}

If strengths or weaknesses lists would be empty, use [] or provide at least one item based on the questions.
Output ONLY valid JSON, nothing else."""

        gemini_api_key = get_gemini_api_key()
        if gemini_api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage
            gemini = ChatGoogleGenerativeAI(model=get_gemini_model(), api_key=gemini_api_key)
            resp = await gemini.ainvoke([HumanMessage(content=prompt)])
            text = resp.content if hasattr(resp, "content") else str(resp)
            import re
            j = re.search(r'\{[\s\S]*\}', text)
            if j:
                import json
                data = json.loads(j.group())
                strengths = data.get('strengths') or []
                weaknesses = data.get('weaknesses') or []
            if isinstance(strengths, str):
                strengths = [strengths]
            if isinstance(weaknesses, str):
                weaknesses = [weaknesses]
        else:
            strengths = strengths or ['Review your correct answers to identify patterns.']
            weaknesses = weaknesses or ['Review the course material for topics you missed.']

        # 1. Intensive Lessons: same lesson title, different course (different difficulty) - max 3
        intensive_lessons = db.get_lessons_same_title_different_course(course_id, limit=3)

        # 2. Related Lessons for Improvement: semantically similar lessons, exclude intensive - max 3
        weakness_query = ' '.join(weaknesses) if weaknesses else ' '.join(incorrect_items[:3])
        intensive_keys = {(l['lesson_id'], l['course_id']) for l in intensive_lessons}
        if weakness_query.strip():
            similar = db.query_similar_lessons(weakness_query, n_results=15)
            for s in similar:
                if len(related_lessons_for_improvement) >= 3:
                    break
                lid, cid = s.get('lesson_id'), s.get('course_id')
                if not lid or not cid or (lid, cid) in intensive_keys:
                    continue
                if cid == course_id:
                    continue
                lesson = db.get_lesson_by_id(lid)
                course = db.get_course_by_id(cid) if cid else None
                if lesson and course:
                    related_lessons_for_improvement.append({
                        'lesson_id': lid,
                        'course_id': cid,
                        'lesson_title': lesson.get('lesson_title', 'Unknown'),
                        'course_name': course.get('course_name', 'Unknown')
                    })
    except Exception as e:
        print(f"Quiz analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
    return {
        'strengths': strengths,
        'weaknesses': weaknesses,
        'intensive_lessons': intensive_lessons,
        'related_lessons_for_improvement': related_lessons_for_improvement
    }


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
        
        analysis = await _analyze_quiz_and_recommend(
            request.quiz_id,
            request.course_id,
            request.answers,
            request.score,
            request.total_points
        )
        
        # Save quiz result analysis (strengths, weaknesses, recommendations) to DB
        if success and result and analysis:
            db.update_quiz_score_analysis(result, analysis)
        
        # Save recommendation courses for Featured Courses on home page
        all_rec_lessons = (analysis.get('intensive_lessons') or []) + (analysis.get('related_lessons_for_improvement') or [])
        if analysis and all_rec_lessons:
            unique_course_ids = list(dict.fromkeys(
                str(l.get('course_id')) for l in all_rec_lessons if l.get('course_id')
            ))
            if unique_course_ids:
                db.save_recommendation_courses(user_id, unique_course_ids)
        
        return {
            'success': True,
            'message': 'Quiz submitted successfully',
            'analysis': analysis
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

@app.get("/api/quiz-result/{course_id}")
async def get_quiz_result_for_course(course_id: str, current_user: str = Depends(verify_token)):
    """Get full quiz result including score and analysis (strengths, weaknesses, recommendations)"""
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
                "analysis": None
            }
        analysis = None
        if any(k in score_record for k in ('strengths', 'weaknesses', 'related_lessons', 'intensive_lessons', 'related_lessons_for_improvement')):
            analysis = {
                "strengths": score_record.get('strengths', []) or [],
                "weaknesses": score_record.get('weaknesses', []) or [],
                "intensive_lessons": score_record.get('intensive_lessons', []) or [],
                "related_lessons_for_improvement": score_record.get('related_lessons_for_improvement', []) or [],
                "related_lessons": score_record.get('related_lessons', []) or []  # backward compat
            }
        return {
            "success": True,
            "attempted": True,
            "score": score_record['score'],
            "total_points": score_record['total_points'],
            "taken_at": score_record.get('taken_at'),
            "analysis": analysis
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

# Admin Gemini Settings
@app.get("/api/admin/gemini/status")
async def get_gemini_status(current_user: str = Depends(verify_admin)):
    """Get current Gemini version and status (active/inactive). Admin only."""
    gemini_api_key = get_gemini_api_key()
    current_model = get_gemini_model()
    status_val = "inactive"
    error_message = None
    if gemini_api_key:
        try:
            from langchain_core.messages import HumanMessage
            gemini = ChatGoogleGenerativeAI(model=current_model, api_key=gemini_api_key, max_retries=0)
            resp = await gemini.ainvoke([HumanMessage(content="Say OK")])
            if resp and (hasattr(resp, "content") and resp.content):
                status_val = "active"
        except Exception as e:
            status_val = "inactive"
            error_msg = str(e)
            if "no longer available" in error_msg.lower():
                error_message = f"Model '{current_model}' is no longer available to new users. Please switch to a different model."
            elif "not found" in error_msg.lower() or "404" in error_msg:
                error_message = f"Model '{current_model}' not found. It may have been deprecated or removed."
            elif "permission" in error_msg.lower() or "403" in error_msg:
                error_message = f"Access denied for model '{current_model}'. Check your API key permissions."
            elif "quota" in error_msg.lower() or "429" in error_msg:
                error_message = f"Rate limit exceeded for model '{current_model}'. Try again later."
            elif "api key" in error_msg.lower() or "invalid" in error_msg.lower():
                error_message = f"Invalid API key. Please check your Gemini API key configuration."
            else:
                error_message = f"Model '{current_model}' is not usable: {error_msg}"
    else:
        error_message = "No API key configured. Please set a Gemini API key."
    
    response = {"current_version": current_model, "status": status_val}
    if error_message:
        response["error"] = error_message
    return response

@app.get("/api/admin/gemini/models")
async def get_gemini_models(current_user: str = Depends(verify_admin)):
    """List all Gemini models that support generateContent. Admin only."""
    gemini_api_key = get_gemini_api_key()
    if not gemini_api_key:
        return {"models": [], "error": "GOOGLE_API_KEY not configured"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key}",
                timeout=15.0
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {"models": [], "error": str(e)}
    models = []
    for m in data.get("models", []):
        supported = m.get("supportedGenerationMethods") or []
        if "generateContent" in supported:
            name = m.get("name", "")
            if name.startswith("models/"):
                name = name[7:]
            models.append(name)
    models.sort()
    return {"models": models}

@app.put("/api/admin/gemini/version")
async def update_gemini_version(
    request: UpdateGeminiVersionRequest,
    current_user: str = Depends(verify_admin)
):
    """Update selected Gemini model. Admin only. Validates the model is usable before saving."""
    if not request.model or not request.model.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is required")
    
    new_model = request.model.strip()
    gemini_api_key = get_gemini_api_key()
    
    if not gemini_api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No API key configured. Please set an API key first.")
    
    # Validate the model by making a test call
    try:
        from langchain_core.messages import HumanMessage
        gemini = ChatGoogleGenerativeAI(model=new_model, api_key=gemini_api_key, max_retries=0)
        resp = await gemini.ainvoke([HumanMessage(content="Say OK")])
        if not (resp and hasattr(resp, "content") and resp.content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{new_model}' did not return a valid response."
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Extract meaningful error message
        if "no longer available" in error_msg.lower():
            detail = f"Model '{new_model}' is no longer available. Please choose a different model."
        elif "not found" in error_msg.lower() or "404" in error_msg:
            detail = f"Model '{new_model}' not found. It may have been deprecated or removed."
        elif "permission" in error_msg.lower() or "403" in error_msg:
            detail = f"Access denied for model '{new_model}'. Your API key may not have permission to use this model."
        elif "402" in error_msg or "payment required" in error_msg.lower():
            detail = "Gemini API credits are exhausted (402 Payment Required). Add prepaid credits at aistudio.google.com/billing."
        elif "quota" in error_msg.lower() or "429" in error_msg:
            detail = f"Rate limit exceeded while testing model '{new_model}'. Please try again later."
        else:
            detail = f"Model '{new_model}' is not usable: {error_msg}"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    
    set_gemini_model(new_model)
    return {"success": True, "current_version": get_gemini_model()}


@app.get("/api/admin/gemini/role-models")
async def get_gemini_role_models(current_user: str = Depends(verify_admin)):
    """Get model configuration for all roles (planner, writer, grader). Admin only."""
    role_models = get_all_role_models()
    
    # Test each role model status
    gemini_api_key = get_gemini_api_key()
    status_per_role = {}
    
    if gemini_api_key:
        from langchain_core.messages import HumanMessage
        for role in VALID_ROLES:
            model_name = get_model_for_role(role)
            try:
                gemini = ChatGoogleGenerativeAI(model=model_name, api_key=gemini_api_key, max_retries=0)
                resp = await gemini.ainvoke([HumanMessage(content="Say OK")])
                if resp and hasattr(resp, "content") and resp.content:
                    status_per_role[role] = "active"
                else:
                    status_per_role[role] = "inactive"
            except Exception as e:
                status_per_role[role] = "inactive"
    else:
        for role in VALID_ROLES:
            status_per_role[role] = "inactive"
    
    return {
        **role_models,
        "status_per_role": status_per_role,
    }


@app.put("/api/admin/gemini/role-model")
async def update_gemini_role_model(
    request: UpdateGeminiRoleModelRequest,
    current_user: str = Depends(verify_admin)
):
    """Update the model for a specific role. Validates the model before saving. Admin only."""
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{request.role}'. Must be one of: {list(VALID_ROLES)}"
        )
    
    if not request.model or not request.model.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is required")
    
    new_model = request.model.strip()
    gemini_api_key = get_gemini_api_key()
    
    if not gemini_api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No API key configured.")
    
    # Validate the model
    try:
        from langchain_core.messages import HumanMessage
        gemini = ChatGoogleGenerativeAI(model=new_model, api_key=gemini_api_key, max_retries=0)
        resp = await gemini.ainvoke([HumanMessage(content="Say OK")])
        if not (resp and hasattr(resp, "content") and resp.content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{new_model}' did not return a valid response."
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "no longer available" in error_msg.lower():
            detail = f"Model '{new_model}' is no longer available."
        elif "not found" in error_msg.lower() or "404" in error_msg:
            detail = f"Model '{new_model}' not found."
        else:
            detail = f"Model '{new_model}' is not usable: {error_msg}"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    
    set_model_for_role(request.role, new_model)
    return {
        "success": True,
        "role": request.role,
        "model": new_model,
        "all_models": get_all_role_models(),
    }


@app.get("/api/admin/gemini/api-key")
async def get_gemini_api_key_status(current_user: str = Depends(verify_admin)):
    """Get Gemini API key info (masked) and source. Admin only."""
    api_key = get_gemini_api_key()
    if api_key:
        # Mask the key: show first 8 and last 4 chars
        if len(api_key) > 12:
            masked = api_key[:8] + "*" * (len(api_key) - 12) + api_key[-4:]
        else:
            masked = "*" * len(api_key)
        # Determine source
        from gemini_config import _read_config
        config_data = _read_config()
        source = "web_config" if config_data.get("api_key") else "env_file"
        return {"has_key": True, "masked_key": masked, "source": source}
    return {"has_key": False, "masked_key": "", "source": "none"}

@app.put("/api/admin/gemini/api-key")
async def update_gemini_api_key_endpoint(
    request: UpdateGeminiApiKeyRequest,
    current_user: str = Depends(verify_admin)
):
    """Update Gemini API key. Admin only."""
    if not request.api_key or not request.api_key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="api_key is required")
    new_key = request.api_key.strip()
    # Validate the key by making a simple API call
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={new_key}",
                timeout=15.0
            )
            r.raise_for_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid API key: {str(e)}"
        )
    set_gemini_api_key(new_key)
    return {"success": True, "message": "API key updated successfully"}

@app.delete("/api/admin/gemini/api-key")
async def delete_gemini_api_key_endpoint(current_user: str = Depends(verify_admin)):
    """Remove custom API key and revert to .env fallback. Admin only."""
    from gemini_config import _read_config, _write_config, CONFIG_FILE
    config_data = _read_config()
    if "api_key" in config_data:
        del config_data["api_key"]
        from gemini_config import _ensure_config_dir, CONFIG_FILE as cf
        _ensure_config_dir()
        import json as _json
        with open(cf, "w", encoding="utf-8") as f:
            _json.dump(config_data, f, indent=2)
    return {"success": True, "message": "Custom API key removed. Using .env fallback."}

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

@app.delete("/api/admin/user/{user_id}")
async def delete_user_admin(user_id: str, current_user: str = Depends(verify_admin)):
    """Delete a user and all related data (admin only)"""
    try:
        admin_user = db.get_user_by_email(current_user)
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        if admin_user['user_id'] == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        target_user = db.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        success, message = db.delete_user(user_id)
        if success:
            return {"success": True, "message": message}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                    success, _ = db.delete_quiz_score(score['score_id'])
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
            # Delete vector for this lesson
            try:
                db.delete_vector(course_id, lesson_id)
            except Exception as e:
                print(f"Warning: Error deleting vector for lesson {lesson_id}: {str(e)}")
            
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
                success, _ = db.delete_enrollment(enrollment['enroll_id'])
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
        
        # 6. Vectors deleted per-lesson in step 2 loop above
        
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

# ==================== DOCUMENT CHUNKING / MAP-REDUCE ====================

async def prepare_document_for_agent(
    text: str,
    progress_callback=None,
) -> str:
    """
    Prepare document text for agent. If too long, compress via Map-Reduce chunking.
    progress_callback: optional (message: str, percent: int) for UI updates
    """
    if not needs_chunking(text):
        return text
    gemini_api_key = get_gemini_api_key()
    if not gemini_api_key:
        return text[:80000] + "\n\n[Document truncated - set GOOGLE_API_KEY for full Map-Reduce]"
    gemini = ChatGoogleGenerativeAI(model=get_gemini_model(), api_key=gemini_api_key)

    async def llm_invoke(prompt: str) -> str:
        from langchain_core.messages import HumanMessage
        res = await gemini.ainvoke([HumanMessage(content=prompt)])
        return res.content if hasattr(res, "content") else str(res)

    return await map_reduce_compress_document(
        text, llm_invoke,
        config=ChunkConfig(max_doc_chars=80000),
        progress_callback=progress_callback,
    )


# ==================== BACKGROUND TASK ENDPOINTS ====================

async def process_single_task(task_id: str):
    """Process a single course generation task"""
    try:
        task = db.get_background_task(task_id)
        if not task:
            print(f"Task {task_id} not found")
            return
        
        # Update status to generating
        db.update_background_task(task_id, status="generating", progress="Starting generation...", progress_percent=5)
        
        # Get document from uploaded_documents collection
        document = db.get_uploaded_document(task['document_id'])
        if not document:
            db.update_background_task(task_id, status="error", error_message="Document not found")
            return
        
        # Decode and save document temporarily
        db.update_background_task(task_id, progress="Extracting document content...", progress_percent=15)
        _id = uuid.uuid4()
        temp_path = f"./temp/{_id}.pdf"
        
        try:
            # Check if compressed/extracted text is already cached from batch-create
            # This avoids re-extracting PDF and re-compressing for each of the 3 difficulty tasks
            fresh_document = db.get_uploaded_document(task['document_id'])
            cached_text = (fresh_document or {}).get('compressed_text')
            
            if cached_text and len(cached_text) > 100:
                text = cached_text
                db.update_background_task(task_id, progress="Using cached document...", progress_percent=25)
            else:
                # Fallback: extract PDF and compress (for tasks created before caching was implemented)
                with open(temp_path, "wb") as f:
                    f.write(base64.b64decode(document['document_base64']))
                
                loader = PyPDFLoader(temp_path)
                docs = loader.lazy_load()
                text = ""
                for doc in docs:
                    text += doc.page_content
                
                # Compress if needed
                def progress_cb(msg: str, pct: int):
                    db.update_background_task(task_id, progress=msg, progress_percent=pct)
                text = await prepare_document_for_agent(text, progress_callback=progress_cb)
                
                # Cache for any remaining sibling tasks
                try:
                    db.update_uploaded_document(task['document_id'], compressed_text=text)
                except Exception as cache_err:
                    print(f"Warning: Failed to cache compressed text: {cache_err}")
            
            db.update_background_task(task_id, progress="Generating course content...", progress_percent=30)
            
            # Generate course using AI with granular progress reporting
            course_creator = CreateCourse()
            
            def course_progress_cb(msg: str, pct: int):
                db.update_background_task(task_id, progress=msg, progress_percent=pct)
            
            result = await course_creator.create_course(
                text, task['difficulty_level'], progress_callback=course_progress_cb
            )
            
            db.update_background_task(task_id, progress="Processing AI response...", progress_percent=80)
            
            final_output = None
            log = []
            for i in result.messages:
                if i.source == "Expert_Agent":
                    final_output = i.content.dict()
                    log_entry = {'agent': i.source, 'content': final_output}
                else:
                    log_entry = {'agent': i.source, 'content': i.content}
                if hasattr(i, 'stage') and i.stage:
                    log_entry['stage'] = i.stage
                if hasattr(i, 'token_usage') and i.token_usage:
                    log_entry['token_usage'] = i.token_usage
                log.append(log_entry)
            
            if final_output:
                # Calculate total token usage across all agents
                total_tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
                for entry in log:
                    if entry.get('token_usage'):
                        total_tokens['prompt_tokens'] += entry['token_usage'].get('prompt_tokens', 0)
                        total_tokens['completion_tokens'] += entry['token_usage'].get('completion_tokens', 0)
                        total_tokens['total_tokens'] += entry['token_usage'].get('total_tokens', 0)
                
                output = {
                    'success': True,
                    'output': final_output,
                    'log': log,
                    'total_token_usage': total_tokens,
                    'quiz_params': task.get('quiz_params', {})
                }
                db.update_background_task(
                    task_id, 
                    status="done", 
                    result_data=output, 
                    progress="Completed successfully!", 
                    progress_percent=100
                )
                print(f"Task {task_id} completed successfully")
            else:
                db.update_background_task(
                    task_id, 
                    status="error", 
                    error_message="No output generated from AI agent",
                    progress="Failed - No output",
                    progress_percent=0
                )
                
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"Error processing task {task_id}: {str(e)}")
        db.update_background_task(
            task_id, 
            status="error", 
            error_message=str(e),
            progress=f"Error: {str(e)[:50]}...",
            progress_percent=0
        )

# Number of parallel workers for background task processing
MAX_PARALLEL_WORKERS = 3

# Track currently processing tasks to avoid duplicate processing
currently_processing = set()
processing_lock = threading.Lock()

def process_task_in_thread(task_id: str):
    """Process a single task in its own thread with its own event loop"""
    try:
        print(f"Worker started for task: {task_id}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_single_task(task_id))
        finally:
            loop.close()
    finally:
        # Remove from currently processing when done
        with processing_lock:
            currently_processing.discard(task_id)
        print(f"Worker finished for task: {task_id}")

def background_task_worker():
    """Background worker that processes pending tasks with parallel execution"""
    global background_task_processor_running
    
    print(f"Background task worker started with {MAX_PARALLEL_WORKERS} parallel workers")
    
    # Create a thread pool for parallel task processing
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS)
    
    while background_task_processor_running:
        try:
            # Get pending tasks
            pending_tasks = db.get_pending_tasks()
            
            # Filter out tasks that are already being processed
            with processing_lock:
                available_slots = MAX_PARALLEL_WORKERS - len(currently_processing)
                tasks_to_process = []
                
                for task in pending_tasks:
                    if len(tasks_to_process) >= available_slots:
                        break
                    task_id = task.get('task_id')
                    if task_id and task_id not in currently_processing:
                        tasks_to_process.append(task_id)
                        currently_processing.add(task_id)
            
            # Submit tasks to the thread pool for parallel processing
            for task_id in tasks_to_process:
                print(f"Submitting task to worker pool: {task_id}")
                executor.submit(process_task_in_thread, task_id)
            
            if tasks_to_process:
                print(f"Processing {len(tasks_to_process)} tasks in parallel (total active: {len(currently_processing)})")
            
            # Run cleanup every hour (check every 5 seconds, run hourly)
            current_time = time.time()
            if not hasattr(background_task_worker, 'last_cleanup'):
                background_task_worker.last_cleanup = current_time
            
            if current_time - background_task_worker.last_cleanup > 3600:  # 1 hour
                print("Running scheduled cleanup...")
                db.cleanup_old_tasks(days_old=7)
                db.cleanup_old_documents(days_old=7)
                background_task_worker.last_cleanup = current_time
            
            # Sleep for a short time before checking again
            time.sleep(5)
            
        except Exception as e:
            print(f"Error in background worker: {str(e)}")
            time.sleep(10)  # Wait longer on error
    
    # Shutdown executor gracefully
    print("Shutting down worker pool...")
    executor.shutdown(wait=True)
    print("Background task worker stopped")

def _ensure_admin_exists():
    """Check if admin user exists on startup; create the first admin from ADMIN_* env if not"""
    try:
        admin_users = db.get_users_by_role("admin")
        if admin_users and len(admin_users) > 0:
            print("Admin user already exists")
            return
        # No fallback password: an unset ADMIN_PASSWORD must not create a guessable admin
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
        if not admin_password:
            print("ERROR: No admin user exists and ADMIN_PASSWORD is not set; admin user was not created",
                  file=sys.stderr)
            return
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@admin.com")
        admin_username = os.environ.get("ADMIN_USERNAME", "admin")
        success, message = db.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            full_name="System Administrator",
            role="admin",
            is_auth=True,
        )
        if success:
            print(f"Created default admin user: {admin_email}")
        else:
            print(f"Failed to create admin user: {message}")
    except Exception as e:
        print(f"Error ensuring admin exists: {e}")


@app.on_event("startup")
async def start_background_worker():
    """Start the background task worker on app startup"""
    global background_task_processor_running, background_task_thread
    
    _ensure_admin_exists()
    
    background_task_processor_running = True
    background_task_thread = threading.Thread(target=background_task_worker, daemon=True)
    background_task_thread.start()
    print("Background task processor started")

@app.on_event("shutdown")
async def stop_background_worker():
    """Stop the background task worker on app shutdown"""
    global background_task_processor_running
    
    background_task_processor_running = False
    print("Background task processor stopped")

@app.post("/api/background-tasks/batch-create")
async def create_batch_tasks(request: BatchCourseUploadRequest, current_user: str = Depends(verify_token)):
    """Create 3 background tasks for all difficulty levels (Casual, Regular, Intense)"""
    try:
        difficulty_levels = ["Casual", "Regular", "Intense"]
        created_tasks = []
        
        # Store document once
        document_id = str(uuid.uuid4())
        doc_success, doc_result = db.create_uploaded_document(
            document_id=document_id,
            document_name=request.document_name,
            document_base64=request.DocumentBased64,
            user_id=current_user
        )
        
        if not doc_success:
            raise HTTPException(status_code=500, detail=f"Failed to store document: {doc_result}")
        
        # Pre-compress document ONCE here so all 3 tasks can reuse it (cost optimization)
        try:
            _id = uuid.uuid4()
            temp_path = f"./temp/{_id}.pdf"
            with open(temp_path, "wb") as f:
                f.write(base64.b64decode(request.DocumentBased64))
            loader = PyPDFLoader(temp_path)
            docs = loader.lazy_load()
            raw_text = ""
            for doc in docs:
                raw_text += doc.page_content
            os.remove(temp_path)
            
            compressed_text = await prepare_document_for_agent(raw_text)
            db.update_uploaded_document(document_id, compressed_text=compressed_text)
        except Exception as compress_err:
            print(f"Warning: Pre-compression failed, tasks will compress individually: {compress_err}")
        
        # Create a task for each difficulty level
        for difficulty in difficulty_levels:
            task_id = str(uuid.uuid4())
            
            quiz_params = request.quiz_params.copy()
            quiz_params['difficulty'] = difficulty
            
            success, result = db.create_background_task(
                task_id=task_id,
                document_id=document_id,
                document_name=request.document_name,
                difficulty_level=difficulty,
                user_id=current_user,
                quiz_params=quiz_params
            )
            
            if success:
                created_tasks.append({
                    "task_id": task_id,
                    "difficulty_level": difficulty,
                    "status": "pending",
                    "progress": "Queued",
                    "progress_percent": 0
                })
            else:
                print(f"Failed to create task for {difficulty}: {result}")
        
        return {
            "success": True, 
            "document_id": document_id,
            "tasks": created_tasks,
            "message": f"Created {len(created_tasks)} generation tasks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating batch tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/background-tasks")
async def get_background_tasks(current_user: str = Depends(verify_token)):
    """Get all background tasks for current user"""
    try:
        tasks = db.get_background_tasks(user_id=current_user)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/background-tasks/{task_id}")
async def get_background_task(task_id: str, current_user: str = Depends(verify_token)):
    """Get a single background task with its result"""
    try:
        task = db.get_background_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Verify ownership
        if task.get('user_id') != current_user:
            # Check if admin
            user = db.get_user_by_email(current_user)
            if not user or user.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Get document base64 if task is done (for preview)
        if task.get('status') == 'done' and task.get('document_id'):
            document = db.get_uploaded_document(task['document_id'])
            if document:
                task['document_base64'] = document.get('document_base64', '')
        
        return {"success": True, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/background-tasks/{task_id}")
async def delete_background_task(task_id: str, current_user: str = Depends(verify_token)):
    """Delete a background task"""
    try:
        task = db.get_background_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Verify ownership or admin
        if task.get('user_id') != current_user:
            user = db.get_user_by_email(current_user)
            if not user or user.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
        
        success, result = db.delete_background_task(task_id)
        if success:
            return {"success": True, "message": "Task deleted"}
        raise HTTPException(status_code=500, detail=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/background-tasks/{task_id}/retry")
async def retry_background_task(task_id: str, current_user: str = Depends(verify_token)):
    """Retry a failed background task"""
    try:
        task = db.get_background_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Verify ownership
        if task.get('user_id') != current_user:
            user = db.get_user_by_email(current_user)
            if not user or user.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Only allow retry for failed tasks
        if task.get('status') != 'error':
            raise HTTPException(status_code=400, detail="Can only retry failed tasks")
        
        # Check retry count
        success, message = db.increment_retry_count(task_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/background-tasks/cleanup")
async def manual_cleanup(current_user: str = Depends(verify_admin)):
    """Manually trigger cleanup of old tasks (admin only)"""
    try:
        task_success, task_message = db.cleanup_old_tasks(days_old=7)
        doc_success, doc_message = db.cleanup_old_documents(days_old=7)
        
        return {
            "success": True,
            "tasks_cleanup": task_message,
            "documents_cleanup": doc_message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/background-tasks/stats/summary")
async def get_task_stats(current_user: str = Depends(verify_token)):
    """Get summary statistics of background tasks for current user"""
    try:
        tasks = db.get_background_tasks(user_id=current_user)
        
        stats = {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.get('status') == 'pending']),
            "generating": len([t for t in tasks if t.get('status') == 'generating']),
            "done": len([t for t in tasks if t.get('status') == 'done']),
            "generated": len([t for t in tasks if t.get('status') == 'generated']),
            "error": len([t for t in tasks if t.get('status') == 'error'])
        }
        
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, debug=True)