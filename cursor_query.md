# ออกแบบฐานข้อมูลสำหรับการ query
_Exported on 6/7/2025 at 18:25:07 GMT+7 from Cursor (1.0.0)_

---

**User**

ถ้าจะ query ข้อมูลมาแสดงรายละเอียดแบนี้ ควร design database ยังไง

---

**Cursor**

ฉันจะช่วยคุณออกแบบฐานข้อมูลสำหรับข้อมูลคอร์สการเรียนที่แสดงในภาพ ขอให้ฉันดูโครงสร้างโปรเจกต์ปัจจุบันก่อนเพื่อเข้าใจบริบท

จากการศึกษาโครงสร้างโปรเจกต์ปัจจุบัน พบว่าใช้ ChromaDB เป็นฐานข้อมูลหลัก ซึ่งเป็น vector database สำหรับข้อมูลคอร์สการเรียนที่แสดงในภาพ ฉันขอแนะนำการออกแบบฐานข้อมูลดังนี้:

## การออกแบบฐานข้อมูลสำหรับระบบคอร์สการเรียน

### 1. Collections ที่ควรมี:

```python
# เพิ่มใน conn.py
class DatabaseManager:
    def __init__(self):
        # ... existing code ...
        
        # Initialize course-related collections
        self.courses_collection = self._get_or_create_collection("courses")
        self.enrollments_collection = self._get_or_create_collection("enrollments")
        self.progress_collection = self._get_or_create_collection("progress")
        self.lessons_collection = self._get_or_create_collection("lessons")
    
    def _get_or_create_collection(self, name):
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(name)
```

### 2. โครงสร้างข้อมูล:

#### **Courses Collection**
```python
course_data = {
    "course_id": "course_001",
    "course_name": "MBA - FULL TIME",
    "program_type": "MBA",
    "category": "ABC Business Innovation",
    "total_hours": 8,
    "description": "Master of Business Administration - Full Time Program",
    "status": "active",
    "created_at": "2024-01-01",
    "difficulty_level": "advanced"
}
```

#### **Lessons Collection**
```python
lesson_data = {
    "lesson_id": "lesson_001",
    "course_id": "course_001", 
    "lesson_title": "Business Strategy Fundamentals",
    "duration_hours": 2,
    "lesson_order": 1,
    "content_type": "video", # video, document, quiz, assignment
    "description": "Introduction to business strategy concepts"
}
```

#### **Enrollments Collection**
```python
enrollment_data = {
    "enrollment_id": "enroll_001",
    "user_id": "user_001",
    "course_id": "course_001",
    "enrollment_date": "2024-01-15",
    "status": "active", # active, completed, suspended
    "completion_date": None
}
```

#### **Progress Collection**
```python
progress_data = {
    "progress_id": "progress_001",
    "user_id": "user_001",
    "course_id": "course_001",
    "lesson_id": "lesson_001",
    "attended_hours": 6,
    "total_hours": 8,
    "progress_percentage": 75,
    "current_status": "Resume", # Resume, Learn, Complete
    "last_accessed": "2024-06-07",
    "completion_status": "in_progress" # not_started, in_progress, completed
}
```

### 3. Functions สำหรับ Query ข้อมูล:

