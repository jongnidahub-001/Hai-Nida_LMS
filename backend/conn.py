import chromadb
from chromadb.config import Settings
import bcrypt
import os
import uuid
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Initialize ChromaDB with persistent storage
        self.persist_directory = "./chroma_db"
        
        # Create directory if it doesn't exist

        # if not os.path.exists(self.persist_directory):
        #     print(f"Creating directory: {self.persist_directory}")
        #     os.makedirs(self.persist_directory)
        
        try:
            
            # Initialize ChromaDB client with settings
            # Use environment variable for host, fallback to localhost for local development
            chroma_host = os.environ.get('CHROMA_HOST', 'localhost')
            chroma_port = int(os.environ.get('CHROMA_PORT', '8000'))
            print(f"Setting up chroma client with host: {chroma_host} and port: {chroma_port}")
            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

            # self.client = chromadb.PersistentClient(
            #     path=self.persist_directory, 
            #     settings=Settings(
            #         anonymized_telemetry=False,
            #         allow_reset=True
            #     )
            # )
            
            # Get or create collections
            self._initialize_collections()
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            # If there's an error, try to reset the database
            # if os.path.exists(self.persist_directory):
            #     import shutil
            #     shutil.rmtree(self.persist_directory)
            #     os.makedirs(self.persist_directory)
            
            # Reinitialize client
            # Use environment variable for host, fallback to localhost for local development
            chroma_host = os.environ.get('CHROMA_HOST', 'localhost')
            chroma_port = int(os.environ.get('CHROMA_PORT', '8000'))
            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            # self.client = chromadb.PersistentClient(
            #     path=self.persist_directory,
            #     settings=Settings(
            #         anonymized_telemetry=False,
            #         allow_reset=True
            #     )
            # )
            self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize all required collections"""
        collections = [
            "users", "courses", "lessons", "content", 
            "enrollments", "progress", "quiz", "question", 
            "choice", "answer", "quiz_score", "vector",
            "background_tasks", "uploaded_documents", "user_recommendation_courses"
        ]


        for collection_name in collections:
            try:
                collection = self.client.get_collection(collection_name)
                print(collection)
                setattr(self, f"{collection_name}_collection", collection)
                print(f"Collection: {collection_name} already exists")
            except Exception as e:
                print(f"Error initializing collection: {e}")
                print(f"Creating collection: {collection_name}")
                collection = self.client.create_collection(collection_name)
                setattr(self, f"{collection_name}_collection", collection)
                print(f"Created collection: {collection_name}")
        
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_user(self, username, email, password, full_name=None, role="user", is_auth=True):
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
                "role": role,
                "is_auth": is_auth,
                "created_at": str(uuid.uuid1().time)
            }
            
            # Add to ChromaDB collection
            self.users_collection.add(
                documents=[f"User: {username} Email: {email} Role: {role}"],
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
    def create_course(self, course_id=None, course_name=None, description=None, total_hour=None, status="Active", difficulty_level="Regular", learning_objectives=None, prerequisites=None):
        """Create a new course in the database"""
        try:
            if course_id is None:
                course_id = str(uuid.uuid4())
            else:
                course_id = course_id
            course_data = {
                "course_id": course_id,
                "course_name": course_name,
                "description": description,
                "total_hour": total_hour,
                "status": status,
                "create_at": datetime.now().isoformat(),
                "difficulty_level": difficulty_level,
                "learning_objectives": json.dumps(learning_objectives if learning_objectives is not None else []),
                "prerequisites": json.dumps(prerequisites if prerequisites is not None else [])
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
                course = results['metadatas'][0]
                # Parse JSON strings back to lists
                if 'learning_objectives' in course:
                    course['learning_objectives'] = json.loads(course['learning_objectives'])
                if 'prerequisites' in course:
                    course['prerequisites'] = json.loads(course['prerequisites'])
                return course
            return None
        except Exception as e:
            print(f"Error getting course: {str(e)}")
            return None
    
    def get_all_courses(self):
        """Get all courses from the database"""
        try:
            results = self.courses_collection.get()
            courses = results['metadatas'] if results['metadatas'] else []
            # Parse JSON strings back to lists for all courses
            for course in courses:
                if 'learning_objectives' in course:
                    course['learning_objectives'] = json.loads(course['learning_objectives'])
                if 'prerequisites' in course:
                    course['prerequisites'] = json.loads(course['prerequisites'])
            return courses
        except Exception as e:
            print(f"Error getting all courses: {str(e)}")
            return []
    
    # Lesson methods
    def create_lesson(self, lesson_id=None, course_id=None, lesson_title=None, duration_hours=None, lesson_order=None, description=None, what_you_will_learn=None):
        """Create a new lesson in the database"""
        try:
            if lesson_id is None:
                lesson_id = str(uuid.uuid4())
            else:
                lesson_id = lesson_id
            lesson_data = {
                "lesson_id": lesson_id,
                "course_id": course_id,
                "lesson_title": lesson_title,
                "duration_hours": duration_hours,
                "lesson_order": lesson_order,
                "description": description,
                "what_you_will_learn": json.dumps(what_you_will_learn if what_you_will_learn is not None else [])
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
                lessons = [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
                # Parse JSON strings back to lists for all lessons
                for lesson in lessons:
                    if 'what_you_will_learn' in lesson:
                        lesson['what_you_will_learn'] = json.loads(lesson['what_you_will_learn'])
                return lessons
            return []
        except Exception as e:
            print(f"Error getting lessons: {str(e)}")
            return []
    
    def get_lesson_by_id(self, lesson_id):
        """Get lesson by ID"""
        try:
            results = self.lessons_collection.get(ids=[lesson_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                lesson = results['metadatas'][0]
                # Parse JSON string back to list
                if 'what_you_will_learn' in lesson:
                    lesson['what_you_will_learn'] = json.loads(lesson['what_you_will_learn'])
                return lesson
            return None
        except Exception as e:
            print(f"Error getting lesson: {str(e)}")
            return None
    
    # Content methods
    def create_content(self, lesson_id, content_order, content, content_type="text"):
        """Create new content in the database"""
        try:
            content_id = str(uuid.uuid4())
            content_data = {
                "content_id": content_id,
                "lesson_id": lesson_id,
                "content_order": content_order,
                "content": content,
                "content_type": content_type
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
                "full_name": "System Administrator",
                "role": "admin",
                "is_auth": True
            },
            {
                "username": "user1",
                "email": "user1@example.com", 
                "password": "password123",
                "full_name": "John Doe",
                "role": "user",
                "is_auth": True
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "password456", 
                "full_name": "Jane Smith",
                "role": "user",
                "is_auth": True
            }
        ]
        
        for user in sample_users:
            success, message = self.create_user(
                user['username'],
                user['email'],
                user['password'],
                user['full_name'],
                user['role'],
                user['is_auth']
            )
            print(f"Creating user {user['email']}: {message}")
    
    def initialize_course_data(self):
        """Initialize sample course, lesson, and content data"""
        print("Starting course data initialization...")
        # Sample courses
        courses = [
            {
                "course_name": "Introduction to Python Programming",
                "description": "Learn the basics of Python programming language including syntax, data types, and control structures.",
                "total_hour": 40,
                "status": "Active",
                "difficulty_level": "Casual",
                "learning_objectives": [
                    "Understand Python syntax and basic programming concepts",
                    "Work with different data types and variables",
                    "Implement control structures like loops and conditionals",
                    "Create and use functions effectively",
                    "Handle errors and exceptions in Python programs"
                ],
                "prerequisites": [
                    "Basic computer literacy",
                    "Understanding of fundamental programming concepts"
                ]
            },
            {
                "course_name": "Web Development with JavaScript",
                "description": "Master modern web development using JavaScript, HTML, and CSS. Build interactive web applications.",
                "total_hour": 60,
                "status": "Active", 
                "difficulty_level": "Regular",
                "learning_objectives": [
                    "Build responsive web pages using HTML and CSS",
                    "Implement interactive features with JavaScript",
                    "Manipulate the DOM and handle user events",
                    "Work with APIs and asynchronous JavaScript",
                    "Deploy web applications to hosting platforms"
                ],
                "prerequisites": [
                    "Basic HTML and CSS knowledge",
                    "Understanding of programming fundamentals",
                    "Familiarity with text editors and web browsers"
                ]
            },
            {
                "course_name": "Advanced Machine Learning",
                "description": "Deep dive into machine learning algorithms, neural networks, and advanced AI concepts.",
                "total_hour": 80,
                "status": "Active",
                "difficulty_level": "Intense",
                "learning_objectives": [
                    "Implement advanced machine learning algorithms from scratch",
                    "Design and train deep neural networks",
                    "Apply reinforcement learning techniques",
                    "Optimize model performance and handle large datasets",
                    "Deploy ML models in production environments"
                ],
                "prerequisites": [
                    "Strong foundation in Python programming",
                    "Linear algebra and calculus knowledge",
                    "Basic machine learning concepts",
                    "Statistics and probability theory",
                    "Experience with NumPy and Pandas"
                ]
            },
            {
                "course_name": "Database Design Fundamentals",
                "description": "Learn database design principles, SQL, and relational database management systems.",
                "total_hour": 35,
                "status": "Inactive",
                "difficulty_level": "Regular",
                "learning_objectives": [
                    "Design normalized relational database schemas",
                    "Write complex SQL queries for data retrieval",
                    "Implement database constraints and relationships",
                    "Optimize database performance and indexing",
                    "Understand transaction management and concurrency"
                ],
                "prerequisites": [
                    "Basic understanding of data structures",
                    "Familiarity with logical thinking and problem solving",
                    "Basic knowledge of software applications"
                ]
            }
        ]
        
        course_ids = []
        for course in courses:
            print(f"Creating course: {course['course_name']}")
            success, result = self.create_course(
                course_name=course['course_name'],
                description=course['description'],
                total_hour=course['total_hour'],
                status=course['status'],
                difficulty_level=course['difficulty_level'],
                learning_objectives=course['learning_objectives'],
                prerequisites=course['prerequisites']
            )
            if success:
                course_ids.append(result)
                print(f"✓ Created course: {course['course_name']}")
            else:
                print(f"✗ Failed to create course {course['course_name']}: {result}")
        
        # Sample lessons for each course
        lessons_data = [
            # Python Course Lessons
            [
                {
                    "lesson_title": "Python Basics and Setup", 
                    "duration_hours": 3, 
                    "lesson_order": 1, 
                    "description": "Setting up Python environment and basic syntax",
                    "what_you_will_learn": [
                        "Install Python and set up development environment",
                        "Understand Python interpreter and IDLE",
                        "Write and execute your first Python programs",
                        "Learn Python syntax and indentation rules"
                    ]
                },
                {
                    "lesson_title": "Variables and Data Types", 
                    "duration_hours": 4, 
                    "lesson_order": 2, 
                    "description": "Understanding Python data types and variables",
                    "what_you_will_learn": [
                        "Declare and assign variables in Python",
                        "Work with integers, floats, strings, and booleans",
                        "Understand type conversion and casting",
                        "Use Python built-in functions for data types"
                    ]
                },
                {
                    "lesson_title": "Control Structures", 
                    "duration_hours": 5, 
                    "lesson_order": 3, 
                    "description": "If statements, loops, and conditional logic",
                    "what_you_will_learn": [
                        "Write conditional statements using if, elif, and else",
                        "Create for loops and while loops",
                        "Implement nested loops and loop control statements",
                        "Use logical operators and comparison operators"
                    ]
                },
                {
                    "lesson_title": "Functions and Modules", 
                    "duration_hours": 6, 
                    "lesson_order": 4, 
                    "description": "Creating functions and organizing code with modules",
                    "what_you_will_learn": [
                        "Define and call functions with parameters",
                        "Understand return values and scope",
                        "Create and import custom modules",
                        "Use built-in Python modules and packages"
                    ]
                }
            ],
            # JavaScript Course Lessons  
            [
                {
                    "lesson_title": "HTML Structure", 
                    "duration_hours": 4, 
                    "lesson_order": 1, 
                    "description": "Building web page structure with HTML",
                    "what_you_will_learn": [
                        "Create semantic HTML document structure",
                        "Use HTML tags for headings, paragraphs, and lists",
                        "Add images, links, and multimedia content",
                        "Build forms and input elements"
                    ]
                },
                {
                    "lesson_title": "CSS Styling", 
                    "duration_hours": 5, 
                    "lesson_order": 2, 
                    "description": "Styling web pages with CSS",
                    "what_you_will_learn": [
                        "Apply CSS styles using selectors and properties",
                        "Create responsive layouts with Flexbox and Grid",
                        "Style text, colors, and backgrounds",
                        "Implement animations and transitions"
                    ]
                },
                {
                    "lesson_title": "JavaScript Fundamentals", 
                    "duration_hours": 6, 
                    "lesson_order": 3, 
                    "description": "JavaScript syntax and basic programming concepts",
                    "what_you_will_learn": [
                        "Understand JavaScript variables and data types",
                        "Write functions and handle events",
                        "Work with arrays and objects",
                        "Implement conditional logic and loops in JavaScript"
                    ]
                },
                {
                    "lesson_title": "DOM Manipulation", 
                    "duration_hours": 7, 
                    "lesson_order": 4, 
                    "description": "Interacting with web page elements using JavaScript",
                    "what_you_will_learn": [
                        "Select and modify HTML elements with JavaScript",
                        "Handle user events like clicks and form submissions",
                        "Create dynamic content and interactive features",
                        "Validate forms and provide user feedback"
                    ]
                }
            ],
            # Machine Learning Course Lessons
            [
                {
                    "lesson_title": "ML Foundations", 
                    "duration_hours": 8, 
                    "lesson_order": 1, 
                    "description": "Mathematical foundations and concepts of machine learning",
                    "what_you_will_learn": [
                        "Understand supervised vs unsupervised learning",
                        "Learn linear algebra concepts for ML",
                        "Grasp probability and statistics fundamentals",
                        "Explore data preprocessing techniques"
                    ]
                },
                {
                    "lesson_title": "Supervised Learning", 
                    "duration_hours": 10, 
                    "lesson_order": 2, 
                    "description": "Classification and regression algorithms",
                    "what_you_will_learn": [
                        "Implement linear and logistic regression",
                        "Build decision trees and random forests",
                        "Apply support vector machines (SVM)",
                        "Evaluate model performance with metrics"
                    ]
                },
                {
                    "lesson_title": "Deep Learning", 
                    "duration_hours": 12, 
                    "lesson_order": 3, 
                    "description": "Neural networks and deep learning architectures",
                    "what_you_will_learn": [
                        "Build neural networks from scratch",
                        "Implement convolutional neural networks (CNNs)",
                        "Create recurrent neural networks (RNNs)",
                        "Use popular deep learning frameworks"
                    ]
                },
                {
                    "lesson_title": "Model Deployment", 
                    "duration_hours": 8, 
                    "lesson_order": 4, 
                    "description": "Deploying ML models to production",
                    "what_you_will_learn": [
                        "Package models for production deployment",
                        "Create REST APIs for model serving",
                        "Implement model monitoring and versioning",
                        "Scale models using cloud platforms"
                    ]
                }
            ],
            # Database Course Lessons
            [
                {
                    "lesson_title": "Database Concepts", 
                    "duration_hours": 4, 
                    "lesson_order": 1, 
                    "description": "Introduction to database management systems",
                    "what_you_will_learn": [
                        "Understand relational database concepts",
                        "Learn about tables, rows, and columns",
                        "Explore different types of databases",
                        "Understand ACID properties and transactions"
                    ]
                },
                {
                    "lesson_title": "SQL Fundamentals", 
                    "duration_hours": 6, 
                    "lesson_order": 2, 
                    "description": "Basic SQL queries and database operations",
                    "what_you_will_learn": [
                        "Write SELECT statements to query data",
                        "Insert, update, and delete database records",
                        "Use WHERE clauses and filtering conditions",
                        "Join multiple tables and aggregate data"
                    ]
                },
                {
                    "lesson_title": "Database Design", 
                    "duration_hours": 5, 
                    "lesson_order": 3, 
                    "description": "Normalization and database design principles",
                    "what_you_will_learn": [
                        "Apply database normalization techniques",
                        "Design efficient database schemas",
                        "Create primary and foreign key relationships",
                        "Optimize database performance with indexes"
                    ]
                }
            ]
        ]
        
        lesson_ids_by_course = []
        for i, course_id in enumerate(course_ids):
            lesson_ids = []
            for lesson in lessons_data[i]:
                success, lesson_id = self.create_lesson(
                    course_id = course_id,
                    lesson_title = lesson['lesson_title'],
                    duration_hours = lesson['duration_hours'],
                    lesson_order = lesson['lesson_order'],
                    description = lesson['description'],
                    what_you_will_learn = lesson['what_you_will_learn']
                )
                if success:
                    lesson_ids.append(lesson_id)
                    print(f"Created lesson: {lesson['lesson_title']}")
            lesson_ids_by_course.append(lesson_ids)
        
        # Comprehensive content templates for different lesson types
        def create_comprehensive_content(lesson_id, lesson_title):
            """Create diverse content for a lesson in a single flow"""
            content_items = []
            
            # Single continuous lesson content
            content_items = [
                {
                    "lesson_id": lesson_id,
                    "content_order": 1,
                    "content_type": "text",
                    "content": f"# Welcome to {lesson_title}\n\nIn this comprehensive lesson, you'll dive deep into the fundamental concepts and practical applications. This lesson is designed to provide you with both theoretical knowledge and hands-on experience."
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 2,
                    "content_type": "video",
                    "content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" if "introduction" in lesson_title.lower() else "https://vimeo.com/123456789"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 3,
                    "content_type": "text",
                    "content": "## Learning Objectives\n\nBy the end of this lesson, you will be able to:\n- Understand the core concepts and principles\n- Apply the knowledge in practical scenarios\n- Identify common patterns and best practices\n- Troubleshoot common issues and challenges"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 4,
                    "content_type": "text",
                    "content": f"## Theoretical Foundation\n\nLet's explore the fundamental theory behind {lesson_title.lower()}. Understanding these concepts is crucial for building a solid foundation in this topic.\n\n### Key Concepts:\n1. **Primary Principles**: The core ideas that drive this field\n2. **Historical Context**: How these concepts evolved over time\n3. **Modern Applications**: Current use cases and implementations"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 5,
                    "content_type": "video",
                    "content": "test.mp4"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 6,
                    "content_type": "text",
                    "content": "### Important Notes\n\n> **Remember**: These theoretical concepts form the backbone of practical implementation. Take time to understand each principle before moving to the next section.\n\n**Pro Tip**: Create your own examples while reading to reinforce understanding."
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 7,
                    "content_type": "text",
                    "content": "## Hands-On Practice\n\nTime to put theory into practice! This section contains step-by-step examples and interactive demonstrations.\n\n### Example 1: Basic Implementation\nLet's start with a simple example that demonstrates the core concepts in action."
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 8,
                    "content_type": "video",
                    "content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" if "web" in lesson_title.lower() else f"practical_demo_{lesson_id[:8]}.mp4"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 9,
                    "content_type": "text",
                    "content": "```python\n# Sample code example\ndef demonstrate_concept():\n    \"\"\"\n    This function demonstrates the key concepts\n    discussed in the theoretical section.\n    \"\"\"\n    result = process_data()\n    return validate_output(result)\n\n# Try this example yourself!\nprint(demonstrate_concept())\n```"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 10,
                    "content_type": "text",
                    "content": "## Practice Exercises\n\nTest your understanding with these interactive exercises. Each exercise builds upon the concepts learned in this lesson.\n\n### Exercise 1: Basic Application\nApply the fundamental concepts to solve this practical problem.\n\n**Challenge**: Implement a solution using the principles discussed. Consider edge cases and optimization opportunities."
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 11,
                    "content_type": "video",
                    "content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" if "machine learning" in lesson_title.lower() else f"exercise_walkthrough_{lesson_id[:8]}.mp4"
                },
                {
                    "lesson_id": lesson_id,
                    "content_order": 12,
                    "content_type": "text",
                    "content": "## Summary and Additional Resources\n\nCongratulations! You've completed this lesson. Here's what you've accomplished:\n\n✅ Mastered the theoretical foundations\n✅ Worked through practical examples\n✅ Completed hands-on exercises\n\n### Recommended Reading\n- Documentation and official guides\n- Industry best practices and standards\n- Case studies and real-world implementations\n\n### What's Next?\nIn the next lesson, we'll build upon these concepts and explore advanced topics."
                }
            ]
            
            return content_items
        
        # Create comprehensive content for each lesson
        total_content_created = 0
        for course_idx, lesson_ids in enumerate(lesson_ids_by_course):
            course_name = courses[course_idx]['course_name']
            print(f"\nCreating content for course: {course_name}")
            
            for lesson_id in lesson_ids:
                # Get lesson details for more contextual content
                lesson = self.get_lesson_by_id(lesson_id)
                if lesson:
                    lesson_title = lesson.get('lesson_title', 'Untitled Lesson')
                    print(f"  Creating content for lesson: {lesson_title}")
                    
                    # Generate comprehensive content for this lesson
                    content_items = create_comprehensive_content(lesson_id, lesson_title)
                    
                    # Create each content item
                    for content_item in content_items:
                        success, content_id = self.create_content(
                            lesson_id=content_item['lesson_id'],
                            content_order=content_item['content_order'],
                            content=content_item['content'],
                            content_type=content_item['content_type']
                        )
                        if success:
                            total_content_created += 1
                        else:
                            print(f"    ✗ Failed to create content: {content_id}")
                    
                    print(f"    ✓ Created {len(content_items)} content items for {lesson_title}")
                else:
                    print(f"  ✗ Could not find lesson details for {lesson_id}")
        
        print(f"\n✅ Content creation completed! Total content items created: {total_content_created}")

    def initialize_enrollment_data(self):
        """Initialize sample enrollment and progress data"""
        try:
            # Get all users and courses
            users = self.get_all_users()
            courses = self.get_all_courses()
            
            print(f"Found {len(users)} users and {len(courses)} courses")
            
            if not users or not courses:
                print("No users or courses found. Initialize users and courses first.")
                return
            
            # Remove duplicate courses by course_name to get unique courses only
            unique_courses = []
            seen_names = set()
            for course in courses:
                if course['course_name'] not in seen_names:
                    unique_courses.append(course)
                    seen_names.add(course['course_name'])
            
            print(f"Using {len(unique_courses)} unique courses for enrollment")
            for i, course in enumerate(unique_courses):
                print(f"  {i}: {course['course_name']}")
            
            # Create enrollments for users using unique courses
            enrollment_patterns = [
                # User 0 (admin) - enrolled in 2 courses
                {"user_idx": 0, "course_idx": 0, "status": "Learning"},
                {"user_idx": 0, "course_idx": 1, "status": "Complete"},
                
                # User 1 (user1) - enrolled in 3 courses
                {"user_idx": 1, "course_idx": 0, "status": "Complete"},
                {"user_idx": 1, "course_idx": 1, "status": "Learning"},
                {"user_idx": 1, "course_idx": 2, "status": "Learning"},
                
                # User 2 (user2) - enrolled in 2 courses
                {"user_idx": 2, "course_idx": 1, "status": "Learning"},
                {"user_idx": 2, "course_idx": 3, "status": "Learning"} if len(unique_courses) > 3 else {"user_idx": 2, "course_idx": 2, "status": "Learning"},
            ]
            
            created_enrollments = []
            
            for pattern in enrollment_patterns:
                if pattern["user_idx"] < len(users) and pattern["course_idx"] < len(unique_courses):
                    user = users[pattern["user_idx"]]
                    course = unique_courses[pattern["course_idx"]]
                    
                    print(f"Attempting to enroll {user['username']} in {course['course_name']}")
                    
                    success, result = self.create_enrollment(
                        user["user_id"], 
                        course["course_id"], 
                        pattern["status"]
                    )
                    
                    if success:
                        created_enrollments.append({
                            "user_id": user["user_id"],
                            "course_id": course["course_id"],
                            "status": pattern["status"]
                        })
                        print(f"✓ Created enrollment: {user['username']} -> {course['course_name']} ({pattern['status']})")
                    else:
                        print(f"✗ Failed to create enrollment: {result}")
                else:
                    print(f"Skipping pattern {pattern} - index out of range")
            
            print(f"Created {len(created_enrollments)} enrollments")
            
            # Create progress data for enrolled users
            for enrollment in created_enrollments:
                user_id = enrollment["user_id"]
                course_id = enrollment["course_id"]
                status = enrollment["status"]
                
                # Get lessons for this course
                lessons = self.get_lessons_by_course_id(course_id)
                print(f"Creating progress for {len(lessons)} lessons in course {course_id}")
                
                if status == "Complete":
                    # If course is complete, mark all lessons as complete
                    for lesson in lessons:
                        success, result = self.create_progress(
                            user_id, course_id, lesson["lesson_id"], "Complete"
                        )
                        if success:
                            print(f"Created progress: Course complete - Lesson {lesson['lesson_title']}")
                            
                elif status == "Learning":
                    # If course is in progress, randomly assign progress to lessons
                    import random
                    completed_count = random.randint(1, max(1, len(lessons) - 1))
                    
                    for i, lesson in enumerate(lessons):
                        lesson_status = "Complete" if i < completed_count else "Learning"
                        success, result = self.create_progress(
                            user_id, course_id, lesson["lesson_id"], lesson_status
                        )
                        if success:
                            print(f"Created progress: Lesson {lesson['lesson_title']} - {lesson_status}")
            
            print("Enrollment and progress data initialization completed!")
            
        except Exception as e:
            print(f"Error initializing enrollment data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Enrollment methods
    def create_enrollment(self, user_id, course_id, status="Learning"):
        """Create a new enrollment in the database"""
        try:
            # Check if enrollment already exists
            existing_enrollment = self.get_enrollment(user_id, course_id)
            if existing_enrollment:
                return False, "User already enrolled in this course"
            
            enroll_id = str(uuid.uuid4())
            enrollment_data = {
                "enroll_id": enroll_id,
                "user_id": user_id,
                "course_id": course_id,
                "enroll_date": datetime.now().isoformat(),
                "status": status,
                "complete_date": ""  # Use empty string instead of None
            }
            
            self.enrollments_collection.add(
                documents=[f"Enrollment: User {user_id} Course {course_id} Status: {status}"],
                metadatas=[enrollment_data],
                ids=[enroll_id]
            )
            
            return True, enroll_id
        except Exception as e:
            return False, f"Error creating enrollment: {str(e)}"
    
    def get_enrollment(self, user_id, course_id):
        """Get enrollment by user_id and course_id"""
        try:
            results = self.enrollments_collection.query(
                query_texts=[f"User {user_id} Course {course_id}"],
                n_results=1,
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}]}
            )
            
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                return results['metadatas'][0][0]
            return None
        except Exception as e:
            print(f"Error getting enrollment: {str(e)}")
            return None
    
    def get_enrollments_by_user(self, user_id):
        """Get all enrollments for a specific user"""
        try:
            results = self.enrollments_collection.query(
                query_texts=[f"User: {user_id}"],
                n_results=100,
                where={"user_id": user_id}
            )
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting enrollments: {str(e)}")
            return []
    
    def get_enrollments_by_course(self, course_id):
        """Get all enrollments for a specific course"""
        try:
            results = self.enrollments_collection.query(
                query_texts=[f"Course {course_id}"],
                n_results=100,
                where={"course_id": course_id}
            )
            
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting course enrollments: {str(e)}")
            return []
    
    def update_enrollment_status(self, user_id, course_id, status, complete_date=None):
        """Update enrollment status"""
        try:
            enrollment = self.get_enrollment(user_id, course_id)
            if not enrollment:
                return False, "Enrollment not found"
            
            # Update enrollment data
            enrollment['status'] = status
            if status == "Complete" and complete_date:
                enrollment['complete_date'] = complete_date
            elif status == "Complete":
                enrollment['complete_date'] = datetime.now().isoformat()
            
            # Delete old entry and add updated one
            self.enrollments_collection.delete(ids=[enrollment['enroll_id']])
            self.enrollments_collection.add(
                documents=[f"Enrollment: User {user_id} Course {course_id} Status: {status}"],
                metadatas=[enrollment],
                ids=[enrollment['enroll_id']]
            )
            
            return True, "Enrollment status updated"
        except Exception as e:
            return False, f"Error updating enrollment: {str(e)}"
    
    # Progress tracking methods
    def create_progress(self, user_id, course_id, lesson_id, status="Learning"):
        """Create or update progress for a lesson"""
        try:
            # Check if progress already exists
            existing_progress = self.get_progress(user_id, course_id, lesson_id)
            if existing_progress:
                return self.update_progress_status(user_id, course_id, lesson_id, status)
            
            progress_id = str(uuid.uuid4())
            progress_data = {
                "progress_id": progress_id,
                "user_id": user_id,
                "course_id": course_id,
                "lesson_id": lesson_id,
                "status": status
            }
            
            self.progress_collection.add(
                documents=[f"Progress: User {user_id} Course {course_id} Lesson {lesson_id} Status: {status}"],
                metadatas=[progress_data],
                ids=[progress_id]
            )
            
            return True, progress_id
        except Exception as e:
            return False, f"Error creating progress: {str(e)}"
    
    def get_progress(self, user_id, course_id, lesson_id):
        """Get progress for a specific lesson"""
        try:
            results = self.progress_collection.query(
                query_texts=[f"User {user_id} Course {course_id} Lesson {lesson_id}"],
                n_results=1,
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}, {"lesson_id": lesson_id}]}
            )
            
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                return results['metadatas'][0][0]
            return None
        except Exception as e:
            print(f"Error getting progress: {str(e)}")
            return None
    
    def get_progress_by_user_course(self, user_id, course_id):
        """Get all progress for a user in a specific course"""
        try:
            results = self.progress_collection.query(
                query_texts=[f"User {user_id} Course {course_id}"],
                n_results=100,
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}]}
            )
            
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting user course progress: {str(e)}")
            return []
    
    def update_progress_status(self, user_id, course_id, lesson_id, status):
        """Update progress status for a lesson"""
        try:
            progress = self.get_progress(user_id, course_id, lesson_id)
            if not progress:
                return False, "Progress not found"
            
            # Update progress data
            progress['status'] = status
            
            # Delete old entry and add updated one
            self.progress_collection.delete(ids=[progress['progress_id']])
            self.progress_collection.add(
                documents=[f"Progress: User {user_id} Course {course_id} Lesson {lesson_id} Status: {status}"],
                metadatas=[progress],
                ids=[progress['progress_id']]
            )
            
            return True, "Progress status updated"
        except Exception as e:
            return False, f"Error updating progress: {str(e)}"
    
    def get_course_progress_summary(self, user_id, course_id):
        """Get progress summary for a course"""
        try:
            # Get all lessons in the course
            lessons = self.get_lessons_by_course_id(course_id)
            total_lessons = len(lessons)
            
            if total_lessons == 0:
                return {"total_lessons": 0, "completed_lessons": 0, "progress_percentage": 0}
            
            # Get user's progress for this course
            progress_records = self.get_progress_by_user_course(user_id, course_id)
            completed_lessons = sum(1 for p in progress_records if p['status'] == 'Complete')
            
            progress_percentage = (completed_lessons / total_lessons) * 100
            
            return {
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress_percentage": round(progress_percentage, 2)
            }
        except Exception as e:
            print(f"Error getting course progress summary: {str(e)}")
            return {"total_lessons": 0, "completed_lessons": 0, "progress_percentage": 0}

    # Quiz methods
    def create_quiz(self, quiz_id=None, course_id=None, quiz_title=None, status="active", description="", difficulty_level="Regular"):
        """Create a new quiz in the database"""
        try:
            if quiz_id is None:
                quiz_id = str(uuid.uuid4())
            else:
                quiz_id = quiz_id
            quiz_data = {
                "quiz_id": quiz_id,
                "course_id": course_id,
                "quiz_title": quiz_title,
                "status": status,
                "description": description,
                "difficulty_level": difficulty_level
            }
            self.quiz_collection.add(
                documents=[f"Quiz: {quiz_title} Course: {course_id}"],
                metadatas=[quiz_data],
                ids=[quiz_id]
            )
            return True, quiz_id
        except Exception as e:
            return False, f"Error creating quiz: {str(e)}"

    def get_quiz_by_course_id(self, course_id):
        """Get quiz by course_id"""
        try:
            results = self.quiz_collection.query(
                query_texts=[f"Course: {course_id}"],
                n_results=10,
                where={"course_id": course_id}
            )
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting quiz: {str(e)}")
            return []

    # Question methods
    def create_question(self, question_id=None, quiz_id=None, question_text=None, question_type=None, points=None):
        """Create a new question in the database"""
        try:
            if question_id is None:
                question_id = str(uuid.uuid4())
            else:
                question_id = question_id
            question_data = {
                "question_id": question_id,
                "quiz_id": quiz_id,
                "question_text": question_text,
                "question_type": question_type,
                "points": points
            }
            self.question_collection.add(
                documents=[f"Question: {question_text} Quiz: {quiz_id}"],
                metadatas=[question_data],
                ids=[question_id]
            )
            return True, question_id
        except Exception as e:
            return False, f"Error creating question: {str(e)}"

    def get_questions_by_quiz_id(self, quiz_id):
        """Get all questions for a quiz"""
        try:
            # Use .get() method for exact metadata filtering instead of semantic search
            results = self.question_collection.get(
                where={"quiz_id": quiz_id}
            )
            
            if results['metadatas']:
                return results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting questions: {str(e)}")
            return []

    # Choice methods
    def create_choice(self, choice_id=None, question_id=None, choice_text=None, is_correct=None, question_type="choices"):
        """Create a new choice for a question"""
        try:
            if choice_id is None:
                choice_id = str(uuid.uuid4())
            else:
                choice_id = choice_id
            choice_data = {
                "choice_id": choice_id,
                "question_id": question_id,
                "choice_text": choice_text,
                "question_type": question_type,
                "is_correct": is_correct
            }
            self.choice_collection.add(
                documents=[f"Choice: {choice_text} Question: {question_id}"],
                metadatas=[choice_data],
                ids=[choice_id]
            )
            return True, choice_id
        except Exception as e:
            return False, f"Error creating choice: {str(e)}"

    def get_choices_by_question_id(self, question_id):
        """Get all choices for a question"""
        try:
            # Use .get() method for exact metadata filtering instead of semantic search
            results = self.choice_collection.get(
                where={"question_id": question_id}
            )
            
            if results['metadatas']:
                return results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting choices: {str(e)}")
            return []

    # Answer methods
    def create_answer(self, answer_id=None, question_id=None, correct_answer=None):
        """Create a new answer for a question"""
        try:
            if answer_id is None:
                answer_id = str(uuid.uuid4())
            else:
                answer_id = answer_id
            answer_data = {
                "answer_id": answer_id,
                "question_id": question_id,
                "correct_answer": correct_answer
            }
            self.answer_collection.add(
                documents=[f"Answer: {correct_answer} Question: {question_id}"],
                metadatas=[answer_data],
                ids=[answer_id]
            )
            return True, answer_id
        except Exception as e:
            return False, f"Error creating answer: {str(e)}"

    def get_answer_by_question_id(self, question_id):
        """Get answer for a question"""
        try:
            # Use .get() method for exact metadata filtering instead of semantic search
            results = self.answer_collection.get(
                where={"question_id": question_id}
            )
            
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            return None
        except Exception as e:
            print(f"Error getting answer: {str(e)}")
            return None

    # ==================== UPLOADED DOCUMENTS MANAGEMENT ====================
    
    def create_uploaded_document(self, document_id, document_name, document_base64, user_id):
        """Store uploaded document once for multiple tasks to reference"""
        try:
            doc_data = {
                "document_id": document_id,
                "document_name": document_name,
                "document_base64": document_base64,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "reference_count": 3  # Initially referenced by 3 tasks (Casual, Regular, Intense)
            }
            
            self.uploaded_documents_collection.add(
                documents=[f"Document: {document_name} User: {user_id}"],
                metadatas=[doc_data],
                ids=[document_id]
            )
            return True, document_id
        except Exception as e:
            return False, f"Error storing document: {str(e)}"
    
    def get_uploaded_document(self, document_id):
        """Get uploaded document by ID"""
        try:
            results = self.uploaded_documents_collection.get(ids=[document_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            return None
        except Exception as e:
            print(f"Error getting uploaded document: {str(e)}")
            return None
    
    def delete_uploaded_document(self, document_id):
        """Delete uploaded document"""
        try:
            self.uploaded_documents_collection.delete(ids=[document_id])
            return True, "Document deleted"
        except Exception as e:
            return False, f"Error deleting document: {str(e)}"
    
    def cleanup_old_documents(self, days_old=7):
        """Clean up documents older than specified days with no active tasks"""
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            results = self.uploaded_documents_collection.get()
            deleted_count = 0
            
            if results['metadatas']:
                for i, metadata in enumerate(results['metadatas']):
                    doc_id = results['ids'][i]
                    created_at = metadata.get('created_at', '')
                    
                    if created_at and created_at < cutoff_date:
                        # Check if any active tasks reference this document
                        tasks = self.get_background_tasks_by_document(doc_id)
                        active_tasks = [t for t in tasks if t.get('status') in ['pending', 'generating']]
                        
                        if not active_tasks:
                            self.delete_uploaded_document(doc_id)
                            deleted_count += 1
            
            return True, f"Cleaned up {deleted_count} old documents"
        except Exception as e:
            return False, f"Error cleaning up documents: {str(e)}"
    
    # ==================== BACKGROUND TASKS MANAGEMENT ====================
    
    def create_background_task(self, task_id, document_id, document_name, difficulty_level, user_id, quiz_params):
        """Create a background task for course generation"""
        try:
            task_data = {
                "task_id": task_id,
                "document_id": document_id,
                "document_name": document_name,
                "difficulty_level": difficulty_level,
                "status": "pending",  # pending, generating, done, error
                "progress": "Queued",  # Progress message
                "progress_percent": 0,
                "user_id": user_id,
                "quiz_params": json.dumps(quiz_params) if isinstance(quiz_params, dict) else quiz_params,
                "result_data": "",
                "error_message": "",
                "retry_count": 0,
                "max_retries": 3,
                "created_at": datetime.now().isoformat(),
                "started_at": "",
                "completed_at": ""
            }
            
            self.background_tasks_collection.add(
                documents=[f"Task: {task_id} Difficulty: {difficulty_level} Status: pending Document: {document_name}"],
                metadatas=[task_data],
                ids=[task_id]
            )
            return True, task_id
        except Exception as e:
            return False, f"Error creating background task: {str(e)}"
    
    def update_background_task(self, task_id, status=None, result_data=None, error_message=None, progress=None, progress_percent=None, retry_count=None):
        """Update background task status and result"""
        try:
            # Get existing task data first
            existing = self.get_background_task(task_id)
            if not existing:
                return False, "Task not found"
            
            update_data = {}
            
            if status:
                update_data["status"] = status
                if status == "generating":
                    update_data["started_at"] = datetime.now().isoformat()
                elif status in ["done", "error", "generated"]:
                    update_data["completed_at"] = datetime.now().isoformat()
            
            if progress:
                update_data["progress"] = progress
            
            if progress_percent is not None:
                update_data["progress_percent"] = progress_percent
            
            if result_data:
                update_data["result_data"] = json.dumps(result_data) if isinstance(result_data, dict) else result_data
            
            if error_message:
                update_data["error_message"] = error_message
            
            if retry_count is not None:
                update_data["retry_count"] = retry_count
            
            # Merge with existing data
            for key, value in existing.items():
                if key not in update_data:
                    if key in ['quiz_params', 'result_data'] and isinstance(value, (dict, list)):
                        update_data[key] = json.dumps(value)
                    else:
                        update_data[key] = value
            
            self.background_tasks_collection.update(
                ids=[task_id],
                metadatas=[update_data],
                documents=[f"Task: {task_id} Difficulty: {update_data.get('difficulty_level', '')} Status: {update_data.get('status', '')}"]
            )
            return True, "Task updated"
        except Exception as e:
            return False, f"Error updating task: {str(e)}"
    
    def get_background_task(self, task_id):
        """Get a single background task by ID"""
        try:
            results = self.background_tasks_collection.get(ids=[task_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                task = results['metadatas'][0].copy()
                # Parse JSON fields
                if task.get('quiz_params') and isinstance(task['quiz_params'], str):
                    try:
                        task['quiz_params'] = json.loads(task['quiz_params'])
                    except:
                        pass
                if task.get('result_data') and isinstance(task['result_data'], str) and task['result_data']:
                    try:
                        task['result_data'] = json.loads(task['result_data'])
                    except:
                        pass
                return task
            return None
        except Exception as e:
            print(f"Error getting background task: {str(e)}")
            return None
    
    def get_background_tasks(self, user_id=None):
        """Get all background tasks, optionally filtered by user"""
        try:
            if user_id:
                results = self.background_tasks_collection.get(
                    where={"user_id": user_id}
                )
            else:
                results = self.background_tasks_collection.get()
            
            tasks = []
            if results['metadatas']:
                for metadata in results['metadatas']:
                    task = metadata.copy()
                    # Parse JSON fields
                    if task.get('quiz_params') and isinstance(task['quiz_params'], str):
                        try:
                            task['quiz_params'] = json.loads(task['quiz_params'])
                        except:
                            pass
                    if task.get('result_data') and isinstance(task['result_data'], str) and task['result_data']:
                        try:
                            task['result_data'] = json.loads(task['result_data'])
                        except:
                            pass
                    tasks.append(task)
            
            # Sort by created_at descending
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return tasks
        except Exception as e:
            print(f"Error getting background tasks: {str(e)}")
            return []
    
    def get_background_tasks_by_document(self, document_id):
        """Get all background tasks for a specific document"""
        try:
            results = self.background_tasks_collection.get(
                where={"document_id": document_id}
            )
            
            tasks = []
            if results['metadatas']:
                for metadata in results['metadatas']:
                    task = metadata.copy()
                    if task.get('quiz_params') and isinstance(task['quiz_params'], str):
                        try:
                            task['quiz_params'] = json.loads(task['quiz_params'])
                        except:
                            pass
                    tasks.append(task)
            return tasks
        except Exception as e:
            print(f"Error getting tasks by document: {str(e)}")
            return []
    
    def get_pending_tasks(self):
        """Get all pending tasks for processing"""
        try:
            results = self.background_tasks_collection.get(
                where={"status": "pending"}
            )
            
            tasks = []
            if results['metadatas']:
                for metadata in results['metadatas']:
                    task = metadata.copy()
                    if task.get('quiz_params') and isinstance(task['quiz_params'], str):
                        try:
                            task['quiz_params'] = json.loads(task['quiz_params'])
                        except:
                            pass
                    tasks.append(task)
            
            # Sort by created_at ascending (oldest first)
            tasks.sort(key=lambda x: x.get('created_at', ''))
            return tasks
        except Exception as e:
            print(f"Error getting pending tasks: {str(e)}")
            return []
    
    def delete_background_task(self, task_id):
        """Delete a background task"""
        try:
            self.background_tasks_collection.delete(ids=[task_id])
            return True, "Task deleted"
        except Exception as e:
            return False, f"Error deleting task: {str(e)}"
    
    def cleanup_old_tasks(self, days_old=7):
        """Clean up completed/error tasks older than specified days"""
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            results = self.background_tasks_collection.get()
            deleted_count = 0
            
            if results['metadatas']:
                for i, metadata in enumerate(results['metadatas']):
                    task_id = results['ids'][i]
                    status = metadata.get('status', '')
                    completed_at = metadata.get('completed_at', '')
                    
                    # Only delete completed or error tasks that are old
                    if status in ['done', 'error'] and completed_at and completed_at < cutoff_date:
                        self.delete_background_task(task_id)
                        deleted_count += 1
            
            return True, f"Cleaned up {deleted_count} old tasks"
        except Exception as e:
            return False, f"Error cleaning up tasks: {str(e)}"
    
    def increment_retry_count(self, task_id):
        """Increment retry count for a task and return if retries are available"""
        try:
            task = self.get_background_task(task_id)
            if not task:
                return False, "Task not found"
            
            current_retries = task.get('retry_count', 0)
            max_retries = task.get('max_retries', 3)
            
            if current_retries >= max_retries:
                return False, "Max retries exceeded"
            
            self.update_background_task(
                task_id, 
                status="pending", 
                retry_count=current_retries + 1,
                progress="Retrying...",
                progress_percent=0,
                error_message=""
            )
            return True, f"Retry {current_retries + 1}/{max_retries}"
        except Exception as e:
            return False, f"Error incrementing retry: {str(e)}"

    def initialize_quiz_data(self):
        """Initialize quizzes, questions, choices, and answers for each course"""
        print("\n4. Creating quizzes, questions, choices, and answers for each course...")
        courses = self.get_all_courses()
        for course in courses:
            quiz_title = f"Quiz for {course['course_name']}"
            status = "active"
            description = f"Auto-generated quiz for {course['course_name']}"
            difficulty_level = course.get('difficulty_level', 'Regular')
            success, quiz_id = self.create_quiz(course_id=course['course_id'], quiz_title=quiz_title, status=status, description=description, difficulty_level=difficulty_level)
            if not success:
                print(f"  ✗ Failed to create quiz for {course['course_name']}: {quiz_id}")
                continue
            print(f"  ✓ Created quiz for {course['course_name']}")
            # 10 multiple choice questions
            for i in range(10):
                q_text = f"What is the answer to MCQ {i+1} for {course['course_name']}?"
                success, question_id = self.create_question(quiz_id=quiz_id, question_text=q_text, question_type="choices", points=1)
                if not success:
                    print(f"    ✗ Failed to create MCQ question: {question_id}")
                    continue
                # 4 choices per question, 1 correct
                correct_index = i % 4
                for j in range(4):
                    choice_text = f"Choice {chr(65+j)} for MCQ {i+1}"
                    is_correct = (j == correct_index)
                    self.create_choice(question_id=question_id, choice_text=choice_text, is_correct=is_correct, question_type="choices")
            # 5 subjective questions
            for i in range(5):
                q_text = f"Describe the concept for Subjective Q{i+1} in {course['course_name']}?"
                success, question_id = self.create_question(quiz_id=quiz_id, question_text=q_text, question_type="subjective", points=2)
                if not success:
                    print(f"    ✗ Failed to create subjective question: {question_id}")
                    continue
                # Add a sample answer
                self.create_answer(question_id=question_id, correct_answer=f"Sample answer for Subjective Q{i+1}")
            # 5 fill-in-the-blank questions
            for i in range(5):
                q_text = f"Fill in the blank: ____ is important in {course['course_name']} (Q{i+1})"
                success, question_id = self.create_question(quiz_id=quiz_id, question_text=q_text, question_type="fill", points=2)
                if not success:
                    print(f"    ✗ Failed to create fill-in-the-blank question: {question_id}")
                    continue
                # Add a correct answer
                self.create_answer(question_id=question_id, correct_answer=f"Correct answer {i+1}")
        print("Quiz/question/choice/answer data initialization completed!")

    # Quiz Score methods
    def create_quiz_score(self, user_id, course_id, quiz_id, score, total_points, answers):
        """Create a new quiz score record"""
        try:
            # Check if user already took the quiz
            existing_score = self.get_quiz_score(user_id, course_id, quiz_id)
            if existing_score:
                return False, "User has already taken this quiz"
            
            score_id = str(uuid.uuid4())
            score_data = {
                "score_id": score_id,
                "user_id": user_id,
                "course_id": course_id,
                "quiz_id": quiz_id,
                "score": score,
                "total_points": total_points,
                "answers": json.dumps(answers),
                "taken_at": datetime.now().isoformat()
            }
            
            self.quiz_score_collection.add(
                documents=[f"Quiz Score: User {user_id} Course {course_id} Quiz {quiz_id}"],
                metadatas=[score_data],
                ids=[score_id]
            )
            
            return True, score_id
        except Exception as e:
            return False, f"Error creating quiz score: {str(e)}"
    
    def get_quiz_score(self, user_id, course_id, quiz_id):
        """Get quiz score for a specific user, course and quiz"""
        try:
            # Use .get() method for exact metadata filtering instead of semantic search
            results = self.quiz_score_collection.get(
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}, {"quiz_id": quiz_id}]}
            )
            
            if results['metadatas'] and len(results['metadatas']) > 0:
                score = self._parse_quiz_score_metadata(results['metadatas'][0])
                return score
            return None
        except Exception as e:
            print(f"Error getting quiz score: {str(e)}")
            return None

    def _parse_quiz_score_metadata(self, meta):
        """Parse quiz score metadata (JSON strings to objects)"""
        score = dict(meta)
        if 'answers' in score and isinstance(score.get('answers'), str):
            try:
                score['answers'] = json.loads(score['answers']) if score['answers'] else []
            except:
                score['answers'] = []
        if 'strengths' in score and isinstance(score.get('strengths'), str):
            try:
                score['strengths'] = json.loads(score['strengths']) if score['strengths'] else []
            except:
                score['strengths'] = []
        if 'weaknesses' in score and isinstance(score.get('weaknesses'), str):
            try:
                score['weaknesses'] = json.loads(score['weaknesses']) if score['weaknesses'] else []
            except:
                score['weaknesses'] = []
        if 'related_lessons' in score and isinstance(score.get('related_lessons'), str):
            try:
                score['related_lessons'] = json.loads(score['related_lessons']) if score['related_lessons'] else []
            except:
                score['related_lessons'] = []
        if 'intensive_lessons' in score and isinstance(score.get('intensive_lessons'), str):
            try:
                score['intensive_lessons'] = json.loads(score['intensive_lessons']) if score['intensive_lessons'] else []
            except:
                score['intensive_lessons'] = []
        if 'related_lessons_for_improvement' in score and isinstance(score.get('related_lessons_for_improvement'), str):
            try:
                score['related_lessons_for_improvement'] = json.loads(score['related_lessons_for_improvement']) if score['related_lessons_for_improvement'] else []
            except:
                score['related_lessons_for_improvement'] = []
        return score

    def update_quiz_score_analysis(self, score_id, analysis):
        """Update quiz score record with analysis (strengths, weaknesses, intensive_lessons, related_lessons_for_improvement)"""
        try:
            results = self.quiz_score_collection.get(ids=[score_id])
            if not results['metadatas'] or len(results['metadatas']) == 0:
                return False
            existing = results['metadatas'][0]
            updated = dict(existing)
            updated['strengths'] = json.dumps(analysis.get('strengths', []))
            updated['weaknesses'] = json.dumps(analysis.get('weaknesses', []))
            updated['intensive_lessons'] = json.dumps(analysis.get('intensive_lessons', []))
            updated['related_lessons_for_improvement'] = json.dumps(analysis.get('related_lessons_for_improvement', []))
            doc = results.get('documents', [[]])
            doc_text = doc[0] if isinstance(doc[0], str) else (doc[0][0] if doc else f"Quiz Score: {score_id}")
            self.quiz_score_collection.update(
                ids=[score_id],
                metadatas=[updated],
                documents=[doc_text]
            )
            return True
        except Exception as e:
            print(f"Error updating quiz score analysis: {str(e)}")
            return False
    
    def get_quiz_scores_by_user_course(self, user_id, course_id):
        """Get all quiz scores for a user in a specific course"""
        try:
            results = self.quiz_score_collection.query(
                query_texts=[f"User {user_id} Course {course_id}"],
                n_results=100,
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}]}
            )
            
            if results['metadatas']:
                scores = [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
                # Parse JSON strings back to lists for all scores
                for score in scores:
                    if 'answers' in score:
                        score['answers'] = json.loads(score['answers'])
                return scores
            return []
        except Exception as e:
            print(f"Error getting user course quiz scores: {str(e)}")
            return []

    def save_recommendation_courses(self, user_id, course_ids):
        """Save or replace recommendation courses for a user (from quiz recommendations)"""
        try:
            doc_id = f"rec_{user_id}"
            try:
                self.user_recommendation_courses_collection.delete(ids=[doc_id])
            except Exception:
                pass  # Document may not exist yet
            self.user_recommendation_courses_collection.add(
                ids=[doc_id],
                documents=[f"Recommendation courses for user {user_id}"],
                metadatas=[{"user_id": user_id, "course_ids": json.dumps(list(course_ids))}]
            )
            return True
        except Exception as e:
            print(f"Error saving recommendation courses: {str(e)}")
            return False

    def get_recommendation_courses(self, user_id):
        """Get saved recommendation course IDs for a user"""
        try:
            doc_id = f"rec_{user_id}"
            results = self.user_recommendation_courses_collection.get(ids=[doc_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                meta = results['metadatas'][0]
                ids_json = meta.get('course_ids', '[]')
                return json.loads(ids_json) if isinstance(ids_json, str) else ids_json
            return []
        except Exception as e:
            print(f"Error getting recommendation courses: {str(e)}")
            return []

    def get_users_by_role(self, role):
        """Get all users with a specific role"""
        try:
            results = self.users_collection.query(
                query_texts=[f"Role: {role}"],
                n_results=100,
                where={"role": role}
            )
            return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
        except Exception as e:
            print(f"Error getting users by role: {str(e)}")
            return []

    def update_user_role(self, email, new_role):
        """Update a user's role"""
        try:
            user = self.get_user_by_email(email)
            if not user:
                return False, "User not found"
            
            # Update user data
            user['role'] = new_role
            
            # Delete old entry and add updated one
            self.users_collection.delete(ids=[user['user_id']])
            self.users_collection.add(
                documents=[f"User: {user['username']} Email: {email} Role: {new_role}"],
                metadatas=[user],
                ids=[user['user_id']]
            )
            
            return True, "User role updated successfully"
        except Exception as e:
            return False, f"Error updating user role: {str(e)}"

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            results = self.users_collection.get(ids=[user_id])
            if results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0]
            return None
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None

    def get_enrollments_by_course_id(self, course_id):
        """Get all enrollments for a specific course"""
        try:
            results = self.enrollments_collection.query(
                query_texts=[f"Course: {course_id}"],
                n_results=100,
                where={"course_id": course_id}
            )
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting enrollments: {str(e)}")
            return []

    def get_quiz_scores_by_quiz_id(self, quiz_id):
        """Get all quiz scores for a specific quiz"""
        try:
            results = self.quiz_score_collection.query(
                query_texts=[f"Quiz: {quiz_id}"],
                n_results=100,
                where={"quiz_id": quiz_id}
            )
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting quiz scores: {str(e)}")
            return []

    def get_quiz_score_by_user_and_quiz(self, user_id, quiz_id):
        """Get quiz score for a specific user and quiz (fix ChromaDB where clause limitation)"""
        try:
            # Query by user_id only
            results = self.quiz_score_collection.query(
                query_texts=[f"User: {user_id}"],
                n_results=10,
                where={"user_id": user_id}
            )
            # Now filter in Python for quiz_id
            if results['metadatas']:
                all_scores = [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
                for score in all_scores:
                    if score.get('quiz_id') == quiz_id:
                        return score
                    
            
            return None
        except Exception as e:
            print(f"Error getting quiz score: {str(e)}")
            return None

    def update_user_auth_status(self, user_id, is_auth=True):
        """Update user's authentication status"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Update user data
            user['is_auth'] = is_auth
            
            # Delete old entry and add updated one
            self.users_collection.delete(ids=[user_id])
            self.users_collection.add(
                documents=[f"User: {user['username']} Email: {user['email']} Role: {user['role']}"],
                metadatas=[user],
                ids=[user_id]
            )
            
            return True, "User auth status updated successfully"
        except Exception as e:
            return False, f"Error updating user auth status: {str(e)}"

    def update_user_profile(self, user_id, username, full_name, password=None):
        """Update user's profile information"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Update user data
            user['username'] = username
            user['full_name'] = full_name
            user['is_auth'] = True  # Mark as authenticated after profile update
            
            if password:
                user['password'] = self.hash_password(password)
            
            # Delete old entry and add updated one
            self.users_collection.delete(ids=[user_id])
            self.users_collection.add(
                documents=[f"User: {username} Email: {user['email']} Role: {user['role']}"],
                metadatas=[user],
                ids=[user_id]
            )
            
            return True, "User profile updated successfully"
        except Exception as e:
            return False, f"Error updating user profile: {str(e)}"

    # Delete methods
    def delete_course(self, course_id):
        """Delete a course by ID"""
        try:
            self.courses_collection.delete(ids=[course_id])
            return True, "Course deleted successfully"
        except Exception as e:
            return False, f"Error deleting course: {str(e)}"
    
    def delete_lesson(self, lesson_id):
        """Delete a lesson by ID"""
        try:
            self.lessons_collection.delete(ids=[lesson_id])
            return True, "Lesson deleted successfully"
        except Exception as e:
            return False, f"Error deleting lesson: {str(e)}"
    
    def delete_content(self, content_id):
        """Delete content by ID"""
        try:
            self.content_collection.delete(ids=[content_id])
            return True, "Content deleted successfully"
        except Exception as e:
            return False, f"Error deleting content: {str(e)}"
    
    def delete_quiz(self, quiz_id):
        """Delete a quiz by ID"""
        try:
            self.quiz_collection.delete(ids=[quiz_id])
            return True, "Quiz deleted successfully"
        except Exception as e:
            return False, f"Error deleting quiz: {str(e)}"
    
    def delete_question(self, question_id):
        """Delete a question by ID"""
        try:
            self.question_collection.delete(ids=[question_id])
            return True, "Question deleted successfully"
        except Exception as e:
            return False, f"Error deleting question: {str(e)}"
    
    def delete_choice(self, choice_id):
        """Delete a choice by ID"""
        try:
            self.choice_collection.delete(ids=[choice_id])
            return True, "Choice deleted successfully"
        except Exception as e:
            return False, f"Error deleting choice: {str(e)}"
    
    def delete_answer(self, answer_id):
        """Delete an answer by ID"""
        try:
            self.answer_collection.delete(ids=[answer_id])
            return True, "Answer deleted successfully"
        except Exception as e:
            return False, f"Error deleting answer: {str(e)}"
    
    def delete_quiz_score(self, quiz_score_id):
        """Delete a quiz score by ID"""
        try:
            self.quiz_score_collection.delete(ids=[quiz_score_id])
            return True, "Quiz score deleted successfully"
        except Exception as e:
            return False, f"Error deleting quiz score: {str(e)}"
    
    def get_quiz_scores_by_user(self, user_id):
        """Get all quiz scores for a user"""
        try:
            results = self.quiz_score_collection.get(
                where={"user_id": user_id}
            )
            if results and results.get('ids'):
                return list(zip(results['ids'], results.get('metadatas', [])))
            return []
        except Exception as e:
            print(f"Error getting quiz scores by user: {str(e)}")
            return []

    def get_progress_by_user(self, user_id):
        """Get all progress records for a user"""
        try:
            results = self.progress_collection.get(
                where={"user_id": user_id}
            )
            if results and results.get('ids'):
                return results['ids']
            return []
        except Exception as e:
            print(f"Error getting progress by user: {str(e)}")
            return []

    def delete_user(self, user_id):
        """Delete a user and all related data (enrollments, progress, quiz scores)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            # 1. Delete quiz scores
            score_records = self.get_quiz_scores_by_user(user_id)
            for score_id, _ in score_records:
                try:
                    self.quiz_score_collection.delete(ids=[score_id])
                except Exception as e:
                    print(f"Warning: Error deleting quiz score {score_id}: {str(e)}")

            # 2. Delete progress records
            progress_ids = self.get_progress_by_user(user_id)
            for progress_id in progress_ids:
                try:
                    self.progress_collection.delete(ids=[progress_id])
                except Exception as e:
                    print(f"Warning: Error deleting progress {progress_id}: {str(e)}")

            # 3. Delete enrollments
            enrollments = self.get_enrollments_by_user(user_id)
            for enroll in enrollments:
                enroll_id = enroll.get('enroll_id') if isinstance(enroll, dict) else None
                if enroll_id:
                    try:
                        self.enrollments_collection.delete(ids=[enroll_id])
                    except Exception as ex:
                        print(f"Warning: Error deleting enrollment {enroll_id}: {str(ex)}")

            # 4. Delete recommendation courses if any
            try:
                doc_id = f"rec_{user_id}"
                self.user_recommendation_courses_collection.delete(ids=[doc_id])
            except Exception:
                pass

            # 5. Delete user
            self.users_collection.delete(ids=[user_id])
            return True, "User deleted successfully"
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"

    def delete_enrollment(self, enrollment_id):
        """Delete an enrollment by ID"""
        try:
            self.enrollments_collection.delete(ids=[enrollment_id])
            return True, "Enrollment deleted successfully"
        except Exception as e:
            return False, f"Error deleting enrollment: {str(e)}"
    
    def delete_progress(self, progress_id):
        """Delete a progress record by ID"""
        try:
            self.progress_collection.delete(ids=[progress_id])
            return True, "Progress deleted successfully"
        except Exception as e:
            return False, f"Error deleting progress: {str(e)}"
    
    def get_progress_by_user_and_course(self, user_id, course_id):
        """Get all progress records for a user in a specific course"""
        try:
            results = self.progress_collection.query(
                query_texts=[f"User {user_id} Course {course_id}"],
                n_results=100,
                where={"$and": [{"user_id": user_id}, {"course_id": course_id}]}
            )
            
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting progress records: {str(e)}")
            return []
    def add_vector(self, course_id, lesson_id, content_vector):
        """Add a vector to the vector collection"""
        try:
            self.vector_collection.add(
                documents=[content_vector],
                metadatas=[{'course_id': course_id, 'lesson_id': lesson_id}],
                ids=[lesson_id]
            )
        except Exception as e:
            print(f"Error adding vector: {str(e)}")
            return False
    def get_vector(self, course_id):
        """Get a vector from the vector collection"""
        try:
            results = self.vector_collection.query(
                query_texts=[f"*"],
                where={"course_id": course_id}
            )
            if results['documents']:
                return results['documents']
            return None
        except Exception as e:
            print(f"Error getting vector: {str(e)}")
            return None
    def delete_vector(self, course_id, lesson_id):
        """Delete a vector from the vector collection"""
        try:
            self.vector_collection.delete(ids=[lesson_id])
            return True
        except Exception as e:
            print(f"Error deleting vector: {str(e)}")
            return False

    def _normalize_title(self, t: str) -> str:
        """Normalize lesson title for flexible matching (lowercase, collapse spaces)"""
        if not t:
            return ''
        return ' '.join(str(t).lower().strip().split())

    def get_lessons_same_title_different_course(self, course_id: str, limit: int = 3):
        """
        Find lessons with same/similar lesson_title in sibling courses (same base name, different difficulty).
        Used for "Intensive Lessons" - same content, different difficulty level.
        Uses: 1) exact title match, 2) normalized match, 3) lesson_order match for sibling courses.
        Returns list of dicts with lesson_id, course_id, lesson_title, course_name.
        """
        try:
            current_course = self.get_course_by_id(course_id)
            if not current_course:
                return []
            our_lessons = self.get_lessons_by_course_id(course_id)
            if not our_lessons:
                return []

            # Find sibling courses: same base name (e.g. "Data Security") but different difficulty
            course_name = current_course.get('course_name', '')
            base_name = course_name
            for suffix in [' (Casual)', ' (Regular)', ' (Intense)']:
                if course_name.endswith(suffix):
                    base_name = course_name[:-len(suffix)].strip()
                    break

            all_courses = self.get_all_courses()
            sibling_course_ids = [
                c['course_id'] for c in all_courses
                if c.get('course_id') != course_id
                and (c.get('course_name', '') == course_name or
                     c.get('course_name', '').startswith(base_name + ' ('))
            ]

            if not sibling_course_ids:
                # Fallback: try exact title match in any other course
                sibling_course_ids = [c['course_id'] for c in all_courses if c.get('course_id') != course_id]

            if not sibling_course_ids:
                return []

            # Get all lessons from sibling courses
            sibling_lessons = []
            for sid in sibling_course_ids:
                sibling_lessons.extend(self.get_lessons_by_course_id(sid) or [])

            our_by_normalized = {self._normalize_title(l.get('lesson_title', '')): l for l in our_lessons}
            our_by_order = {l.get('lesson_order'): l for l in our_lessons if l.get('lesson_order') is not None}

            found = []
            seen = set()

            def add_if_new(lesson, course_obj):
                lid = lesson.get('lesson_id')
                cid = lesson.get('course_id')
                if not lid or not cid or (lid, cid) in seen:
                    return
                seen.add((lid, cid))
                found.append({
                    'lesson_id': lid,
                    'course_id': cid,
                    'lesson_title': lesson.get('lesson_title', 'Unknown'),
                    'course_name': course_obj.get('course_name', 'Unknown')
                })

            for sl in sibling_lessons:
                if len(found) >= limit:
                    break
                cid = sl.get('course_id')
                course_obj = self.get_course_by_id(cid) if cid else None
                if not course_obj:
                    continue

                norm_title = self._normalize_title(sl.get('lesson_title', ''))
                if not norm_title:
                    continue

                # Match 1: exact normalized title
                if norm_title in our_by_normalized:
                    add_if_new(sl, course_obj)
                    continue

                # Match 2: same lesson_order (structure preserved across difficulties)
                lo = sl.get('lesson_order')
                if lo is not None and lo in our_by_order:
                    add_if_new(sl, course_obj)
                    continue

                # Match 3: one title contains the other (e.g. "Introduction" vs "Introduction to Security")
                for our_norm, our_lesson in our_by_normalized.items():
                    if our_norm and (norm_title in our_norm or our_norm in norm_title):
                        add_if_new(sl, course_obj)
                        break

            return found
        except Exception as e:
            print(f"Error in get_lessons_same_title_different_course: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def query_similar_lessons(self, query_text: str, n_results: int = 10):
        """
        Query vector collection for lessons semantically similar to the query text.
        Returns list of dicts with lesson_id, course_id, and optionally lesson/course info.
        """
        try:
            if not query_text or not query_text.strip():
                return []
            results = self.vector_collection.query(
                query_texts=[query_text.strip()],
                n_results=min(n_results, 20),
                include=["metadatas", "distances"]
            )
            if not results or not results.get('ids') or not results['ids'][0]:
                return []
            ids = results['ids'][0]
            metadatas = results.get('metadatas', [[]])[0]
            lessons = []
            seen = set()
            for i, lid in enumerate(ids):
                if lid in seen:
                    continue
                meta = metadatas[i] if i < len(metadatas) else {}
                course_id = meta.get('course_id')
                lesson_id = meta.get('lesson_id') or lid
                if course_id and lesson_id:
                    seen.add(lid)
                    lessons.append({
                        'lesson_id': lesson_id,
                        'course_id': course_id
                    })
            return lessons
        except Exception as e:
            print(f"Error querying similar lessons: {str(e)}")
            return []

# Global database instance
db = DatabaseManager()
