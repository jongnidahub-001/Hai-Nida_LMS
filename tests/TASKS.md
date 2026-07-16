# Robot Framework Test Restructure — Task List

## เป้าหมาย
Capture screenshots ให้ครบทุกรูปใน `USER_MANUAL.md` โดยมี data จริง (enrolled users, quiz scores, progress)

## Flow ใหม่ (5 Suites ตามลำดับ)

```
Suite 01 — Admin Setup       : admin login, สร้าง user, import PDF ผ่าน UI, รอ generate, submit course
Suite 02 — Login Screenshots : หน้า login, error, first-time setup
Suite 03 — User Actions      : user enroll, เรียน lesson, ทำ quiz (capture quiz ระหว่างทำ)
Suite 04 — User Screenshots  : capture dashboard/courses/lesson (มีข้อมูลแล้ว)
Suite 05 — Admin Screenshots : capture admin pages (มี enrolled users + quiz scores)
```

---

## Screenshots ทั้งหมดที่ต้อง capture (จาก USER_MANUAL.md)

| # | Filename | Capture จาก Suite | หมายเหตุ |
|---|----------|-------------------|----------|
| 1 | `start.png` | 02 | redirect ไป login |
| 2 | `login.png` | 02 | หน้า login เต็ม |
| 3 | `login-error.png` | 02 | กรอกผิด |
| 4 | `first-time-setup.png` | 02 | หน้า first-time setup |
| 5 | `dashboard.png` | 04 | dashboard full (มี enrolled course) |
| 6 | `dashboard-featured.png` | 04 | Featured Courses section |
| 7 | `dashboard-my-courses.png` | 04 | MY COURSES section (มี progress) |
| 8 | `all-courses.png` | 04 | หน้า All Courses |
| 9 | `all-courses-cards.png` | 04 | grid cards |
| 10 | `course-detail.png` | 04 | course detail (enrolled, มี progress) |
| 11 | `course-detail-progress.png` | 04 | Your Progress section |
| 12 | `lesson-page.png` | 04 | หน้าบทเรียน |
| 13 | `lesson-chat.png` | 04 | Chat modal |
| 14 | `lesson-nav.png` | 04 | floating chat + nav bar |
| 15 | `quiz-taking.png` | 03 | ขณะทำ quiz (ก่อน submit) |
| 16 | `quiz-questions.png` | 03 | คำถาม subjective/fill |
| 17 | `quiz-completed.png` | 04 | หน้า Quiz Result (หลัง submit) |
| 18 | `admin-dashboard.png` | 05 | All Users (มี test user) |
| 19 | `admin-add-user.png` | 01 | modal Add User |
| 20 | `admin-courses.png` | 05 | Course Management (มี course) |
| 21 | `admin-process.png` | 05 | Process tab (มี tasks) |
| 22 | `admin-import.png` | 01 | modal Import Document (with PDF selected) |
| 23 | `admin-course-preview.png` | 01 | Course Preview page (บทเรียน + ปุ่ม Edit/Create Quiz) |
| 24 | `admin-quiz-preview.png` | 01 | Quiz Preview page (คำถาม + ปุ่ม Submit Quiz) |
| 25 | `admin-course-detail.png` | 05 | course detail (มี enrolled users) |
| 26 | `admin-course-users.png` | 05 | Enrolled Users tab (มีข้อมูล) |
| 27 | `admin-user-detail.png` | 05 | user detail (มี enrollment+quiz) |
| 28 | `admin-view-answers.png` | 05 | modal View Answers |
| 29 | `admin-settings.png` | 05 | Gemini Settings |
| 30 | `admin-quizzes.png` | 05 | All Quiz Scores (มี score) |
| 31 | `use-case-diagram.png` | — | สร้างแยก (ไม่ใช่ screenshot) |

---

## รายละเอียดแต่ละ Suite

### Suite 01: `01_admin_setup.robot`
**จุดประสงค์:** Admin สร้างข้อมูลพื้นฐาน (user + course จาก PDF) ผ่าน UI ทั้งหมด

