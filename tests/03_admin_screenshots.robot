*** Settings ***
Documentation    Capture screenshots ของหน้าต่างๆ ฝั่ง Admin
Resource         resources/common.resource
Suite Setup      Setup Admin Session
Suite Teardown   Close Browser

*** Keywords ***
Setup Admin Session
    Open Browser To App
    Login As Admin

*** Test Cases ***
Capture Admin Dashboard
    [Documentation]    แดชบอร์ด All Users
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    Wait And Screenshot    admin-dashboard.png

Capture Admin Add User Modal
    [Documentation]    Modal เพิ่มผู้ใช้
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    # Click Add User button
    Click    text="Add User"
    Wait For Elements State    .modal.is-active    visible
    Sleep    0.5s
    Take Viewport Screenshot    admin-add-user.png
    # Close modal
    Click    .modal .delete

Capture Admin Courses Page
    [Documentation]    หน้า Course Management แท็บ Courses
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    Wait And Screenshot    admin-courses.png

Capture Admin Process Tab
    [Documentation]    แท็บ Process และตาราง tasks
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    # Click Process tab
    ${process_tab}=    Get Elements    text="Process"
    IF    len($process_tab) > 0
        Click    text="Process"
        Sleep    ${ANIMATION_WAIT}
        Wait And Screenshot    admin-process.png
    END

Capture Admin Import Document Modal
    [Documentation]    Modal Import Document
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    # Click Import Document button
    ${import_btns}=    Get Elements    text="Import Document"
    IF    len($import_btns) > 0
        Click    text="Import Document"
        Wait For Elements State    .modal.is-active    visible
        Sleep    0.5s
        Take Viewport Screenshot    admin-import.png
        # Close modal
        Click    .modal .delete
    END

Capture Admin Course Detail Page
    [Documentation]    หน้ารายละเอียดคอร์ส Admin (ต้องมี course ใน DB)
    [Tags]    requires-course-data
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    # Click first View Details button
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        Click    text="View Details" >> nth=0
        Wait For Page Load
        Wait And Screenshot    admin-course-detail.png
    END

Capture Admin Course Enrolled Users Tab
    [Documentation]    แท็บ Enrolled Users
    [Tags]    requires-course-data
    # Assuming we're on admin course detail from previous test
    ${users_tab}=    Get Elements    text="Enrolled Users"
    IF    len($users_tab) > 0
        Click    text="Enrolled Users"
        Sleep    ${ANIMATION_WAIT}
        Wait And Screenshot    admin-course-users.png
    END

Capture Admin User Detail Page
    [Documentation]    หน้ารายละเอียดผู้ใช้ (ต้องมี user ใน DB)
    [Tags]    requires-user-data
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    # Click first View Details button in user table
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        Click    text="View Details" >> nth=0
        Wait For Page Load
        Wait And Screenshot    admin-user-detail.png
    END

Capture Admin View Answers Modal
    [Documentation]    Modal View Answers (ต้องมี quiz result ของ user)
    [Tags]    requires-quiz-data
    # Assuming we're on admin user detail page
    # Switch to Quiz Results tab
    ${quiz_tab}=    Get Elements    text=Quiz Results
    IF    len($quiz_tab) > 0
        Click    text=Quiz Results >> visible=true
        Sleep    ${ANIMATION_WAIT}
        # Click View Answers button
        ${answers_btns}=    Get Elements    text="View Answers"
        IF    len($answers_btns) > 0
            Click    text="View Answers" >> nth=0
            Wait For Elements State    .modal.is-active    visible
            Sleep    1s
            Take Viewport Screenshot    admin-view-answers.png
            # Close modal
            Click    .modal .delete
        END
    END

Capture Admin Settings Page
    [Documentation]    หน้า Gemini API Settings
    Go To    ${BASE_URL}/admin/settings
    Wait For Page Load
    Wait And Screenshot    admin-settings.png

Capture Admin Quizzes Page
    [Documentation]    หน้า All Quiz Scores
    Go To    ${BASE_URL}/admin/quizzes
    Wait For Page Load
    Wait And Screenshot    admin-quizzes.png
