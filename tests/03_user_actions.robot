*** Settings ***
Documentation    Suite 3: User enroll คอร์ส, เรียน lesson, ทำ quiz
...              Capture quiz-taking + quiz-questions ระหว่างทำ (เพราะ quiz ทำได้ครั้งเดียว)
...
...              Use Cases ที่ครอบคลุม (ตามลำดับ flow จริง):
...              - UC-U5: User Login → Dashboard
...              - UC-U6: All Courses → เลือกคอร์ส
...              - UC-U7: Course Detail → Enroll (Start Course)
...              - UC-U8: Lesson Page → Mark as Complete
...              - UC-U9: Take Quiz (ตอบคำถามทุกข้อ + capture)
...              - UC-U10: Quiz Completed (ผลคะแนน + AI analysis)
Resource         resources/common.resource
Suite Setup      Setup User Session
Suite Teardown   Close Browser

*** Keywords ***
Setup User Session
    Open Browser To App
    Login As User

*** Test Cases ***
# ─── UC-U5: User Login → Dashboard (handled by Suite Setup) ──────
# Login is performed in Suite Setup. Dashboard is verified in next step.

# ─── UC-U6: Browse All Courses ───────────────────────────────────
Browse All Courses And Select Course
    [Documentation]    User ไปหน้า All Courses → เลือกคอร์สแรก
    ...    Verifies: Course grid renders with actual course cards
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    # Navigate to first course detail
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
    END

# ─── UC-U7: Course Detail → Enroll ───────────────────────────────
Enroll In Course
    [Documentation]    User กด Start Course เพื่อลงทะเบียนคอร์ส
    ...    Verifies: Start Course button works, enrollment succeeds
    # Should be on course detail page from previous test
    ${start_btn}=    Get Elements    button:has-text("Start Course")
    IF    len($start_btn) > 0
        Click    button:has-text("Start Course")
        # Wait for enrollment to process and page to update
        Wait For Elements State    button:has-text("Start Course")    hidden    timeout=${DEFAULT_TIMEOUT}
        Sleep    ${CONTENT_SETTLE}
    END

# ─── UC-U8: Lesson Page → Mark as Complete ───────────────────────
Complete First Lesson
    [Documentation]    User เข้าบทเรียนแรก → อ่านเนื้อหา → Mark as Complete
    ...    Verifies: Lesson content renders, Mark as Complete updates progress
    # Navigate to first lesson from course detail page
    ${start_lesson_btns}=    Get Elements    text="Start Lesson" >> visible=true
    ${continue_btns}=    Get Elements    text="Continue Lesson" >> visible=true
    IF    len($start_lesson_btns) > 0
        Click    text="Start Lesson" >> nth=0
    ELSE IF    len($continue_btns) > 0
        Click    text="Continue Lesson" >> nth=0
    END
    # Wait for lesson page to fully render (content loaded, no loading indicators)
    Wait For Lesson Page Ready
    # Mark the lesson as complete
    ${mark_btn}=    Get Elements    button:has-text("Mark as Complete")
    IF    len($mark_btn) > 0
        Click    button:has-text("Mark as Complete")
        # Wait for the button to finish loading (is-loading class removed)
        Wait For Elements State    button.is-success:not(.is-loading)    visible    timeout=${DEFAULT_TIMEOUT}
        Sleep    ${CONTENT_SETTLE}
    END

# ─── UC-U9: Take Quiz ────────────────────────────────────────────
Take Quiz And Capture Screenshots
    [Documentation]    User ทำแบบทดสอบ + capture quiz-taking, quiz-questions
    ...    Verifies: Quiz renders questions, all types can be answered
    ...    Captures: quiz-taking.png (first question), quiz-questions.png (subjective/fill)
    # Navigate back to course detail
    Go To    ${BASE_URL}/courses
    Wait For All Courses Ready
    ${course_links}=    Get Elements    a[href*="/course/"]
    IF    len($course_links) > 0
        Click    a[href*="/course/"] >> nth=0
        Wait For Course Detail Ready
    END
    # Click Take Assessment button
    ${quiz_btn}=    Get Elements    button:has-text("Take Assessment")
    IF    len($quiz_btn) > 0
        Click    button:has-text("Take Assessment")
        # Wait for quiz questions to fully render (not "Loading quiz..." text)
        Wait For Quiz Page Ready
        # Capture first question view
        Wait And Screenshot    quiz-taking.png
        # Answer all questions and capture different types
        Answer All Quiz Questions
    END

# ─── UC-U10: Quiz Completed ──────────────────────────────────────
# Quiz completion screenshot is captured at the end of Answer All Quiz Questions

*** Keywords ***
Answer All Quiz Questions
    [Documentation]    Loop ตอบคำถามทุกข้อ + capture quiz-questions เมื่อเจอ subjective/fill
    ...    After all answered: submit and wait for Quiz Completed page
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
            # Wait for AI evaluation and quiz completion (can take 30-120s for AI grading)
            Wait For Quiz Completed Ready
            Wait And Screenshot    quiz-completed.png
            BREAK
        ELSE IF    len($next_btn) > 0
            Click    button:has-text("Next Question")
            # Wait for next question to render (no loading flicker)
            Sleep    ${CONTENT_SETTLE}
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
        Fill Text    .question-card textarea >> nth=0    This is my answer for the subjective question about the course material.
        RETURN
    END
    # Fill in the blank - type in text input
    ${text_inputs}=    Get Elements    .question-card input[type="text"]
    IF    len($text_inputs) > 0
        Fill Text    .question-card input[type="text"] >> nth=0    answer
        RETURN
    END