| Step | Action | Screenshot | Wait Condition |
|------|--------|-----------|----------------|
| 1 | Cleanup test user (API script) | — | — |
| 2 | Open Browser + Login Admin | — | URL contains `/admin` |
| 3 | Go to Admin Dashboard | — | `nav.navbar` visible |
| 4 | Click "Add User" → Fill email → Submit | `admin-add-user.png` | `.modal.is-active` visible |
| 5 | Go to Admin Courses | — | `nav.navbar` visible |
| 6 | Click "Import Document" | — | `.modal.is-active` visible |
| 7 | Upload `tests/test.pdf` ใน modal | `admin-import.png` | file input filled |
| 8 | Click "Generate All Levels" | — | modal closes, redirect to Process tab |
| 9 | **รอ tasks complete** (poll/refresh ทุก 15s) | — | task status badge = "completed" (timeout 5-10 นาที) |
| 10 | Click "Preview" บน task ที่เสร็จ | — | "Course Preview" heading visible |
| 11 | **Capture Course Preview** | `admin-course-preview.png` | page loaded with course data |
| 12 | *(Optional)* Expand lesson → Click Edit → type prompt → Regenerate → Save/Discard | — | ถ้าต้องการ capture edit flow |
| 13 | Click "Create Quiz" | — | loading → "Quiz Preview" heading visible |
| 14 | **Capture Quiz Preview** | `admin-quiz-preview.png` | page loaded with questions |
| 15 | *(Optional)* Expand question → Click Edit → type prompt → Regenerate → Save/Discard | — | ถ้าต้องการ capture edit flow |
| 16 | Click "Submit Quiz" | — | success notification / redirect to courses |
| 17 | Capture Admin Settings | `admin-settings.png` | `nav.navbar` visible |
| 18 | Close browser | — | — |

**Note:**
- Step 9 ใช้ loop refresh หน้าทุก 15 วินาที จนกว่า task จะ complete (timeout 10 นาที สำหรับ AI generation)
- Step 13 "Create Quiz" จะเรียก AI อีกรอบ ใช้เวลา ~1-3 นาที
- Import ผ่าน UI เพื่อให้ Process tab มี task data ให้ capture ใน Suite 05

---

### Suite 02: `02_login_screenshots.robot`
**จุดประสงค์:** Capture หน้า login ทั้งหมด + first-time setup

| Step | Action | Screenshot | Wait Condition |
|------|--------|-----------|----------------|
| 1 | Open Browser | — | — |
| 2 | Go to base URL | `start.png` | `.login-form-card` visible |
| 3 | Go to /login | `login.png` | `.login-form-card` visible |
| 4 | Fill wrong credentials + submit | `login-error.png` | `.help.is-danger` visible |
| 5 | Login as new user (default pwd) | `first-time-setup.png` | URL contains `/first-time-setup` |
| 6 | Fill form + Complete Setup | — | URL contains `/login` |
| 7 | Close browser | — | — |

---

### Suite 03: `03_user_actions.robot`
**จุดประสงค์:** User enroll + เรียน + ทำ quiz (capture quiz ระหว่างทำ)

| Step | Action | Screenshot | Wait Condition |
|------|--------|-----------|----------------|
| 1 | Open Browser + Login as User | — | URL contains `/home` |
| 2 | Go to /courses | — | `nav.navbar` visible |
| 3 | Click คอร์สที่ admin สร้าง | — | `.course-header-card` visible |
| 4 | Click "Start Course" (enroll) | — | page refresh, button changes |
| 5 | Click "Start Lesson" | — | lesson page loads |
| 6 | Click "Mark as Complete" | — | success feedback |
| 7 | Navigate back to course detail | — | `.course-header-card` visible |
| 8 | Click "Take Assessment" | — | quiz page loads |
| 9 | ตอบคำถามข้อแรก | `quiz-taking.png` | `.question-card` visible |
| 10 | Click Next → ตอบ + capture | `quiz-questions.png` | คำถามประเภทอื่น visible |
| 11 | ตอบคำถามที่เหลือทั้งหมด | — | loop จน submit ได้ |
| 12 | Click "Submit Quiz" | — | quiz result page loads |
| 13 | Close browser | — | — |