```python
# เพิ่มใน conn.py
def get_user_course_progress(self, user_id):
    """Get all course progress for a user"""
    try:
        # Query enrollments for user
        enrollments = self.enrollments_collection.query(
            query_texts=[f"User: {user_id}"],
            where={"user_id": user_id}
        )
        
        course_progress = []
        if enrollments['metadatas']:
            for enrollment in enrollments['metadatas'][0]:
                course_id = enrollment['course_id']
                
                # Get course details
                course = self.get_course_by_id(course_id)
                
                # Get progress details
                progress = self.get_course_progress(user_id, course_id)
                
                course_data = {
                    "course_name": course['course_name'],
                    "category": course['category'],
                    "attended_hours": progress['attended_hours'],
                    "total_hours": progress['total_hours'],
                    "progress_percentage": progress['progress_percentage'],
                    "status": progress['current_status']
                }
                course_progress.append(course_data)
        
        return course_progress
    except Exception as e:
        print(f"Error getting user course progress: {str(e)}")
        return []

def get_course_by_id(self, course_id):
    """Get course details by ID"""
    try:
        results = self.courses_collection.query(
            query_texts=[f"Course: {course_id}"],
            where={"course_id": course_id},
            n_results=1
        )
        
        if results['metadatas'] and len(results['metadatas'][0]) > 0:
            return results['metadatas'][0][0]
        return None
    except Exception as e:
        print(f"Error getting course: {str(e)}")
        return None

def get_course_progress(self, user_id, course_id):
    """Get progress for specific user and course"""
    try:
        results = self.progress_collection.query(
            query_texts=[f"Progress: {user_id} {course_id}"],
            where={"$and": [{"user_id": user_id}, {"course_id": course_id}]},
            n_results=1
        )
        
        if results['metadatas'] and len(results['metadatas'][0]) > 0:
            return results['metadatas'][0][0]
        return None
    except Exception as e:
        print(f"Error getting progress: {str(e)}")
        return None

def update_course_progress(self, user_id, course_id, attended_hours):
    """Update course progress"""
    try:
        # Get current progress
        progress = self.get_course_progress(user_id, course_id)
        course = self.get_course_by_id(course_id)
        
        if progress and course:
            total_hours = course['total_hours']
            new_percentage = (attended_hours / total_hours) * 100
            
            # Determine status based on progress
            if new_percentage == 100:
                status = "Complete"
            elif new_percentage > 0:
                status = "Resume"
            else:
                status = "Learn"
            
            # Update progress
            updated_progress = progress.copy()
            updated_progress.update({
                "attended_hours": attended_hours,
                "progress_percentage": new_percentage,
                "current_status": status,
                "last_accessed": str(datetime.datetime.now().date())
            })
            
            # Update in ChromaDB
            self.progress_collection.update(
                ids=[progress['progress_id']],
                metadatas=[updated_progress]
            )
            
            return True
        return False
    except Exception as e:
        print(f"Error updating progress: {str(e)}")
        return False
```

### 4. API Endpoint สำหรับดึงข้อมูล:

```python
# เพิ่มใน app.py
@app.route('/api/courses/progress', methods=['GET'])
@token_required
def get_my_course_progress(current_user):
    """Get course progress for current user"""
    user = db.get_user_by_email(current_user)
    if not user:
        return jsonify(success=False, message="User not found"), 404
    
    progress_data = db.get_user_course_progress(user['user_id'])
    
    return jsonify({
        'success': True,
        'courses': progress_data
    })

@app.route('/api/courses', methods=['GET'])
@token_required  
def get_available_courses(current_user):
    """Get all available courses"""
    courses = db.get_all_courses()
    return jsonify({
        'success': True,
        'courses': courses
    })

@app.route('/api/courses/<course_id>/enroll', methods=['POST'])
@token_required
def enroll_course(current_user, course_id):
    """Enroll user in a course"""
    user = db.get_user_by_email(current_user)
    if not user:
        return jsonify(success=False, message="User not found"), 404
    
    success = db.enroll_user_in_course(user['user_id'], course_id)
    
    if success:
        return jsonify(success=True, message="Enrolled successfully")
    else:
        return jsonify(success=False, message="Enrollment failed"), 400
```

การออกแบบนี้จะช่วยให้คุณสามารถ:
- แสดงรายการคอร์สพร้อมความคืบหน้า
- ติดตามชั่วโมงการเรียน
- จัดการสถานะของการเรียน (Resume, Learn, Complete)
- Query ข้อมูลได้อย่างมีประสิทธิภาพผ่าน ChromaDB

คุณต้องการให้ฉันสร้างไฟล์ implementation ที่สมบูรณ์หรือมีคำถามเพิ่มเติมเกี่ยวกับการออกแบบนี้ไหม?

```python
# เพิ่มใน conn.py
class DatabaseManager:
    def __init__(self):
        # ... existing code ...
        
        # Initialize course-related collections
        self.courses_collection = self._get_or_create_collection("courses")
        self.enrollments_collection = self._get_or_create_collection("enrollments")
        self.progress_collection = self._get_or_create_collection("progress")
        self.lessons_collection = self._get_or_create_collection("lessons")
    
    def _get_or_create_collection(self, name):
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(name)
```

```python
course_data = {
    "course_id": "course_001",
    "course_name": "MBA - FULL TIME",
    "program_type": "MBA",
    "category": "ABC Business Innovation",
    "total_hours": 8,
    "description": "Master of Business Administration - Full Time Program",
    "status": "active",
    "created_at": "2024-01-01",
    "difficulty_level": "advanced"
}
```

```python
lesson_data = {
    "lesson_id": "lesson_001",
    "course_id": "course_001", 
    "lesson_title": "Business Strategy Fundamentals",
    "duration_hours": 2,
    "lesson_order": 1,
    "content_type": "video", # video, document, quiz, assignment
    "description": "Introduction to business strategy concepts"
}
```

```python
enrollment_data = {
    "enrollment_id": "enroll_001",
    "user_id": "user_001",
    "course_id": "course_001",
    "enrollment_date": "2024-01-15",
    "status": "active", # active, completed, suspended
    "completion_date": None
}
```

