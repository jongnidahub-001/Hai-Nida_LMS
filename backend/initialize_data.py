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
    
    print("\n" + "=" * 50)
    print("Data initialization completed successfully!")
    
    # Display summary
    print("\nData Summary:")
    print(f"Users: {len(db.get_all_users())}")
    print(f"Courses: {len(db.get_all_courses())}")
    
    # Show course details
    print("\nCourses created:")
    courses = db.get_all_courses()
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