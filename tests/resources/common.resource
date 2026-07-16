*** Settings ***
Library    Browser    auto_closing_level=SUITE
Library    Process

*** Variables ***
${BASE_URL}           http://localhost:3000
${API_URL}            http://localhost:5000
${SCREENSHOT_DIR}     ${CURDIR}/../../images
${BROWSER}            chromium
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
${DEFAULT_TIMEOUT}    15s
${LONG_TIMEOUT}       600s
${ANIMATION_WAIT}     1.5s

# Test PDF path
${TEST_PDF}           ${CURDIR}/../test.pdf

*** Keywords ***
# ─── Setup / Cleanup ───────────────────────────────────────────────
Cleanup Test User
    [Documentation]    Delete existing test user via API so it can be recreated fresh
    ${script}=    Set Variable    ${CURDIR}/cleanup_user.py
    ${result}=    Run Process    python    ${script}    ${API_URL}    ${ADMIN_EMAIL}    ${ADMIN_PASSWORD}    ${USER_EMAIL}
    Log    ${result.stdout}

Open Browser To App
    [Documentation]    Open browser with consistent viewport for screenshots
    New Browser    ${BROWSER}    headless=true
    New Context    viewport={'width': ${VIEWPORT_WIDTH}, 'height': ${VIEWPORT_HEIGHT}}
    New Page    ${BASE_URL}
    Set Browser Timeout    ${DEFAULT_TIMEOUT}

# ─── Screenshot Helpers ────────────────────────────────────────────
Take Full Page Screenshot
    [Documentation]    Take a full-page screenshot and save to images folder
    [Arguments]    ${filename}
    Take Screenshot    ${SCREENSHOT_DIR}/${filename}    fullPage=true

Take Viewport Screenshot
    [Documentation]    Take a viewport screenshot (what user sees)
    [Arguments]    ${filename}
    Take Screenshot    ${SCREENSHOT_DIR}/${filename}    fullPage=false

Wait And Screenshot
    [Documentation]    Wait for page to stabilize then take screenshot
    [Arguments]    ${filename}    ${full_page}=true
    Sleep    ${ANIMATION_WAIT}
    IF    '${full_page}' == 'true'
        Take Full Page Screenshot    ${filename}
    ELSE
        Take Viewport Screenshot    ${filename}
    END

Scroll To Element And Screenshot
    [Documentation]    Scroll element into view then take viewport screenshot
    [Arguments]    ${selector}    ${filename}
    Scroll To Element    ${selector}
    Sleep    0.5s
    Take Viewport Screenshot    ${filename}

# ─── Login Keywords ────────────────────────────────────────────────
Login As Admin
    [Documentation]    Login with admin credentials
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${ADMIN_EMAIL}
    Fill Text    input[type="password"]    ${ADMIN_PASSWORD}
    Click    button[type="submit"]
    Wait For Navigation    /admin

Login As User
    [Documentation]    Login with test user credentials (after first-time setup)
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_NEW_PWD}
    Click    button[type="submit"]
    Wait For Navigation    /home

Login As New User
    [Documentation]    Login with newly created user (default password, will redirect to first-time-setup)
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_DEFAULT_PWD}
    Click    button[type="submit"]
    Wait For Navigation    /first-time-setup

# ─── Navigation Wait Keywords ──────────────────────────────────────
Wait For Navigation
    [Documentation]    Wait until URL contains expected path
    [Arguments]    ${expected_path}
    Wait For Condition    url    contains    ${expected_path}    timeout=${DEFAULT_TIMEOUT}

Wait For Page Load
    [Documentation]    Wait for page with navbar to be visible
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

# ─── Detail Page Wait Keywords (wait for actual content, not just shell) ───
Wait For Admin Detail Load
    [Documentation]    Wait for admin detail page content to fully render (course or user detail)
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    # Wait for tabs to render (indicates data fetched and rendered)
    ${has_boxed_tabs}=    Get Elements    .tabs.is-boxed
    ${has_toggle_tabs}=    Get Elements    .tabs.is-toggle
    IF    len($has_boxed_tabs) > 0
        Wait For Elements State    .tabs.is-boxed    visible    timeout=${DEFAULT_TIMEOUT}
    ELSE IF    len($has_toggle_tabs) > 0
        Wait For Elements State    .tabs.is-toggle    visible    timeout=${DEFAULT_TIMEOUT}
    END
    Sleep    ${ANIMATION_WAIT}

Wait For Course Detail Load
    [Documentation]    Wait for user course detail page content to fully render
    Wait For Elements State    .course-header-card    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    .lesson-item    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Lesson Page Load
    [Documentation]    Wait for lesson content to fully render (markdown content)
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    3s

Wait For Quiz Page Load
    [Documentation]    Wait for quiz questions to render
    Wait For Elements State    .question-card    visible    timeout=30s
    Sleep    ${ANIMATION_WAIT}

Wait For Course Preview Load
    [Documentation]    Wait for Course Preview conditional page to render (after AI generate)
    Wait For Elements State    text="Course Preview"    visible    timeout=${LONG_TIMEOUT}
    Wait For Elements State    .home-courses-card    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Quiz Preview Load
    [Documentation]    Wait for Quiz Preview conditional page to render (after Create Quiz)
    Wait For Elements State    text="Quiz Preview"    visible    timeout=${LONG_TIMEOUT}
    Wait For Elements State    .home-courses-card    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Quiz Result Load
    [Documentation]    Wait for quiz result page (score + AI analysis)
    Wait For Elements State    text=Quiz Completed    visible    timeout=60s
    Sleep    3s

Wait For Dashboard Load
    [Documentation]    Wait for dashboard content to fully load
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    .home-courses-card >> nth=0    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Process Task Complete
    [Documentation]    Poll/refresh Process tab until at least one task shows "completed" status
    [Arguments]    ${max_wait}=600
    FOR    ${i}    IN RANGE    40
        ${completed}=    Get Elements    text="completed"
        IF    len($completed) > 0    BREAK
        Sleep    15s
        Keyboard Key    press    F5
        Sleep    3s
    END