**Note:** ต้องตอบทุกข้อจริง (เลือก choice / พิมพ์ข้อความ) ก่อน submit ได้

---

### Suite 04: `04_user_screenshots.robot`
**จุดประสงค์:** Capture หน้า user ทั้งหมด (มีข้อมูลครบแล้ว)

| Step | Action | Screenshot | Wait Condition |
|------|--------|-----------|----------------|
| 1 | Open Browser + Login as User | — | URL contains `/home` |
| 2 | Dashboard full page | `dashboard.png` | `.home-courses-card` visible |
| 3 | Scroll to Featured Courses | `dashboard-featured.png` | `.home-overview-card` visible |
| 4 | Scroll to MY COURSES | `dashboard-my-courses.png` | `.home-courses-card` visible |
| 5 | Go to /courses | `all-courses.png` | `nav.navbar` visible |
| 6 | Scroll to course grid | `all-courses-cards.png` | `.columns.is-multiline` visible |
| 7 | Click คอร์ส (enrolled) | `course-detail.png` | `.course-header-card` visible |
| 8 | Scroll to progress card | `course-detail-progress.png` | `.course-progress-card` visible |
| 9 | Click lesson → lesson page | `lesson-page.png` | lesson content loads |
| 10 | Click "Chat with AI" | `lesson-chat.png` | `.chat-modal` visible |
| 11 | Close chat → scroll to floating btn | `lesson-nav.png` | `.floating-chat-button` visible |
| 12 | Go to course → Click "Quiz Result" | `quiz-completed.png` | quiz result page loads |
| 13 | Close browser | — | — |

---

### Suite 05: `05_admin_screenshots.robot`
**จุดประสงค์:** Capture หน้า admin ทั้งหมด (มี enrolled user + quiz score)

| Step | Action | Screenshot | Wait Condition |
|------|--------|-----------|----------------|
| 1 | Open Browser + Login as Admin | — | URL contains `/admin` |
| 2 | Admin Dashboard | `admin-dashboard.png` | `nav.navbar` + table visible |
| 3 | Go to /admin/courses | `admin-courses.png` | `nav.navbar` visible |
| 4 | Click Process tab | `admin-process.png` | process table visible |
| 5 | Go to /admin/courses → click View Details | `admin-course-detail.png` | `.admin-home-bg` + tabs visible |
| 6 | Click "Enrolled Users" tab | `admin-course-users.png` | table with user data |
| 7 | Go to /admin → click View Details (user) | `admin-user-detail.png` | `.admin-home-bg` + user info visible |
| 8 | Click "Quiz Results" tab → "View Answers" | `admin-view-answers.png` | `.modal.is-active` visible |
| 9 | Go to /admin/settings | `admin-settings.png` | `nav.navbar` visible |
| 10 | Go to /admin/quizzes | `admin-quizzes.png` | `nav.navbar` + table visible |
| 11 | Close browser | — | — |

---

## ไฟล์ที่ต้องสร้าง/แก้ไข

| ไฟล์ | Action | หมายเหตุ |
|------|--------|----------|
| `tests/resources/common.resource` | **แก้ไข** | เพิ่ม keywords: Wait For Process Complete, Answer Quiz Question, Wait For Course Preview, etc. |
| `tests/resources/cleanup_user.py` | **มีอยู่แล้ว ✓** | — |
| `tests/01_admin_setup.robot` | **เขียนใหม่** | แทนที่ไฟล์เดิม (admin setup + import + preview + submit) |
| `tests/02_login_screenshots.robot` | **แก้ไขเล็กน้อย** | ใช้ flow ที่ทำงานได้แล้ว |
| `tests/03_user_actions.robot` | **สร้างใหม่** | enroll + learn + quiz + capture ระหว่างทำ |
| `tests/04_user_screenshots.robot` | **สร้างใหม่** | capture user pages ที่มีข้อมูล |
| `tests/05_admin_screenshots.robot` | **สร้างใหม่** | capture admin pages ที่มีข้อมูล |
| `USER_MANUAL.md` | **อัปเดตแล้ว ✓** | เพิ่ม section 11.6 Course Preview + 11.7 Quiz Preview |

