import chromadb
from chromadb.config import Settings
import bcrypt
import os
import uuid
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Initialize ChromaDB with persistent storage
        self.persist_directory = "./chroma_db"
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Get or create the users collection
        try:
            self.users_collection = self.client.get_collection("users")
        except:
            self.users_collection = self.client.create_collection("users")
        
        # Get or create the courses collection
        try:
            self.courses_collection = self.client.get_collection("courses")
        except:
            self.courses_collection = self.client.create_collection("courses")
        
        # Get or create the lessons collection
        try:
            self.lessons_collection = self.client.get_collection("lessons")
        except:
            self.lessons_collection = self.client.create_collection("lessons")
        
        # Get or create the content collection
        try:
            self.content_collection = self.client.get_collection("content")
        except:
            self.content_collection = self.client.create_collection("content")
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_user(self, username, email, password, full_name=None):
        """Create a new user in the database"""
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email)
            if existing_user:
                return False, "User already exists"
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user document
            user_id = str(uuid.uuid4())
            user_data = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "full_name": full_name or username,
                "created_at": str(uuid.uuid1().time)
            }
            
            # Add to ChromaDB collection
            self.users_collection.add(
                documents=[f"User: {username} Email: {email}"],
                metadatas=[user_data],
                ids=[user_id]
            )
            
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            results = self.users_collection.query(
                query_texts=[f"Email: {email}"],
                n_results=1,
                where={"email": email}
            )
            
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                return results['metadatas'][0][0]
            return None
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if user and self.verify_password(password, user['password']):
            return user
        return None
    
    def get_all_users(self):
        """Get all users from the database"""
        try:
            results = self.users_collection.get()
            return results['metadatas'] if results['metadatas'] else []
        except Exception as e:
            print(f"Error getting all users: {str(e)}")
            return []
    
    # Course methods
    def create_course(self, course_name, description, total_hour, status="Active", difficulty_level="Regular"):
        """Create a new course in the database"""
        try:
            course_id = str(uuid.uuid4())
            course_data = {
                "course_id": course_id,
                "course_name": course_name,
                "description": description,
                "total_hour": total_hour,
                "status": status,
                "create_at": datetime.now().isoformat(),
                "difficulty_level": difficulty_level
            }
            
            self.courses_collection.add(
                documents=[f"Course: {course_name} Description: {description} Difficulty: {difficulty_level}"],
                metadatas=[course_data],
                ids=[course_id]
            )
            
            return True, course_id
        except Exception as e:
            return False, f"Error creating course: {str(e)}"
    
    def get_course_by_id(self, course_id):
        """Get course by ID"""
        try:
            results = self.courses_collection.get(ids=[course_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            return None
        except Exception as e:
            print(f"Error getting course: {str(e)}")
            return None
    
    def get_all_courses(self):
        """Get all courses from the database"""
        try:
            results = self.courses_collection.get()
            return results['metadatas'] if results['metadatas'] else []
        except Exception as e:
            print(f"Error getting all courses: {str(e)}")
            return []
    
    # Lesson methods
    def create_lesson(self, course_id, lesson_title, duration_hours, lesson_order, description=""):
        """Create a new lesson in the database"""
        try:
            lesson_id = str(uuid.uuid4())
            lesson_data = {
                "lesson_id": lesson_id,
                "course_id": course_id,
                "lesson_title": lesson_title,
                "duration_hours": duration_hours,
                "lesson_order": lesson_order,
                "description": description
            }
            
            self.lessons_collection.add(
                documents=[f"Lesson: {lesson_title} Description: {description} Course: {course_id}"],
                metadatas=[lesson_data],
                ids=[lesson_id]
            )
            
            return True, lesson_id
        except Exception as e:
            return False, f"Error creating lesson: {str(e)}"
    
    def get_lessons_by_course_id(self, course_id):
        """Get all lessons for a specific course"""
        try:
            results = self.lessons_collection.query(
                query_texts=[f"Course: {course_id}"],
                n_results=100,
                where={"course_id": course_id}
            )
            # Flatten the nested list structure from ChromaDB
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting lessons: {str(e)}")
            return []
    
    def get_lesson_by_id(self, lesson_id):
        """Get lesson by ID"""
        try:
            results = self.lessons_collection.get(ids=[lesson_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            return None
        except Exception as e:
            print(f"Error getting lesson: {str(e)}")
            return None
    
    # Content methods
    def create_content(self, lesson_id, content_order, content, content_type="text", content_page=1):
        """Create new content in the database"""
        try:
            content_id = str(uuid.uuid4())
            content_data = {
                "content_id": content_id,
                "lesson_id": lesson_id,
                "content_order": content_order,
                "content": content,
                "content_type": content_type,
                "content_page": content_page
            }
            
            self.content_collection.add(
                documents=[f"Content: {content[:100]}... Type: {content_type} Lesson: {lesson_id}"],
                metadatas=[content_data],
                ids=[content_id]
            )
            
            return True, content_id
        except Exception as e:
            return False, f"Error creating content: {str(e)}"
    
    def get_content_by_lesson_id(self, lesson_id):
        """Get all content for a specific lesson"""
        try:
            results = self.content_collection.query(
                query_texts=[f"Lesson: {lesson_id}"],
                n_results=100,
                where={"lesson_id": lesson_id}
            )
            # Flatten the nested list structure from ChromaDB
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting content: {str(e)}")
            return []
    
    def initialize_sample_data(self):
        """Initialize sample user data"""
        sample_users = [
            {
                "username": "admin",
                "email": "admin@admin.com",
                "password": "admin",
                "full_name": "System Administrator"
            },
            {
                "username": "user1",
                "email": "user1@example.com", 
                "password": "password123",
                "full_name": "John Doe"
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "password456", 
                "full_name": "Jane Smith"
            }
        ]
        
        for user in sample_users:
            success, message = self.create_user(
                user['username'],
                user['email'],
                user['password'],
                user['full_name']
            )
            print(f"Creating user {user['email']}: {message}")
    
    def initialize_course_data(self):
        """Initialize sample course, lesson, and content data"""
        # Sample courses
        courses = [
            {
                "course_name": "Introduction to Python Programming",
                "description": "Learn the basics of Python programming language including syntax, data types, and control structures.",
                "total_hour": 40,
                "status": "Active",
                "difficulty_level": "Casual"
            },
            {
                "course_name": "Web Development with JavaScript",
                "description": "Master modern web development using JavaScript, HTML, and CSS. Build interactive web applications.",
                "total_hour": 60,
                "status": "Active", 
                "difficulty_level": "Regular"
            },
            {
                "course_name": "Advanced Machine Learning",
                "description": "Deep dive into machine learning algorithms, neural networks, and advanced AI concepts.",
                "total_hour": 80,
                "status": "Active",
                "difficulty_level": "Intense"
            },
            {
                "course_name": "Database Design Fundamentals",
                "description": "Learn database design principles, SQL, and relational database management systems.",
                "total_hour": 35,
                "status": "Inactive",
                "difficulty_level": "Regular"
            }
        ]
        
        course_ids = []
        for course in courses:
            success, course_id = self.create_course(
                course['course_name'],
                course['description'],
                course['total_hour'],
                course['status'],
                course['difficulty_level']
            )
            if success:
                course_ids.append(course_id)
                print(f"Created course: {course['course_name']}")
        
        # Sample lessons for each course
        lessons_data = [
            # Python Course Lessons
            [
                {"lesson_title": "Python Basics and Setup", "duration_hours": 3, "lesson_order": 1, "description": "Setting up Python environment and basic syntax"},
                {"lesson_title": "Variables and Data Types", "duration_hours": 4, "lesson_order": 2, "description": "Understanding Python data types and variables"},
                {"lesson_title": "Control Structures", "duration_hours": 5, "lesson_order": 3, "description": "If statements, loops, and conditional logic"},
                {"lesson_title": "Functions and Modules", "duration_hours": 6, "lesson_order": 4, "description": "Creating functions and organizing code with modules"}
            ],
            # JavaScript Course Lessons  
            [
                {"lesson_title": "HTML Structure", "duration_hours": 4, "lesson_order": 1, "description": "Building web page structure with HTML"},
                {"lesson_title": "CSS Styling", "duration_hours": 5, "lesson_order": 2, "description": "Styling web pages with CSS"},
                {"lesson_title": "JavaScript Fundamentals", "duration_hours": 6, "lesson_order": 3, "description": "JavaScript syntax and basic programming concepts"},
                {"lesson_title": "DOM Manipulation", "duration_hours": 7, "lesson_order": 4, "description": "Interacting with web page elements using JavaScript"}
            ],
            # Machine Learning Course Lessons
            [
                {"lesson_title": "ML Foundations", "duration_hours": 8, "lesson_order": 1, "description": "Mathematical foundations and concepts of machine learning"},
                {"lesson_title": "Supervised Learning", "duration_hours": 10, "lesson_order": 2, "description": "Classification and regression algorithms"},
                {"lesson_title": "Deep Learning", "duration_hours": 12, "lesson_order": 3, "description": "Neural networks and deep learning architectures"},
                {"lesson_title": "Model Deployment", "duration_hours": 8, "lesson_order": 4, "description": "Deploying ML models to production"}
            ],
            # Database Course Lessons
            [
                {"lesson_title": "Database Concepts", "duration_hours": 4, "lesson_order": 1, "description": "Introduction to database management systems"},
                {"lesson_title": "SQL Fundamentals", "duration_hours": 6, "lesson_order": 2, "description": "Basic SQL queries and database operations"},
                {"lesson_title": "Database Design", "duration_hours": 5, "lesson_order": 3, "description": "Normalization and database design principles"}
            ]
        ]
        
        lesson_ids_by_course = []
        for i, course_id in enumerate(course_ids):
            lesson_ids = []
            for lesson in lessons_data[i]:
                success, lesson_id = self.create_lesson(
                    course_id,
                    lesson['lesson_title'],
                    lesson['duration_hours'],
                    lesson['lesson_order'],
                    lesson['description']
                )
                if success:
                    lesson_ids.append(lesson_id)
                    print(f"Created lesson: {lesson['lesson_title']}")
            lesson_ids_by_course.append(lesson_ids)
        
        # Sample content for lessons
        content_templates = [
            # Text content
            {"content_type": "text", "content": "Welcome to this lesson! In this section, you will learn about the fundamental concepts and practical applications."},
            {"content_type": "text", "content": "Let's start with the basic theory and principles that form the foundation of this topic."},
            {"content_type": "text", "content": "Now let's look at some practical examples and how to apply what you've learned."},
            
            # Video content
            {"content_type": "video", "content": "introduction_video.mp4"},
            {"content_type": "video", "content": "demonstration_video.mp4"},
            {"content_type": "video", "content": "practical_examples.mp4"},
        ]
        
        # Create content for each lesson
        for lesson_ids in lesson_ids_by_course:
            for lesson_id in lesson_ids:
                for i, content_template in enumerate(content_templates[:4]):  # 4 content items per lesson
                    success, content_id = self.create_content(
                        lesson_id,
                        i + 1,
                        content_template['content'],
                        content_template['content_type'],
                        1 if content_template['content_type'] == 'text' else 1
                    )
                    if success:
                        print(f"Created content for lesson {lesson_id[:8]}...")

# Global database instance
db = DatabaseManager()
