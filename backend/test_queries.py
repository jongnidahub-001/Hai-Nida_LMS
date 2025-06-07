#!/usr/bin/env python3
"""
Test script to demonstrate querying the course management system data
"""

from conn import db
import json

def print_json(data, title=""):
    """Helper function to print JSON data nicely"""
    if title:
        print(f"\n{title}:")
        print("-" * len(title))
    print(json.dumps(data, indent=2, default=str))

def main():
    print("Course Management System - Query Examples")
    print("=" * 50)
    
    # 1. Get all courses
    print("\n1. All Courses:")
    courses = db.get_all_courses()
    for course in courses:
        print(f"- {course['course_name']} ({course['status']}) - {course['difficulty_level']}")
    
    # 2. Get lessons for a specific course
    if courses:
        first_course = courses[0]
        print(f"\n2. Lessons for '{first_course['course_name']}':")
        lessons = db.get_lessons_by_course_id(first_course['course_id'])
        for lesson in sorted(lessons, key=lambda x: x['lesson_order']):
            print(f"   {lesson['lesson_order']}. {lesson['lesson_title']} ({lesson['duration_hours']}h)")
            print(f"      Description: {lesson['description']}")
    
    # 3. Get content for a specific lesson
    if lessons:
        first_lesson = lessons[0]
        print(f"\n3. Content for '{first_lesson['lesson_title']}':")
        content_items = db.get_content_by_lesson_id(first_lesson['lesson_id'])
        for content in sorted(content_items, key=lambda x: x['content_order']):
            content_preview = content['content'][:80] + "..." if len(content['content']) > 80 else content['content']
            print(f"   {content['content_order']}. [{content['content_type'].upper()}] {content_preview}")
    
    # 4. Course statistics
    print("\n4. Course Statistics:")
    active_courses = [c for c in courses if c['status'] == 'Active']
    inactive_courses = [c for c in courses if c['status'] == 'Inactive']
    
    print(f"   Total Courses: {len(courses)}")
    print(f"   Active Courses: {len(active_courses)}")
    print(f"   Inactive Courses: {len(inactive_courses)}")
    
    # Difficulty breakdown
    difficulty_counts = {}
    for course in courses:
        diff = course['difficulty_level']
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
    
    print("   Difficulty Distribution:")
    for level, count in difficulty_counts.items():
        print(f"     {level}: {count}")
    
    # 5. Total hours by difficulty
    print("\n5. Total Hours by Difficulty:")
    difficulty_hours = {}
    for course in courses:
        diff = course['difficulty_level']
        hours = course['total_hour']
        difficulty_hours[diff] = difficulty_hours.get(diff, 0) + hours
    
    for level, hours in difficulty_hours.items():
        print(f"   {level}: {hours} hours")
    
    # 6. Users in the system
    print("\n6. Users in System:")
    users = db.get_all_users()
    for user in users:
        print(f"   - {user['full_name']} ({user['email']})")
    
    # 7. Example: Find specific course by searching
    print("\n7. Search Example - Finding Python course:")
    python_courses = [c for c in courses if 'Python' in c['course_name']]
    if python_courses:
        course = python_courses[0]
        print_json(course, f"Course Details: {course['course_name']}")
        
        # Get its lessons
        lessons = db.get_lessons_by_course_id(course['course_id'])
        print(f"\nThis course has {len(lessons)} lessons:")
        for lesson in sorted(lessons, key=lambda x: x['lesson_order']):
            print(f"   {lesson['lesson_order']}. {lesson['lesson_title']}")
            
            # Get content count for each lesson
            content_count = len(db.get_content_by_lesson_id(lesson['lesson_id']))
            print(f"      └── {content_count} content items")

if __name__ == "__main__":
    main() 