---

## วิธีรัน

```bash
# รันทั้งหมดตามลำดับ (ต้องรัน 01→02→03→04→05)
robot --outputdir tests/results tests/01_admin_setup.robot
robot --outputdir tests/results tests/02_login_screenshots.robot
robot --outputdir tests/results tests/03_user_actions.robot
robot --outputdir tests/results tests/04_user_screenshots.robot
robot --outputdir tests/results tests/05_admin_screenshots.robot

# หรือรันทั้งหมดใน folder (Robot จะ sort ตามชื่อไฟล์ = ลำดับถูก)
robot --outputdir tests/results tests/
```

---

## ข้อควรระวัง

1. **Import Document ใช้เวลา 3-5 นาที** (AI generate) — ต้อง set timeout สูง
2. **Create Quiz ใช้เวลาอีก 1-3 นาที** (AI generate) — ต้อง set timeout สูงเช่นกัน
3. **Quiz ทำได้ครั้งเดียว** — ต้อง capture ระหว่างทำใน suite 03
4. **ลำดับ suite สำคัญมาก** — suite 04/05 depend on data จาก 01/02/03
5. **test.pdf** อยู่ที่ `tests/test.pdf` — ใช้ `Upload File By Selector` keyword ของ Browser library
6. **Headless browser** อาจมีปัญหากับ file upload — ทดสอบก่อนว่า upload ได้
7. **Course Preview / Quiz Preview** เป็นหน้าที่ render condition (ไม่ใช่ route แยก) — ต้อง wait ด้วย text/element ไม่ใช่ URL

---

## ปัญหาที่ต้องแก้: หน้า Detail ทุกหน้า capture ก่อน content โหลดเสร็จ

### สาเหตุ
หน้าที่เป็น detail (admin course detail, admin user detail, course detail ฝั่ง user, lesson page, quiz page)
ทั้งหมดเป็น **client-side rendered** — เมื่อ navigate ไปหน้านั้น จะ render shell ก่อน (navbar/header)
แล้วค่อย fetch data จาก API → render content ทีหลัง

ถ้า Robot capture ตอนที่เห็น navbar แล้วแต่ content ยัง fetch ไม่เสร็จ จะได้ภาพว่างหรือแสดง "Loading..."

### หน้าที่มีปัญหานี้ + วิธีแก้

| หน้า | ปัญหา | Wait Element ที่ถูกต้อง (รอจนมี) |
|------|--------|----------------------------------|
| **Admin Course Detail** | capture เห็นแค่ `.admin-home-bg` แต่ไม่มีชื่อคอร์ส | รอ `.tabs.is-boxed` visible + text "Total Hours" visible |
| **Admin User Detail** | capture เห็นแค่ shell ไม่มีข้อมูล user | รอ `.tabs.is-toggle` visible + text "User Information" visible |
| **Admin Course Enrolled Users Tab** | tab content ยังไม่โหลด | Click tab → รอ `table.is-fullwidth` visible (ใน tab content) |
| **Admin View Answers Modal** | modal content ยังไม่โหลด (fetch answers async) | รอ `.modal.is-active` visible + text "Question 1" visible |
| **User Course Detail** | `.course-header-card` visible แต่ lessons ยังไม่โหลด | รอ `.course-header-card` + `.lesson-item` visible |
| **User Lesson Page** | navbar visible แต่ lesson content ยัง fetch | รอ `.lesson-content` หรือ `.content` ภายใน lesson area visible |
| **Course Preview (Admin)** | conditional render ไม่มี route | รอ text "Course Preview" + `.home-courses-card` visible |
| **Quiz Preview (Admin)** | conditional render ไม่มี route | รอ text "Quiz Preview" + `.home-courses-card` visible |
| **Quiz Taking (User)** | quiz questions fetch async | รอ `.question-card` visible |
| **Quiz Result (User)** | result + AI analysis fetch async | รอ text "Quiz Completed" หรือ score circle visible |
| **Dashboard (User)** | courses fetch async | รอ `.home-courses-card >> nth=0` visible (ทำอยู่แล้ว ✓) |

