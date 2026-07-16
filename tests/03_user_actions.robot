*** Settings ***
Documentation    Suite 3: User enroll คอร์ส, เรียน lesson, ทำ quiz
...              Capture quiz-taking + quiz-questions ระหว่างทำ (เพราะ quiz ทำได้ครั้งเดียว)
Resource         resources/common.resource
Suite Setup      Setup User Session
Suite Teardown   Close Browser

*** Keywords ***
Setup User Session
    Open Browser To App
    Login As User

*** Test Cases ***
Enroll In Course
    [Documentation]    User ไปหน้า All Courses → เข้าคอร์ส → กด Start Course (enroll)
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    # Click first course
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
        # Click Start Course to enroll
        ${start_btn}=    Get Elements    button:has-text("Start Course")
        IF    len($start_btn) > 0
            Click    button:has-text("Start Course")
            Sleep    2s
        END
    END

Complete First Lesson
    [Documentation]    User เข้าบทเรียนแรก → Mark as Complete
    # Should be on course detail after enroll
    ${lesson_btns}=    Get Elements    text="Start Lesson" >> visible=true
    IF    len($lesson_btns) > 0
        Click    text="Start Lesson" >> nth=0
    ELSE
        ${continue_btns}=    Get Elements    text="Continue Lesson" >> visible=true
        IF    len($continue_btns) > 0
            Click    text="Continue Lesson" >> nth=0
        END
    END
    Wait For Lesson Page Load
    # Mark as complete
    ${mark_btn}=    Get Elements    button:has-text("Mark as Complete")
    IF    len($mark_btn) > 0
        Click    button:has-text("Mark as Complete")
        Sleep    2s
    END

Take Quiz And Capture Screenshots
    [Documentation]    User ทำแบบทดสอบ + capture quiz-taking, quiz-questions
    # Navigate to course detail
    Go To    ${BASE_URL}/courses
    Wait For Page Load
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Load
    END
    # Click Take Assessment
    ${quiz_btn}=    Get Elements    button:has-text("Take Assessment")
    IF    len($quiz_btn) > 0
        Click    button:has-text("Take Assessment")
        Wait For Quiz Page Load
        # Capture first question
        Wait And Screenshot    quiz-taking.png
        # Answer all questions and capture different types
        Answer All Quiz Questions
    END

*** Keywords ***
Answer All Quiz Questions
    [Documentation]    Loop ตอบคำถามทุกข้อ + capture quiz-questions เมื่อเจอ subjective/fill
    ${captured_questions}=    Set Variable    ${FALSE}
    FOR    ${i}    IN RANGE    50
        # Check if we're still on quiz page with questions
        ${questions}=    Get Elements    .question-card
        IF    len($questions) == 0    BREAK
        # Try to answer current question
        Answer Current Question
        # Capture quiz-questions when we find subjective/fill type (capture once)
        IF    '${captured_questions}' == '${FALSE}'
            ${subjective}=    Get Elements    textarea
            ${fill}=    Get Elements    .question-card input[type="text"]
            IF    len($subjective) > 0 or len($fill) > 0
                Wait And Screenshot    quiz-questions.png
                ${captured_questions}=    Set Variable    ${TRUE}
            END
        END
        # Try to go to next question or submit
        ${next_btn}=    Get Elements    button:has-text("Next Question")
        ${submit_btn}=    Get Elements    button:has-text("Submit Quiz")
        IF    len($submit_btn) > 0
            Click    button:has-text("Submit Quiz")
            Sleep    5s
            BREAK
        ELSE IF    len($next_btn) > 0
            Click    button:has-text("Next Question")
            Sleep    1s
        ELSE
            BREAK
        END
    END

Answer Current Question
    [Documentation]    ตอบคำถามปัจจุบัน (เลือก choice / พิมพ์ข้อความ)
    # Multiple choice - click first radio/option
    ${radio_btns}=    Get Elements    .question-card input[type="radio"]
    IF    len($radio_btns) > 0
        Click    .question-card input[type="radio"] >> nth=0
        RETURN
    END
    # Subjective - type in textarea
    ${textareas}=    Get Elements    .question-card textarea
    IF    len($textareas) > 0
        Fill Text    .question-card textarea >> nth=0    This is my answer for the subjective question.
        RETURN
    END
    # Fill in the blank - type in text input
    ${text_inputs}=    Get Elements    .question-card input[type="text"]
    IF    len($text_inputs) > 0
        Fill Text    .question-card input[type="text"] >> nth=0    answer
        RETURN
    END
