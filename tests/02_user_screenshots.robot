*** Settings ***
Documentation    Capture screenshots ของหน้าต่างๆ ฝั่ง User (Student)
Resource         resources/common.resource
Suite Setup      Setup User Session
Suite Teardown   Close Browser

*** Keywords ***
Setup User Session
    Open Browser To App
    Login As User

*** Test Cases ***
Capture Dashboard Full Page
    [Documentation]    หน้าหลัก Dashboard ทั้งหมด
    Go To    ${BASE_URL}/home
    Wait For Page Load
    Wait And Screenshot    dashboard.png

Capture Dashboard Featured Courses
    [Documentation]    ส่วน Featured Courses (dark card area)
    Go To    ${BASE_URL}/home
    Wait For Page Load
    Scroll To Element And Screenshot    .home-overview-card:nth-child(2)    dashboard-featured.png

Capture Dashboard My Courses
    [Documentation]    ส่วน MY COURSES พร้อมแท็บ
    Go To    ${BASE_URL}/home
    Wait For Page Load
    Scroll To Element And Screenshot    .home-courses-card    dashboard-my-courses.png

Capture All Courses Page
    [Documentation]    หน้าคอร์สทั้งหมด
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    Wait And Screenshot    all-courses.png

Capture All Courses Cards
    [Documentation]    การ์ดคอร์สแบบต่างๆ (zoom ส่วน grid)
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    Scroll To Element And Screenshot    .columns.is-multiline    all-courses-cards.png

Capture Course Detail Page
    [Documentation]    หน้ารายละเอียดคอร์ส (ต้องมี courseId ใน DB)
    [Tags]    requires-course-data
    # Navigate to first course from courses page
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    # Click first "View Detail" or course card link
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Page Load
        Wait And Screenshot    course-detail.png
    END

Capture Course Detail Progress Section
    [Documentation]    ส่วน Your Progress และปุ่ม
    [Tags]    requires-course-data
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Page Load
        Scroll To Element And Screenshot    .course-progress-card    course-detail-progress.png
    END

Capture Lesson Page
    [Documentation]    หน้าบทเรียนเต็มรูปแบบ (ต้องเข้าบทเรียนได้)
    [Tags]    requires-enrolled
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    # Navigate to a course then a lesson
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Page Load
        # Click start/continue lesson button
        ${lesson_btns}=    Get Elements    text="Start Lesson" >> visible=true
        IF    len($lesson_btns) > 0
            Click    text="Start Lesson" >> nth=0
        ELSE
            ${continue_btns}=    Get Elements    text="Continue Lesson" >> visible=true
            IF    len($continue_btns) > 0
                Click    text="Continue Lesson" >> nth=0
            ELSE
                ${review_btns}=    Get Elements    text="Review Lesson" >> visible=true
                IF    len($review_btns) > 0
                    Click    text="Review Lesson" >> nth=0
                END
            END
        END
        Wait For Page Load
        Wait And Screenshot    lesson-page.png
    END

Capture Lesson Chat Modal
    [Documentation]    Modal แชท AI
    [Tags]    requires-enrolled
    # Assuming we are already on a lesson page from previous test
    ${chat_btns}=    Get Elements    text="Chat with AI"
    IF    len($chat_btns) > 0
        Click    text="Chat with AI"
        Wait For Elements State    .chat-modal    visible
        Sleep    1s
        Wait And Screenshot    lesson-chat.png    full_page=false
        # Close chat
        Click    .chat-modal .chat-controls button >> nth=-1
    END

Capture Lesson Navigation
    [Documentation]    ปุ่มลอย Chat และแถบนำทาง
    [Tags]    requires-enrolled
    # Scroll to bottom to see floating button and nav footer
    ${floating_btn}=    Get Elements    .floating-chat-button
    IF    len($floating_btn) > 0
        Scroll To Element And Screenshot    .floating-chat-button    lesson-nav.png
    END

Capture Quiz Taking Page
    [Documentation]    หน้าแบบทดสอบขณะทำ (ต้องมี quiz ใน course)
    [Tags]    requires-quiz
    # Navigate to quiz (need course with quiz)
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Page Load
        # Look for Take Assessment button
        ${quiz_btns}=    Get Elements    text="Take Assessment"
        IF    len($quiz_btns) > 0
            Click    text="Take Assessment"
            Wait For Page Load
            Wait And Screenshot    quiz-taking.png
        END
    END

Capture Quiz Questions
    [Documentation]    คำถามแบบ Subjective และ Fill in the Blank
    [Tags]    requires-quiz
    # If we're on quiz page, scroll to find different question types
    ${questions}=    Get Elements    .question-card
    IF    len($questions) > 1
        Scroll To Element And Screenshot    .question-card >> nth=1    quiz-questions.png
    END

Capture Quiz Completed Page
    [Documentation]    หน้า Quiz Completed (ดูจาก quiz-result route)
    [Tags]    requires-quiz-completed
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Page Load
        # Look for Quiz Result button (already completed quiz)
        ${result_btns}=    Get Elements    text="Quiz Result"
        IF    len($result_btns) > 0
            Click    text="Quiz Result"
            Wait For Page Load
            Wait And Screenshot    quiz-completed.png
        END
    END
