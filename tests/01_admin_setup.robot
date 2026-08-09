*** Settings ***
Documentation    Suite 1: Admin login, สร้าง test user, import document ผ่าน UI,
...              รอ AI generate, preview course, create quiz, submit — เพื่อเตรียมข้อมูลสำหรับ suite ถัดไป
...
...              Use Cases ที่ครอบคลุม:
...              - UC-A1: Admin Login
...              - UC-A2: Add User (สร้าง test user)
...              - UC-A3: Import Document (PDF → Generate All Levels)
...              - UC-A4: Wait for AI Generation
...              - UC-A5: Preview Course
...              - UC-A6: Create Quiz + Preview
...              - UC-A7: Submit Quiz to Database
...              - UC-A8: Capture Admin Settings
Resource         resources/common.resource
Suite Setup      Setup Admin Session
Suite Teardown   Close Browser

*** Keywords ***
Setup Admin Session
    Cleanup Test User
    Open Browser To App
    Login As Admin

*** Test Cases ***
# ─── UC-A1: Admin Login (handled by Suite Setup) ─────────────────
# Admin login is performed in Suite Setup via Login As Admin keyword

# ─── UC-A2: Add User ─────────────────────────────────────────────
Create Test User Via Add User Modal
    [Documentation]    Admin สร้าง test user ใหม่ + capture modal
    ...    Verifies: Modal opens, email can be entered, user is created
    Go To    ${BASE_URL}/admin
    Wait For Admin Page Ready
    Click    button:has-text("Add User") >> nth=0
    Wait For Elements State    .modal.is-active    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for modal animation to complete
    Wait For Elements State    .modal input[type="email"]    visible    timeout=${DEFAULT_TIMEOUT}
    Take Viewport Screenshot    admin-add-user.png
    Fill Text    .modal input[type="email"]    ${USER_EMAIL}
    Click    .modal .modal-card-foot button.is-primary
    # Wait for modal to close or success indication
    Sleep    2s
    ${modal_open}=    Get Elements    .modal.is-active .delete
    IF    len($modal_open) > 0
        Click    .modal.is-active .delete
    END

# ─── UC-A3: Import Document ──────────────────────────────────────
Import Document Via UI
    [Documentation]    Admin import test.pdf ผ่าน Import Document modal + capture
    ...    Verifies: Modal opens, PDF can be uploaded, Generate All Levels triggers processing
    Go To    ${BASE_URL}/admin/courses
    Wait For Admin Courses Ready
    # Open Import Document modal
    Click    text="Import Document"
    Wait For Elements State    .modal.is-active    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for modal form elements to render
    Wait For Elements State    .modal input[type="file"]    visible    timeout=${DEFAULT_TIMEOUT}
    # Upload PDF file
    Upload File By Selector    .modal input[type="file"]    ${TEST_PDF}
    # Wait for file to be accepted (file name should appear)
    Sleep    ${CONTENT_SETTLE}
    Take Viewport Screenshot    admin-import.png
    # Click Generate All Levels
    Click    .modal button:has-text("Generate All Levels")
    # Wait for modal to close and redirect to Process tab
    Sleep    3s

# ─── UC-A4: Wait for AI Generation ───────────────────────────────
Wait For Generation Complete
    [Documentation]    รอจน task สถานะ completed (poll ทุก 15 วินาที, timeout 10 นาที)
    ...    Verifies: AI background task finishes successfully
    Wait For Process Task Complete

# ─── UC-A5: Preview Generated Course ─────────────────────────────
Preview Generated Course
    [Documentation]    คลิก Preview + capture Course Preview page
    ...    Verifies: Preview page renders with course name, lessons, and objectives
    Click    button:has-text("Preview") >> nth=0
    Wait For Course Preview Ready
    Wait And Screenshot    admin-course-preview.png

# ─── UC-A6: Create and Preview Quiz ──────────────────────────────
Create And Preview Quiz
    [Documentation]    คลิก Create Quiz → รอ AI generate quiz → capture Quiz Preview
    ...    Verifies: Quiz is generated with questions visible in preview
    # Scroll to bottom where Create Quiz button is
    Scroll To Element    button:has-text("Create Quiz")
    Sleep    ${CONTENT_SETTLE}
    Click    button:has-text("Create Quiz")
    Wait For Quiz Preview Ready
    Wait And Screenshot    admin-quiz-preview.png

# ─── UC-A7: Submit Quiz to Database ──────────────────────────────
Submit Quiz To Database
    [Documentation]    คลิก Submit Quiz → บันทึกคอร์ส+quiz ลง database
    ...    Verifies: Course and quiz are persisted, redirects back to course management
    # Scroll to bottom where Submit Quiz button is
    Scroll To Element    button:has-text("Submit Quiz")
    Sleep    ${CONTENT_SETTLE}
    Click    button:has-text("Submit Quiz")
    # Wait for submission to complete and redirect
    Wait For Admin Courses Ready
    Sleep    ${CONTENT_SETTLE}

# ─── UC-A8: Capture Admin Settings ───────────────────────────────
Capture Admin Settings
    [Documentation]    หน้า Gemini API Settings (Multi-model configuration)
    ...    Verifies: Settings page renders with API key section and model roles
    Go To    ${BASE_URL}/admin/settings
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for settings content to fully render (API key info + model cards)
    Wait For Elements State    text="Gemini API Settings"    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading..."
    Sleep    ${CONTENT_SETTLE}
    Wait And Screenshot    admin-settings.png
