*** Settings ***
Documentation    Suite 1: Admin login, สร้าง test user, import document ผ่าน UI,
...              รอ AI generate, preview course, create quiz, submit — เพื่อเตรียมข้อมูลสำหรับ suite ถัดไป
Resource         resources/common.resource
Suite Setup      Setup Admin Session
Suite Teardown   Close Browser

*** Keywords ***
Setup Admin Session
    Cleanup Test User
    Open Browser To App
    Login As Admin

*** Test Cases ***
Create Test User Via Add User Modal
    [Documentation]    Admin สร้าง test user ใหม่ + capture modal
    Go To    ${BASE_URL}/admin
    Wait For Page Load
    Click    button:has-text("Add User") >> nth=0
    Wait For Elements State    .modal.is-active    visible
    Sleep    0.5s
    Take Viewport Screenshot    admin-add-user.png
    Fill Text    .modal input[type="email"]    ${USER_EMAIL}
    Click    .modal .modal-card-foot button.is-primary
    Sleep    2s
    # Close modal if still open
    ${modal_open}=    Get Elements    .modal.is-active .delete
    IF    len($modal_open) > 0
        Click    .modal.is-active .delete
    END

Import Document Via UI
    [Documentation]    Admin import test.pdf ผ่าน Import Document modal + capture
    Go To    ${BASE_URL}/admin/courses
    Wait For Page Load
    # Open Import Document modal
    Click    text="Import Document"
    Wait For Elements State    .modal.is-active    visible
    Sleep    0.5s
    # Upload PDF file
    Upload File By Selector    .modal input[type="file"]    ${TEST_PDF}
    Sleep    1s
    Take Viewport Screenshot    admin-import.png
    # Click Generate All Levels
    Click    .modal button:has-text("Generate All Levels")
    Sleep    3s

Wait For Generation Complete
    [Documentation]    รอจน task สถานะ completed (poll ทุก 15 วินาที, timeout 10 นาที)
    # Should already be on Process tab after Generate
    Wait For Process Task Complete

Preview Generated Course
    [Documentation]    คลิก Preview + capture Course Preview page
    # Click Preview button on first completed task
    Click    button:has-text("Preview") >> nth=0
    Wait For Course Preview Load
    Wait And Screenshot    admin-course-preview.png

Create And Preview Quiz
    [Documentation]    คลิก Create Quiz → รอ AI generate quiz → capture Quiz Preview
    Click    button:has-text("Create Quiz")
    Wait For Quiz Preview Load
    Wait And Screenshot    admin-quiz-preview.png

Submit Quiz To Database
    [Documentation]    คลิก Submit Quiz → บันทึกคอร์ส+quiz ลง database
    Click    button:has-text("Submit Quiz")
    Sleep    3s
    # Should redirect back to courses or show success
    Wait For Page Load

Capture Admin Settings
    [Documentation]    หน้า Gemini API Settings
    Go To    ${BASE_URL}/admin/settings
    Wait For Page Load
    Wait And Screenshot    admin-settings.png
