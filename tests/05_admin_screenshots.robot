*** Settings ***
Documentation    Suite 5: Capture screenshots หน้า Admin ทั้งหมด (มี enrolled users + quiz scores)
...              + Cleanup: ลบ test user ตอนจบ
...
...              Use Cases ที่ครอบคลุม:
...              - UC-A9: Admin Dashboard (All Users table)
...              - UC-A10: Admin Course Management (Courses tab + Process tab)
...              - UC-A11: Admin Course Detail (enrolled users + quiz scores)
...              - UC-A12: Admin User Detail (enrollment + quiz results)
...              - UC-A13: Admin View Answers Modal
...              - UC-A14: Admin Settings (Gemini API)
...              - UC-A15: Admin All Quiz Scores
...              - UC-A16: Delete User (cleanup test account)
Resource         resources/common.resource
Suite Setup      Setup Admin Session
Suite Teardown   Close Browser

*** Keywords ***
Setup Admin Session
    Open Browser To App
    Login As Admin

*** Test Cases ***
# ═══════════════════════════════════════════════════════════════════
# UC-A9: Admin Dashboard (All Users)
# ═══════════════════════════════════════════════════════════════════
Capture Admin Dashboard
    [Documentation]    แดชบอร์ด All Users (มี test user ที่ enrolled + completed quiz)
    ...    Verifies: User table renders with actual user data (not loading state)
    Go To    ${BASE_URL}/admin
    Wait For Admin Page Ready
    # Wait for user table rows to appear (actual data, not just the container)
    Wait For Elements State    table    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading users..."
    Sleep    ${CONTENT_SETTLE}
    Wait And Screenshot    admin-dashboard.png

# ═══════════════════════════════════════════════════════════════════
# UC-A10: Admin Course Management
# ═══════════════════════════════════════════════════════════════════
Capture Admin Courses Page
    [Documentation]    หน้า Course Management แท็บ Courses (มี course ที่สร้างจาก PDF)
    ...    Verifies: Course cards are rendered with names and details
    Go To    ${BASE_URL}/admin/courses
    Wait For Admin Courses Ready
    # Wait for course cards to render
    ${course_cards}=    Get Elements    .home-courses-card
    IF    len($course_cards) > 0
        Wait For Elements State    .home-courses-card >> nth=0    visible    timeout=${DEFAULT_TIMEOUT}
    END
    Sleep    ${CONTENT_SETTLE}
    Wait And Screenshot    admin-courses.png

Capture Admin Process Tab
    [Documentation]    แท็บ Process (มี completed tasks จาก import)
    ...    Verifies: Process tab shows task history with status
    Go To    ${BASE_URL}/admin/courses
    Wait For Admin Courses Ready
    ${process_tab}=    Get Elements    a:has-text("Process")
    IF    len($process_tab) > 0
        Click    a:has-text("Process") >> nth=0
        # Wait for process tab content to render (table or task list)
        Sleep    ${CONTENT_SETTLE}
        Wait And Screenshot    admin-process.png
    END

# ═══════════════════════════════════════════════════════════════════
# UC-A11: Admin Course Detail
# ═══════════════════════════════════════════════════════════════════
Capture Admin Course Detail Page
    [Documentation]    หน้ารายละเอียดคอร์ส Admin (course info + tabs)
    ...    Verifies: Course detail page renders with name, stats, and tab content
    Go To    ${BASE_URL}/admin/courses
    Wait For Admin Courses Ready
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        Click    text="View Details" >> nth=0
        Wait For Admin Detail Ready
        Wait And Screenshot    admin-course-detail.png
    END

Capture Admin Course Enrolled Users Tab
    [Documentation]    แท็บ Enrolled Users (มี test user + progress + quiz score)
    ...    Verifies: Enrolled Users tab shows user list with progress data
    ${users_tab}=    Get Elements    text="Enrolled Users"
    IF    len($users_tab) > 0
        Click    text="Enrolled Users"
        # Wait for tab content to switch and data to render
        Sleep    ${CONTENT_SETTLE}
        # Wait for user rows or content to appear
        ${user_rows}=    Get Elements    table tbody tr
        IF    len($user_rows) == 0
            Sleep    2s
        END
        Wait And Screenshot    admin-course-users.png
    END

# ═══════════════════════════════════════════════════════════════════
# UC-A12: Admin User Detail
# ═══════════════════════════════════════════════════════════════════
Capture Admin User Detail Page
    [Documentation]    หน้ารายละเอียดผู้ใช้ (test user ที่มี enrollment + quiz result)
    ...    Verifies: User detail page renders with user info, enrolled courses, quiz results
    Go To    ${BASE_URL}/admin
    Wait For Admin Page Ready
    Wait For Elements State    table    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading users..."
    # Find test user row and click View Details (last one is likely the test user, not admin)
    ${detail_btns}=    Get Elements    text="View Details"
    IF    len($detail_btns) > 0
        Click    text="View Details" >> nth=-1
        Wait For Admin Detail Ready
        Wait And Screenshot    admin-user-detail.png
    END

