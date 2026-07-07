*** Settings ***
Library    Browser    auto_closing_level=SUITE

*** Variables ***
${BASE_URL}           http://localhost:3000
${API_URL}            http://localhost:5000
${SCREENSHOT_DIR}     ${CURDIR}/../../images
${BROWSER}            chromium
${VIEWPORT_WIDTH}     1920
${VIEWPORT_HEIGHT}    1080

# Credentials - ใช้ข้อมูลจาก init_db
${ADMIN_EMAIL}        admin@admin.com
${ADMIN_PASSWORD}     admin
${USER_EMAIL}         user@test.com
${USER_PASSWORD}      password

# Timeouts
${DEFAULT_TIMEOUT}    15s
${ANIMATION_WAIT}     1.5s

*** Keywords ***
Open Browser To App
    [Documentation]    Open browser with consistent viewport for screenshots
    New Browser    ${BROWSER}    headless=true
    New Context    viewport={'width': ${VIEWPORT_WIDTH}, 'height': ${VIEWPORT_HEIGHT}}
    Set Browser Timeout    ${DEFAULT_TIMEOUT}

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

Login As Admin
    [Documentation]    Login with admin credentials
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${ADMIN_EMAIL}
    Fill Text    input[type="password"]    ${ADMIN_PASSWORD}
    Click    button[type="submit"]
    Wait For Navigation

Login As User
    [Documentation]    Login with user credentials
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_PASSWORD}
    Click    button[type="submit"]
    Wait For Navigation

Wait For Navigation
    [Documentation]    Wait until URL changes from login page
    Wait For Condition    url    should not contain    /login    timeout=${DEFAULT_TIMEOUT}

Wait For Page Load
    [Documentation]    Wait for page content to be visible (no loading spinners)
    Wait For Elements State    .navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}
