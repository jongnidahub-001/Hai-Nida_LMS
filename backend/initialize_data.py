#!/usr/bin/env python3
"""
Script to initialize dummy data for the course management system
Run this script to populate the ChromaDB with sample data
"""

from conn import db

def main():
    print("Initializing Course Management System Data...")
    print("=" * 50)
    
    # Initialize user data
    print("\n1. Creating sample users...")
    db.initialize_sample_data()
    
    # Initialize course data
    print("\n2. Creating sample courses, lessons, and content...")
    db.initialize_course_data()
    
    # Initialize enrollment and progress data
    print("\n3. Creating sample enrollments and progress tracking...")
    db.initialize_enrollment_data()
    
    print("\n" + "=" * 50)
    print("Data initialization completed successfully!")
    
    # Display summary
    print("\nData Summary:")
    users = db.get_all_users()
    courses = db.get_all_courses()
    print(f"Users: {len(users)}")
    print(f"Courses: {len(courses)}")
    
    # Show enrollment summary
    total_enrollments = 0
    for user in users:
        enrollments = db.get_enrollments_by_user(user['user_id'])
        total_enrollments += len(enrollments)
        if enrollments:
            print(f"\n{user['username']} enrolled in:")
            for enrollment in enrollments:
                course = db.get_course_by_id(enrollment['course_id'])
                if course:
                    progress = db.get_course_progress_summary(user['user_id'], enrollment['course_id'])
                    print(f"  - {course['course_name']} ({enrollment['status']}) - {progress['progress_percentage']}% complete")
    
    print(f"\nTotal Enrollments: {total_enrollments}")
    
    # Show course details
    print("\nCourses created:")
    for course in courses:
        print(f"- {course['course_name']} ({course['difficulty_level']}, {course['total_hour']} hours)")
        lessons = db.get_lessons_by_course_id(course['course_id'])
        print(f"  └── {len(lessons)} lessons")
        
        # Show lesson details for first course
        if course == courses[0]:
            print("  Lessons:")
            for lesson in lessons:
                print(f"    {lesson['lesson_order']}. {lesson['lesson_title']} ({lesson['duration_hours']}h)")
                content_items = db.get_content_by_lesson_id(lesson['lesson_id'])
                print(f"       └── {len(content_items)} content items")

if __name__ == "__main__":
    main() 