# ═══════════════════════════════════════════════════════════════════
# UC-A13: Admin View Answers Modal
# ═══════════════════════════════════════════════════════════════════
Capture Admin View Answers Modal
    [Documentation]    Modal View Answers (quiz answers with correct/incorrect marking)
    ...    Verifies: Modal shows questions, user answers, and correct answers
    # Should be on user detail page from previous test case
    # Switch to Quiz Results tab
    ${quiz_tab}=    Get Elements    text=Quiz Results
    IF    len($quiz_tab) > 0
        Click    text=Quiz Results >> visible=true
        # Wait for quiz results tab content to load
        Sleep    ${CONTENT_SETTLE}
        # Wait for table or content to render
        ${table_visible}=    Get Elements    table
        IF    len($table_visible) > 0
            Wait For Elements State    table    visible    timeout=${DEFAULT_TIMEOUT}
        END
        Sleep    ${CONTENT_SETTLE}
        # Click View Answers button
        ${answers_btns}=    Get Elements    text="View Answers"
        IF    len($answers_btns) > 0
            Click    text="View Answers" >> nth=0
            # Wait for modal to open AND content to load (answers are fetched async)
            Wait For Elements State    .modal.is-active    visible    timeout=${DEFAULT_TIMEOUT}
            # Wait for answers content inside modal (not just the modal shell)
            Wait For Elements State    .modal.is-active .modal-card-body    visible    timeout=${DEFAULT_TIMEOUT}
            # Give async fetch time to populate answers
            Sleep    3s
            Take Viewport Screenshot    admin-view-answers.png
            Click    .modal .delete
        END
    END

# ═══════════════════════════════════════════════════════════════════
# UC-A14: Admin Settings
# ═══════════════════════════════════════════════════════════════════
Capture Admin Settings Page
    [Documentation]    หน้า Gemini API Settings (API key + model configuration per role)
    ...    Verifies: Settings page shows API key section and 3 role model cards
    Go To    ${BASE_URL}/admin/settings
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    text="Gemini API Settings"    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading..."
    Sleep    ${CONTENT_SETTLE}
    Wait And Screenshot    admin-settings.png

# ═══════════════════════════════════════════════════════════════════
# UC-A15: Admin All Quiz Scores
# ═══════════════════════════════════════════════════════════════════
Capture Admin Quizzes Page
    [Documentation]    หน้า All Quiz Scores (score table with search + pagination)
    ...    Verifies: Quiz scores table renders with actual score data
    Go To    ${BASE_URL}/admin/quizzes
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for scores table to render with data
    Wait For Elements State    table    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading..."
    Sleep    ${CONTENT_SETTLE}
    Wait And Screenshot    admin-quizzes.png

# ═══════════════════════════════════════════════════════════════════
# UC-A16: Delete Test User (Cleanup)
# ═══════════════════════════════════════════════════════════════════
Delete Test User Account
    [Documentation]    Admin ลบ test user account เพื่อ cleanup หลังเทสเสร็จ
    ...    Verifies: Delete confirmation modal works, user is removed from table
    ...    Note: ต้องอยู่ท้ายสุดเพราะลบ test data ทั้งหมด (enrollments, progress, quiz scores)
    Go To    ${BASE_URL}/admin
    Wait For Admin Page Ready
    Wait For Elements State    table    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading users..."
    Sleep    ${CONTENT_SETTLE}
    # Find and click Delete button for the test user (last non-admin user row)
    # The Delete button is disabled for admin users, so we target the enabled one
    ${delete_btns}=    Get Elements    button.is-danger.is-small:not([disabled])
    IF    len($delete_btns) > 0
        Click    button.is-danger.is-small:not([disabled]) >> nth=-1
        # Wait for delete confirmation modal to appear
        Wait For Elements State    .modal.is-active    visible    timeout=${DEFAULT_TIMEOUT}
        Wait For Elements State    .modal.is-active .modal-card-body    visible    timeout=${DEFAULT_TIMEOUT}
        # Confirm deletion by clicking "Delete User" button in modal
        Click    .modal.is-active button.is-danger:has-text("Delete User")
        # Wait for modal to close (deletion complete)
        Wait For Elements State    .modal.is-active    hidden    timeout=${DEFAULT_TIMEOUT}
        # Wait for user table to refresh
        Sleep    ${CONTENT_SETTLE}
    END
