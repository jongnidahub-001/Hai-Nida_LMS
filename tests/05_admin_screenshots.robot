*** Settings ***
Documentation    Suite 5: Capture screenshots หน้า Admin ทั้งหมด (มี enrolled users + quiz scores)
Resource         resources/common.resource
Suite Setup      Setup Admin Session
Suite Teardown   Close Browser

*** Keywords ***
Setup Admin Session
    Open Browser To App
    Login As Admin

*** Test Cases ***
Capture Admin Dashboard
    [Documentation]    แดชบอร์ด All Users (มี test user ที่ enrolled แล้ว)
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    Wait And Screenshot    admin-dashboard.png

Capture Admin Courses Page
    [Documentation]    หน้า Course Management แท็บ Courses (มี course ที่สร้างจาก PDF)
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    Wait And Screenshot    admin-courses.png

Capture Admin Process Tab
    [Documentation]    แท็บ Process (มี tasks จาก import)
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    ${process_tab}=    Get Elements    a:has-text("Process")
    IF    len($process_tab) > 0
        Click    a:has-text("Process") >> nth=0
        Sleep    ${ANIMATION_WAIT}
        Wait And Screenshot    admin-process.png
    END

Capture Admin Course Detail Page
    [Documentation]    หน้ารายละเอียดคอร์ส Admin (มี enrolled users)
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        Click    text="View Details" >> nth=0
        Wait For Admin Detail Load
        Wait And Screenshot    admin-course-detail.png
    END

Capture Admin Course Enrolled Users Tab
    [Documentation]    แท็บ Enrolled Users (มี test user + progress + quiz score)
    ${users_tab}=    Get Elements    text="Enrolled Users"
    IF    len($users_tab) > 0
        Click    text="Enrolled Users"
        Sleep    2s
        Wait And Screenshot    admin-course-users.png
    END

Capture Admin User Detail Page
    [Documentation]    หน้ารายละเอียดผู้ใช้ (test user ที่มี enrollment + quiz)
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    # Find test user row and click View Details
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        # Click the last View Details (likely test user, not admin)
        Click    text="View Details" >> nth=-1
        Wait For Admin Detail Load
        Wait And Screenshot    admin-user-detail.png
    END

Capture Admin View Answers Modal
    [Documentation]    Modal View Answers (ต้องอยู่ที่ user detail page จาก test case ก่อน)
    # Switch to Quiz Results tab
    ${quiz_tab}=    Get Elements    text=Quiz Results
    IF    len($quiz_tab) > 0
        Click    text=Quiz Results >> visible=true
        Sleep    2s
        # Click View Answers button
        ${answers_btns}=    Get Elements    text="View Answers"
        IF    len($answers_btns) > 0
            Click    text="View Answers" >> nth=0
            Wait For Elements State    .modal.is-active    visible
            # Wait for answers content to load (async fetch)
            Sleep    3s
            Take Viewport Screenshot    admin-view-answers.png
            Click    .modal .delete
        END
    END

Capture Admin Settings Page
    [Documentation]    หน้า Gemini API Settings
    Go To    ${BASE_URL}/admin/settings
    Wait For Page Load
    Wait And Screenshot    admin-settings.png

Capture Admin Quizzes Page
    [Documentation]    หน้า All Quiz Scores (มี score จาก test user)
    Go To    ${BASE_URL}/admin/quizzes
    Wait For Page Load
    Wait And Screenshot    admin-quizzes.png
