*** Settings ***
Documentation    Capture screenshots ของหน้า Login และ First Time Setup
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
    [Documentation]    หน้าตั้งค่าแรกเข้า (ต้องมี user ที่ is_auth=false)
    [Tags]    requires-first-time-user
    # Login with first-time user (is_auth=false)
    Go To    ${BASE_URL}/login
    Wait For Elements State    input[type="text"]    visible
    Fill Text    input[type="text"]    ${USER_EMAIL}
    Fill Text    input[type="password"]    ${USER_PASSWORD}
    Click    button[type="submit"]
    # Wait for redirect to first-time-setup
    Wait For Condition    url    should contain    /first-time-setup    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}
    Wait And Screenshot    first-time-setup.png
