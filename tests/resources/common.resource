*** Settings ***
Library    Browser    auto_closing_level=SUITE
Library    Process

*** Variables ***
${BASE_URL}           http://localhost:3000
${API_URL}            http://localhost:5000
${SCREENSHOT_DIR}     ${CURDIR}/../../images
${BROWSER}            chromium
${HEADLESS}           true
${VIEWPORT_WIDTH}     1920
${VIEWPORT_HEIGHT}    1080

# Credentials - Admin (exists by default)
${ADMIN_EMAIL}        admin@admin.com
${ADMIN_PASSWORD}     admin

# Credentials - Test User (created by admin during test)
${USER_EMAIL}         testuser@robot.com
${USER_DEFAULT_PWD}   haionetime1234
${USER_NEW_PWD}       newpass123
${USER_USERNAME}      testrobot
${USER_FULLNAME}      Test Robot

# Timeouts
${DEFAULT_TIMEOUT}    30s
${LONG_TIMEOUT}       600s
${ANIMATION_WAIT}     0.5s
${CONTENT_SETTLE}     1s

# Test PDF path
${TEST_PDF}           ${CURDIR}/../test.pdf

*** Keywords ***
# ═══════════════════════════════════════════════════════════════════
# Setup / Cleanup
# ═══════════════════════════════════════════════════════════════════
Cleanup Test User
    [Documentation]    Delete existing test user via API so it can be recreated fresh
    ${script}=    Set Variable    ${CURDIR}/cleanup_user.py
    ${result}=    Run Process    python    ${script}    ${API_URL}    ${ADMIN_EMAIL}    ${ADMIN_PASSWORD}    ${USER_EMAIL}
    Log    ${result.stdout}

Open Browser To App
    [Documentation]    Open browser with consistent viewport for screenshots
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': ${VIEWPORT_WIDTH}, 'height': ${VIEWPORT_HEIGHT}}
    New Page    ${BASE_URL}
    Set Browser Timeout    ${DEFAULT_TIMEOUT}

# ═══════════════════════════════════════════════════════════════════
# Screenshot Helpers
# ═══════════════════════════════════════════════════════════════════
Take Full Page Screenshot
    [Documentation]    Take a full-page screenshot and save to images folder
    [Arguments]    ${filename}
    Take Screenshot    ${SCREENSHOT_DIR}/${filename}    fullPage=true

Take Viewport Screenshot
    [Documentation]    Take a viewport screenshot (what user sees)
    [Arguments]    ${filename}
    Take Screenshot    ${SCREENSHOT_DIR}/${filename}    fullPage=false

Wait And Screenshot
    [Documentation]    Wait for content to settle then take screenshot (replaces Sleep-based approach)
    [Arguments]    ${filename}    ${full_page}=true
    Sleep    ${CONTENT_SETTLE}
    IF    '${full_page}' == 'true'
        Take Full Page Screenshot    ${filename}
    ELSE
        Take Viewport Screenshot    ${filename}
    END

Scroll To Element And Screenshot
    [Documentation]    Scroll element into view then take viewport screenshot
    [Arguments]    ${selector}    ${filename}
    Scroll To Element    ${selector}
    Sleep    ${CONTENT_SETTLE}
    Take Viewport Screenshot    ${filename}

# ═══════════════════════════════════════════════════════════════════
# Login Keywords
# ═══════════════════════════════════════════════════════════════════
Login As Admin
    [Documentation]    Login with admin credentials and wait for admin page
    Go To    ${BASE_URL}/login
    Wait For Elements State    .login-form-card    visible    timeout=${DEFAULT_TIMEOUT}
    Fill Text    input[type="text"]    ${ADMIN_EMAIL}
    Fill Text    input[type="password"]    ${ADMIN_PASSWORD}
    Click    button[type="submit"]
    Wait For Navigation    /admin

Login As User
    [Documentation]    Login with test user credentials (after first-time setup)
    Go To    ${BASE_URL}/login
    Wait For Elements State    .login-form-card    visible    timeout=${DEFAULT_TIMEOUT}
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_NEW_PWD}
    Click    button[type="submit"]
    Wait For Navigation    /home

Login As New User
    [Documentation]    Login with newly created user (default password) -> redirect to /first-time-setup
    Go To    ${BASE_URL}/login
    Wait For Elements State    .login-form-card    visible    timeout=${DEFAULT_TIMEOUT}
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_DEFAULT_PWD}
    Click    button[type="submit"]
    Wait For Navigation    /first-time-setup

# ═══════════════════════════════════════════════════════════════════
# Navigation Wait Keywords
# ═══════════════════════════════════════════════════════════════════
Wait For Navigation
    [Documentation]    Wait until URL contains expected path
    [Arguments]    ${expected_path}
    Wait For Condition    url    contains    ${expected_path}    timeout=${DEFAULT_TIMEOUT}

# ═══════════════════════════════════════════════════════════════════
# Content-Ready Wait Keywords (wait for ACTUAL content, not just shell)
# ═══════════════════════════════════════════════════════════════════
Wait Until Loading Text Gone
    [Documentation]    Wait until a loading indicator text element is no longer visible.
    ...               Uses a try/catch pattern — if element never existed, that's fine.
    [Arguments]    ${loading_selector}    ${timeout}=${DEFAULT_TIMEOUT}
    ${elements}=    Get Elements    ${loading_selector}
    IF    len($elements) > 0
        Wait For Elements State    ${loading_selector}    hidden    timeout=${timeout}
    END

