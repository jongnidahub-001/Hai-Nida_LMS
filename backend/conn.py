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
        
        # Get or create the enrollments collection
        try:
            self.enrollments_collection = self.client.get_collection("enrollments")
        except:
            self.enrollments_collection = self.client.create_collection("enrollments")
        
        # Get or create the progress collection
        try:
            self.progress_collection = self.client.get_collection("progress")
        except:
            self.progress_collection = self.client.create_collection("progress")
    
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
    def create_course(self, course_name, description, total_hour, status="Active", difficulty_level="Regular", learning_objectives=None, prerequisites=None):
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
    def create_lesson(self, course_id, lesson_title, duration_hours, lesson_order, description="", what_you_will_learn=None):
        """Create a new lesson in the database"""
        try:
            lesson_id = str(uuid.uuid4())
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
                course['course_name'],
                course['description'],
                course['total_hour'],
                course['status'],
                course['difficulty_level'],
                course['learning_objectives'],
                course['prerequisites']
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
                    course_id,
                    lesson['lesson_title'],
                    lesson['duration_hours'],
                    lesson['lesson_order'],
                    lesson['description'],
                    lesson['what_you_will_learn']
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
                            content_item['lesson_id'],
                            content_item['content_order'],
                            content_item['content'],
                            content_item['content_type']
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
                query_texts=[f"User {user_id}"],
                n_results=100,
                where={"user_id": user_id}
            )
            
            if results['metadatas']:
                return [item for sublist in results['metadatas'] for item in sublist] if isinstance(results['metadatas'][0], list) else results['metadatas']
            return []
        except Exception as e:
            print(f"Error getting user enrollments: {str(e)}")
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

# Global database instance
db = DatabaseManager()