```python
progress_data = {
    "progress_id": "progress_001",
    "user_id": "user_001",
    "course_id": "course_001",
    "lesson_id": "lesson_001",
    "attended_hours": 6,
    "total_hours": 8,
    "progress_percentage": 75,
    "current_status": "Resume", # Resume, Learn, Complete
    "last_accessed": "2024-06-07",
    "completion_status": "in_progress" # not_started, in_progress, completed
}
```

```python
# เพิ่มใน conn.py
def get_user_course_progress(self, user_id):
    """Get all course progress for a user"""
    try:
        # Query enrollments for user
        enrollments = self.enrollments_collection.query(
            query_texts=[f"User: {user_id}"],
            where={"user_id": user_id}
        )
        
        course_progress = []
        if enrollments['metadatas']:
            for enrollment in enrollments['metadatas'][0]:
                course_id = enrollment['course_id']
                
                # Get course details
                course = self.get_course_by_id(course_id)
                
                # Get progress details
                progress = self.get_course_progress(user_id, course_id)
                
                course_data = {
                    "course_name": course['course_name'],
                    "category": course['category'],
                    "attended_hours": progress['attended_hours'],
                    "total_hours": progress['total_hours'],
                    "progress_percentage": progress['progress_percentage'],
                    "status": progress['current_status']
                }
                course_progress.append(course_data)
        
        return course_progress
    except Exception as e:
        print(f"Error getting user course progress: {str(e)}")
        return []

def get_course_by_id(self, course_id):
    """Get course details by ID"""
    try:
        results = self.courses_collection.query(
            query_texts=[f"Course: {course_id}"],
            where={"course_id": course_id},
            n_results=1
        )
        
        if results['metadatas'] and len(results['metadatas'][0]) > 0:
            return results['metadatas'][0][0]
        return None
    except Exception as e:
        print(f"Error getting course: {str(e)}")
        return None

def get_course_progress(self, user_id, course_id):
    """Get progress for specific user and course"""
    try:
        results = self.progress_collection.query(
            query_texts=[f"Progress: {user_id} {course_id}"],
            where={"$and": [{"user_id": user_id}, {"course_id": course_id}]},
            n_results=1
        )
        
        if results['metadatas'] and len(results['metadatas'][0]) > 0:
            return results['metadatas'][0][0]
        return None
    except Exception as e:
        print(f"Error getting progress: {str(e)}")
        return None

def update_course_progress(self, user_id, course_id, attended_hours):
    """Update course progress"""
    try:
        # Get current progress
        progress = self.get_course_progress(user_id, course_id)
        course = self.get_course_by_id(course_id)
        
        if progress and course:
            total_hours = course['total_hours']
            new_percentage = (attended_hours / total_hours) * 100
            
            # Determine status based on progress
            if new_percentage == 100:
                status = "Complete"
            elif new_percentage > 0:
                status = "Resume"
            else:
                status = "Learn"
            
            # Update progress
            updated_progress = progress.copy()
            updated_progress.update({
                "attended_hours": attended_hours,
                "progress_percentage": new_percentage,
                "current_status": status,
                "last_accessed": str(datetime.datetime.now().date())
            })
            
            # Update in ChromaDB
            self.progress_collection.update(
                ids=[progress['progress_id']],
                metadatas=[updated_progress]
            )
            
            return True
        return False
    except Exception as e:
        print(f"Error updating progress: {str(e)}")
        return False
```

```python
# เพิ่มใน app.py
@app.route('/api/courses/progress', methods=['GET'])
@token_required
def get_my_course_progress(current_user):
    """Get course progress for current user"""
    user = db.get_user_by_email(current_user)
    if not user:
        return jsonify(success=False, message="User not found"), 404
    
    progress_data = db.get_user_course_progress(user['user_id'])
    
    return jsonify({
        'success': True,
        'courses': progress_data
    })

@app.route('/api/courses', methods=['GET'])
@token_required  
def get_available_courses(current_user):
    """Get all available courses"""
    courses = db.get_all_courses()
    return jsonify({
        'success': True,
        'courses': courses
    })

@app.route('/api/courses/<course_id>/enroll', methods=['POST'])
@token_required
def enroll_course(current_user, course_id):
    """Enroll user in a course"""
    user = db.get_user_by_email(current_user)
    if not user:
        return jsonify(success=False, message="User not found"), 404
    
    success = db.enroll_user_in_course(user['user_id'], course_id)
    
    if success:
        return jsonify(success=True, message="Enrolled successfully")
    else:
        return jsonify(success=False, message="Enrollment failed"), 400
```

