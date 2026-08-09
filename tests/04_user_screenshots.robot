*** Settings ***
Documentation    Suite 4: Capture screenshots หน้า User ทั้งหมด (มีข้อมูล enrolled + quiz score แล้ว)
...
...              Use Cases ที่ครอบคลุม (ตามลำดับ user flow):
...              - UC-U5: Dashboard (Featured, My Courses, Quiz Status)
...              - UC-U6: All Courses (search, filter, cards)
...              - UC-U7: Course Detail (enrolled, progress)
...              - UC-U8: Lesson Page (content, chat, navigation)
...              - UC-U10: Quiz Result (score + AI analysis)
Resource         resources/common.resource
Suite Setup      Setup User Session
Suite Teardown   Close Browser

*** Keywords ***
Setup User Session
    Open Browser To App
    Login As User

*** Test Cases ***
# ═══════════════════════════════════════════════════════════════════
# UC-U5: Dashboard Screenshots
# ═══════════════════════════════════════════════════════════════════
Capture Dashboard Full Page
    [Documentation]    หน้าหลัก Dashboard ทั้งหมด (มี enrolled course + quiz status)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Ready
    Wait And Screenshot    dashboard.png

Capture Dashboard Featured Courses
    [Documentation]    ส่วน Featured Courses (dark card area with recommendations)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Ready
    ${cards}=    Get Elements    .home-overview-card
    IF    len($cards) > 1
        Scroll To Element And Screenshot    .home-overview-card >> nth=1    dashboard-featured.png
    ELSE IF    len($cards) > 0
        Scroll To Element And Screenshot    .home-overview-card >> nth=0    dashboard-featured.png
    END

Capture Dashboard My Courses
    [Documentation]    ส่วน MY COURSES พร้อมแท็บ ALL / Resume / Complete (มี progress)
    Go To    ${BASE_URL}/home
    Wait For Dashboard Ready
    Scroll To Element And Screenshot    .home-courses-card >> nth=0    dashboard-my-courses.png

# ═══════════════════════════════════════════════════════════════════
# UC-U6: All Courses Screenshots
# ═══════════════════════════════════════════════════════════════════
Capture All Courses Page
    [Documentation]    หน้าคอร์สทั้งหมด (header + search + difficulty filter + grid)
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    Wait And Screenshot    all-courses.png

Capture All Courses Cards
    [Documentation]    การ์ดคอร์สแบบต่างๆ (zoom ส่วน grid — enrolled, completed, available)
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    Scroll To Element And Screenshot    .columns.is-multiline    all-courses-cards.png

# ═══════════════════════════════════════════════════════════════════
# UC-U7: Course Detail Screenshots
# ═══════════════════════════════════════════════════════════════════
Capture Course Detail Page
    [Documentation]    หน้ารายละเอียดคอร์ส (enrolled, มี progress, lesson list)
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
        Wait And Screenshot    course-detail.png
    END

Capture Course Detail Progress Section
    [Documentation]    ส่วน Your Progress (progress bar, stats, action buttons)
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
        ${progress_card}=    Get Elements    .course-progress-card
        IF    len($progress_card) > 0
            Scroll To Element And Screenshot    .course-progress-card    course-detail-progress.png
        END
    END

# ═══════════════════════════════════════════════════════════════════
# UC-U8: Lesson Page Screenshots
# ═══════════════════════════════════════════════════════════════════
Capture Lesson Page
    [Documentation]    หน้าบทเรียนเต็มรูปแบบ (content + sidebar + navigation)
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
        # Click any available lesson button
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
        Wait For Lesson Page Ready
        Wait And Screenshot    lesson-page.png
    END

Capture Lesson Chat Modal
    [Documentation]    Modal แชท AI (opened from lesson page)
    ${chat_btns}=    Get Elements    text="Chat with AI"
    IF    len($chat_btns) > 0
        Click    text="Chat with AI"
        # Wait for chat modal to fully render (not just visible, but content ready)
        Wait For Elements State    .chat-modal    visible    timeout=${DEFAULT_TIMEOUT}
        # Wait for chat input to be ready (modal fully loaded)
        Wait For Elements State    .chat-modal textarea    visible    timeout=${DEFAULT_TIMEOUT}
        Wait And Screenshot    lesson-chat.png    full_page=false
        # Close chat modal
        ${close_btns}=    Get Elements    .chat-modal .chat-controls button
        IF    len($close_btns) > 0
            Click    .chat-modal .chat-controls button >> nth=-1
        END
    END

Capture Lesson Navigation
    [Documentation]    ปุ่มลอย Chat และแถบนำทาง (Previous / Next)
    ${floating_btn}=    Get Elements    .floating-chat-button
    IF    len($floating_btn) > 0
        Scroll To Element And Screenshot    .floating-chat-button    lesson-nav.png
    END

# ═══════════════════════════════════════════════════════════════════
# UC-U10: Quiz Result Screenshot
# ═══════════════════════════════════════════════════════════════════
Capture Quiz Result Page
    [Documentation]    หน้า Quiz Result (score + AI analysis + recommendations)
    ...    Accessed via Quiz Result button on course detail page
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
        ${result_btns}=    Get Elements    button:has-text("Quiz Result")
        IF    len($result_btns) > 0
            Click    button:has-text("Quiz Result")
            # Wait for quiz result page to fully load (AI analysis may take time)
            Wait For Quiz Result Page Ready
            Wait And Screenshot    quiz-completed.png
        END
    END