Wait For Login Page Ready
    [Documentation]    Wait for login form to be fully rendered and interactive
    Wait For Elements State    .login-form-card    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    input[type="text"]    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    button[type="submit"]    visible    timeout=${DEFAULT_TIMEOUT}

Wait For Dashboard Ready
    [Documentation]    Wait for Dashboard content to fully load (not just navbar shell)
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for the course cards container to appear
    Wait For Elements State    .home-courses-card >> nth=0    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for loading text inside courses section to disappear
    Wait Until Loading Text Gone    text="Loading courses..."
    # Allow animations/transitions to complete
    Sleep    ${CONTENT_SETTLE}

Wait For All Courses Ready
    [Documentation]    Wait for All Courses page with course cards fully rendered
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for course grid to have actual course cards
    Wait For Elements State    .columns.is-multiline .column.is-4 >> nth=0    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading courses..."
    Sleep    ${CONTENT_SETTLE}

Wait For Course Detail Ready
    [Documentation]    Wait for course detail page with actual course data rendered
    # Wait for loading screen to disappear
    Wait Until Loading Text Gone    text="Loading course details..."
    # Wait for actual content
    Wait For Elements State    .course-header-card    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    .lesson-item >> nth=0    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${CONTENT_SETTLE}

Wait For Lesson Page Ready
    [Documentation]    Wait for lesson page with actual content rendered (not loading state)
    # Wait for initial loading to finish
    Wait Until Loading Text Gone    text="Loading lesson..."    timeout=${DEFAULT_TIMEOUT}
    # Wait for content card to be visible
    Wait For Elements State    .lesson-content-card    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for navigation loading to finish (in case of lesson-to-lesson navigation)
    Wait Until Loading Text Gone    text="Loading lesson content..."
    # Wait for lesson text/video/image content to render
    Sleep    ${CONTENT_SETTLE}

Wait For Quiz Page Ready
    [Documentation]    Wait for quiz questions to be fully rendered
    Wait Until Loading Text Gone    text="Loading quiz..."    timeout=30s
    Wait For Elements State    .question-card    visible    timeout=30s
    Sleep    ${CONTENT_SETTLE}

Wait For Quiz Completed Ready
    [Documentation]    Wait for quiz completion page with score and AI analysis
    # After submit, AI evaluates answers — this can take time
    Wait For Elements State    .quiz-complete-card    visible    timeout=120s
    Sleep    ${CONTENT_SETTLE}

Wait For Quiz Result Page Ready
    [Documentation]    Wait for Quiz Result page (accessed via Quiz Result button)
    Wait Until Loading Text Gone    text="Loading quiz result..."    timeout=60s
    Wait For Elements State    .quiz-complete-card    visible    timeout=60s
    Sleep    ${CONTENT_SETTLE}

Wait For Admin Page Ready
    [Documentation]    Wait for any admin page to load with actual content (not just container)
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Wait Until Loading Text Gone    text="Loading users..."
    Sleep    ${CONTENT_SETTLE}

Wait For Admin Courses Ready
    [Documentation]    Wait for admin courses page with course cards or process tab content
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${CONTENT_SETTLE}

Wait For Admin Detail Ready
    [Documentation]    Wait for admin detail page (course or user) with tabs and data
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for tabs to render (indicates data has been fetched)
    ${has_boxed_tabs}=    Get Elements    .tabs.is-boxed
    ${has_toggle_tabs}=    Get Elements    .tabs.is-toggle
    IF    len($has_boxed_tabs) > 0
        Wait For Elements State    .tabs.is-boxed    visible    timeout=${DEFAULT_TIMEOUT}
    ELSE IF    len($has_toggle_tabs) > 0
        Wait For Elements State    .tabs.is-toggle    visible    timeout=${DEFAULT_TIMEOUT}
    END
    # Wait for loading indicators inside to disappear
    Wait Until Loading Text Gone    text="Loading..."
    Sleep    ${CONTENT_SETTLE}

Wait For Course Preview Ready
    [Documentation]    Wait for Course Preview page to render (after clicking Preview button)
    # Wait for Course Preview specific content (not just admin shell)
    Wait For Elements State    button:has-text("Back to Courses")    visible    timeout=${LONG_TIMEOUT}
    # Wait for the tabs area with course content
    Wait For Elements State    .tabs.is-boxed    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${CONTENT_SETTLE}

Wait For Quiz Preview Ready
    [Documentation]    Wait for Quiz Preview page to render (after Create Quiz AI generation)
    # Wait for Quiz Preview specific content
    Wait For Elements State    button:has-text("Back to Course Preview")    visible    timeout=${LONG_TIMEOUT}
    Wait For Elements State    .tabs.is-boxed    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${CONTENT_SETTLE}

Wait For Process Task Complete
    [Documentation]    Poll/refresh Process tab until Preview button appears (task completed)
    [Arguments]    ${max_wait}=600
    FOR    ${i}    IN RANGE    40
        ${preview_btns}=    Get Elements    button:has-text("Preview")
        IF    len($preview_btns) > 0    BREAK
        Sleep    15s
        Keyboard Key    press    F5
        Sleep    3s
    END
    # Ensure Preview button is fully interactive
    Wait For Elements State    button:has-text("Preview")    visible    timeout=${DEFAULT_TIMEOUT}
