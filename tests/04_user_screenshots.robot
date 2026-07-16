*** Settings ***
Documentation    Suite 4: Capture screenshots หน้า User ทั้งหมด (มีข้อมูล enrolled + quiz score แล้ว)
Resource         resources/common.resource
Suite Setup      Setup User Session
Suite Teardown   Close Browser

*** Keywords ***
Setup User Session
    Open Browser To App
    Login As User

*** Test Cases ***
Capture Dashboard Full Page
    [Documentation]    หน้าหลัก Dashboard ทั้งหมด (มี enrolled course + quiz status)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Load
    Wait And Screenshot    dashboard.png

Capture Dashboard Featured Courses
    [Documentation]    ส่วน Featured Courses (dark card area)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Load
    ${cards}=    Get Elements    .home-overview-card
    IF    len($cards) > 1
        Scroll To Element And Screenshot    .home-overview-card >> nth=1    dashboard-featured.png
    ELSE IF    len($cards) > 0
        Scroll To Element And Screenshot    .home-overview-card >> nth=0    dashboard-featured.png
    END

Capture Dashboard My Courses
    [Documentation]    ส่วน MY COURSES พร้อมแท็บ (มี progress)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Load
    Scroll To Element And Screenshot    .home-courses-card >> nth=0    dashboard-my-courses.png

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
    [Documentation]    หน้ารายละเอียดคอร์ส (enrolled, มี progress)
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
        Wait And Screenshot    course-detail.png
    END

Capture Course Detail Progress Section
    [Documentation]    ส่วน Your Progress และปุ่ม
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
        Scroll To Element And Screenshot    .course-progress-card    course-detail-progress.png
    END

Capture Lesson Page
    [Documentation]    หน้าบทเรียนเต็มรูปแบบ
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
        # Click any lesson button
        ${review_btns}=    Get Elements    text="Review Lesson" >> visible=true
        ${continue_btns}=    Get Elements    text="Continue Lesson" >> visible=true
        ${start_btns}=    Get Elements    text="Start Lesson" >> visible=true
        IF    len($review_btns) > 0
            Click    text="Review Lesson" >> nth=0
        ELSE IF    len($continue_btns) > 0
            Click    text="Continue Lesson" >> nth=0
        ELSE IF    len($start_btns) > 0
            Click    text="Start Lesson" >> nth=0
        END
        Wait For Lesson Page Load
        Wait And Screenshot    lesson-page.png
    END

Capture Lesson Chat Modal
    [Documentation]    Modal แชท AI
    ${chat_btns}=    Get Elements    text="Chat with AI"
    IF    len($chat_btns) > 0
        Click    text="Chat with AI"
        Wait For Elements State    .chat-modal    visible
        Sleep    1s
        Wait And Screenshot    lesson-chat.png    full_page=false
        # Close chat
        ${close_btns}=    Get Elements    .chat-modal .chat-controls button
        IF    len($close_btns) > 0
            Click    .chat-modal .chat-controls button >> nth=-1
        END
    END

Capture Lesson Navigation
    [Documentation]    ปุ่มลอย Chat และแถบนำทาง
    ${floating_btn}=    Get Elements    .floating-chat-button
    IF    len($floating_btn) > 0
        Scroll To Element And Screenshot    .floating-chat-button    lesson-nav.png
    END

Capture Quiz Completed Page
    [Documentation]    หน้า Quiz Result (หลังทำ quiz แล้ว)
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
        ${result_btns}=    Get Elements    button:has-text("Quiz Result")
        IF    len($result_btns) > 0
            Click    button:has-text("Quiz Result")
            Wait For Quiz Result Load
            Wait And Screenshot    quiz-completed.png
        END
    END
