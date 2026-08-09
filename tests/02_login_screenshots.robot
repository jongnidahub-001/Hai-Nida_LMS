*** Settings ***
Documentation    Suite 2: Capture หน้า Login, Login Error, First Time Setup
...              (ต้องรัน 01_admin_setup ก่อน เพื่อสร้าง test user)
...
...              Use Cases ที่ครอบคลุม:
...              - UC-U1: หน้า Start (redirect to login)
...              - UC-U2: หน้า Login (ฟอร์มปกติ)
...              - UC-U3: Login Error (credential ผิด)
...              - UC-U4: First Time Setup (ผู้ใช้ใหม่ตั้งค่าแรกเข้า)
Resource         resources/common.resource
Suite Setup      Open Browser To App
Suite Teardown   Close Browser

*** Test Cases ***
# ─── UC-U1: Start Page (redirect to login) ───────────────────────
Capture Start Page
    [Documentation]    หน้าจอเริ่มต้นของระบบ (redirect ไป login)
    ...    Verifies: Unauthenticated users are redirected to login page
    Go To    ${BASE_URL}
    Wait For Login Page Ready
    Wait And Screenshot    start.png

# ─── UC-U2: Login Page ────────────────────────────────────────────
Capture Login Page
    [Documentation]    หน้าล็อกอินเต็มรูปแบบ (Username, Password, Sign In button)
    ...    Verifies: Login page renders with sidebar, branding, and form
    Go To    ${BASE_URL}/login
    Wait For Login Page Ready
    Wait And Screenshot    login.png

# ─── UC-U3: Login Error ───────────────────────────────────────────
Capture Login Error Page
    [Documentation]    หน้าล็อกอินเมื่อกรอกข้อมูลผิด → แสดง error message
    ...    Verifies: Invalid credentials show error message (class: .help.is-danger)
    Go To    ${BASE_URL}/login
    Wait For Login Page Ready
    Fill Text    input[type="text"]    wronguser@test.com
    Fill Text    input[type="password"]    wrongpassword
    Click    button[type="submit"]
    # Wait for error message to appear (not just button loading state to clear)
    Wait For Elements State    .help.is-danger    visible    timeout=${DEFAULT_TIMEOUT}
    # Ensure the button is no longer in loading state before screenshot
    Wait For Elements State    button[type="submit"]:not(.is-loading)    visible    timeout=${DEFAULT_TIMEOUT}
    Wait And Screenshot    login-error.png

# ─── UC-U4: First Time Setup ─────────────────────────────────────
Capture First Time Setup Page
    [Documentation]    หน้าตั้งค่าแรกเข้า + complete setup เพื่อให้ user พร้อมใช้ใน suite ถัดไป
    ...    Verifies: New user redirected to first-time-setup with form fields
    ...    Actions: Captures screenshot then completes setup (username, fullname, password)
    # Login with new user (default password) -> redirect to /first-time-setup
    Login As New User
    # Wait for the first-time-setup form to fully render
    Wait For Elements State    input[placeholder="Enter your username"]    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    button[type="submit"]    visible    timeout=${DEFAULT_TIMEOUT}
    Wait And Screenshot    first-time-setup.png
    # Complete first-time setup so user is ready for next suites
    Complete First Time Setup

*** Keywords ***
Complete First Time Setup
    [Documentation]    กรอกข้อมูล first-time setup → บันทึก → redirect ไปหน้า login
    Fill Text    input[placeholder="Enter your username"]    ${USER_USERNAME}
    Fill Text    input[placeholder="Enter your full name"]    ${USER_FULLNAME}
    Fill Text    input[placeholder*="new password"] >> nth=0    ${USER_NEW_PWD}
    Fill Text    input[placeholder*="Confirm"] >> nth=0    ${USER_NEW_PWD}
    Click    button[type="submit"]
    # Wait for redirect back to login page (setup complete → auto logout → login)
    Wait For Condition    url    contains    /login    timeout=${DEFAULT_TIMEOUT}