### Action Items สำหรับ `common.resource`

เพิ่ม/แก้ไข keywords ใน `common.resource`:

```robot
Wait For Admin Detail Load
    # ปัจจุบัน: รอแค่ .admin-home-bg → ไม่พอ
    # แก้เป็น: รอ .tabs.is-boxed (admin course) หรือ .tabs.is-toggle (admin user)
    Wait For Elements State    .admin-home-bg    visible    timeout=${DEFAULT_TIMEOUT}
    # รอ content จริง load (เลือก 1 ใน 2):
    ${has_boxed_tabs}=    Get Elements    .tabs.is-boxed
    ${has_toggle_tabs}=    Get Elements    .tabs.is-toggle
    IF    len($has_boxed_tabs) > 0
        Wait For Elements State    .tabs.is-boxed    visible    timeout=${DEFAULT_TIMEOUT}
    ELSE IF    len($has_toggle_tabs) > 0
        Wait For Elements State    .tabs.is-toggle    visible    timeout=${DEFAULT_TIMEOUT}
    END
    Sleep    ${ANIMATION_WAIT}

Wait For Course Detail Load
    # ปัจจุบัน: รอแค่ .course-header-card → อาจยังไม่มี lessons
    # แก้เป็น: รอ header + lesson list
    Wait For Elements State    .course-header-card    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    .lesson-item    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Lesson Page Load
    # ใหม่: รอ lesson content render จริง
    Wait For Elements State    nav.navbar    visible    timeout=${DEFAULT_TIMEOUT}
    Wait For Elements State    .content    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    2s    # lesson content มี markdown render อาจช้า

Wait For Quiz Page Load
    # ใหม่: รอ quiz questions render
    Wait For Elements State    .question-card    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Course Preview Load
    # ใหม่: รอ Course Preview conditional render
    Wait For Elements State    text="Course Preview"    visible    timeout=120s
    Wait For Elements State    .home-courses-card    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Quiz Preview Load
    # ใหม่: รอ Quiz Preview conditional render
    Wait For Elements State    text="Quiz Preview"    visible    timeout=180s
    Wait For Elements State    .home-courses-card    visible    timeout=${DEFAULT_TIMEOUT}
    Sleep    ${ANIMATION_WAIT}

Wait For Quiz Result Load
    # ใหม่: รอ quiz result page (มี score + analysis)
    Wait For Elements State    text=Quiz Completed    visible    timeout=30s
    Sleep    3s    # AI analysis อาจใช้เวลา render
```

### สรุป: ทุก suite ที่ capture หน้า detail ต้องใช้ wait keyword ที่ถูกต้อง

| Suite | Test Case | ใช้ keyword |
|-------|-----------|-------------|
| 01 | Course Preview | `Wait For Course Preview Load` |
| 01 | Quiz Preview | `Wait For Quiz Preview Load` |
| 03 | Quiz Taking | `Wait For Quiz Page Load` |
| 04 | Course Detail | `Wait For Course Detail Load` (แก้ให้รอ `.lesson-item` ด้วย) |
| 04 | Lesson Page | `Wait For Lesson Page Load` |
| 04 | Quiz Result | `Wait For Quiz Result Load` |
| 05 | Admin Course Detail | `Wait For Admin Detail Load` (แก้ให้รอ tabs + content) |
| 05 | Admin User Detail | `Wait For Admin Detail Load` |
| 05 | Admin View Answers | Wait `.modal.is-active` + text "Question 1" |
