*** Settings ***
Documentation    Suite 2: Capture หน้า Login, Login Error, First Time Setup
...              (ต้องรัน 01_admin_setup ก่อน เพื่อสร้าง test user)
Resource         resources/common.resource
Suite Setup      Open Browser To App
Suite Teardown   Close Browser

*** Test Cases ***
Capture Start Page
    [Documentation]    หน้าจอเริ่มต้นของระบบ (redirect ไป login)
    Go To    ${BASE_URL}
    Wait For Elements State    .login-form-card    visible
    Wait And Screenshot    start.png

Capture Login Page
    [Documentation]    หน้าล็อกอินเต็มรูปแบบ
    Go To    ${BASE_URL}/login
    Wait For Elements State    .login-form-card    visible
    Wait And Screenshot    login.png

Capture Login Error Page
    [Documentation]    หน้าล็อกอินเมื่อกรอกข้อมูลผิด
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    wronguser@test.com
    Fill Text    input[type="password"]    wrongpassword
    Click    button[type="submit"]
    Wait For Elements State    .help.is-danger    visible
    Wait And Screenshot    login-error.png

Capture First Time Setup Page
    [Documentation]    หน้าตั้งค่าแรกเข้า + complete setup เพื่อให้ user พร้อมใช้ใน suite ถัดไป
    # Login with new user (default password) -> redirect to /first-time-setup
    Login As New User
    Sleep    ${ANIMATION_WAIT}
    Wait And Screenshot    first-time-setup.png
    # Complete first-time setup
    Complete First Time Setup

*** Keywords ***
Complete First Time Setup
    [Documentation]    กรอกข้อมูล first-time setup
    Fill Text    input[placeholder="Enter your username"]    ${USER_USERNAME}
    Fill Text    input[placeholder="Enter your full name"]    ${USER_FULLNAME}
    Fill Text    input[placeholder*="new password"] >> nth=0    ${USER_NEW_PWD}
    Fill Text    input[placeholder*="Confirm"] >> nth=0    ${USER_NEW_PWD}
    Click    button[type="submit"]
    Wait For Condition    url    contains    /login    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}
