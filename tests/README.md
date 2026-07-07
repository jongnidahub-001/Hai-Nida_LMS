# Robot Framework - Screenshot Capture for User Manual

ระบบ automated screenshot capture สำหรับสร้างรูปประกอบ USER_MANUAL.md

## วิธีติดตั้ง

```bash
# 1. สร้าง virtual environment (แนะนำ)
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 2. ติดตั้ง dependencies
pip install -r tests/requirements.txt

# 3. ติดตั้ง Browser Library (ดาวน์โหลด Playwright browsers)
rfbrowser init
```

## Prerequisites

ก่อนรัน test ต้องเตรียมระบบให้พร้อม:

1. **Backend** ต้องทำงานอยู่:
   ```bash
   cd backend
   python -m uvicorn app:app --reload --port 5000
   ```

2. **Frontend** ต้องทำงานอยู่:
   ```bash
   cd frontend
   npm start
   ```

3. **Database** ต้องมีข้อมูลตัวอย่าง:
   - มี admin user: `admin@admin.com` / `admin`
   - มี user ทั่วไปอย่างน้อย 1 คน (สำหรับ user flow)
   - มี course อย่างน้อย 1 course ที่มี lessons
   - มี quiz ใน course อย่างน้อย 1 ชุด
   - มี user ที่ enrolled ใน course (เพื่อ capture lesson/quiz pages)

## วิธีรัน

```bash
# รัน test ทั้งหมด (capture ทุกหน้า)
robot --outputdir tests/results tests/

# รันเฉพาะแต่ละ suite
robot --outputdir tests/results tests/01_login_screenshots.robot
robot --outputdir tests/results tests/02_user_screenshots.robot
robot --outputdir tests/results tests/03_admin_screenshots.robot

# รันเฉพาะ test ที่ไม่ต้องการ data พิเศษ
robot --outputdir tests/results --exclude requires-* tests/

# รันแบบ headed (เห็นหน้าจอ) สำหรับ debug
robot --outputdir tests/results --variable BROWSER:chromium --variable HEADLESS:false tests/
```

## โครงสร้างไฟล์

```
tests/
├── README.md                    # ไฟล์นี้
├── requirements.txt             # Python dependencies
├── resources/
│   └── common.resource          # Shared keywords & variables
├── 01_login_screenshots.robot   # Login & First-time Setup
├── 02_user_screenshots.robot    # User/Student flow
├── 03_admin_screenshots.robot   # Admin flow
└── results/                     # Test output (gitignored)
```

## รายการ Screenshots ที่จะ Capture

### Suite 01: Login Flow
| ไฟล์ | คำอธิบาย |
|------|----------|
| start.png | หน้าจอเริ่มต้น |
| login.png | หน้าล็อกอิน |
| login-error.png | ล็อกอินผิด |
| first-time-setup.png | ตั้งค่าแรกเข้า |

### Suite 02: User Flow
| ไฟล์ | คำอธิบาย |
|------|----------|
| dashboard.png | Dashboard ทั้งหมด |
| dashboard-featured.png | Featured Courses |
| dashboard-my-courses.png | MY COURSES + แท็บ |
| all-courses.png | หน้าคอร์สทั้งหมด |
| all-courses-cards.png | การ์ดคอร์ส |
| course-detail.png | รายละเอียดคอร์ส |
| course-detail-progress.png | Your Progress |
| lesson-page.png | หน้าบทเรียน |
| lesson-chat.png | Modal แชท AI |
| lesson-nav.png | ปุ่มลอย + นำทาง |
| quiz-taking.png | ทำแบบทดสอบ |
| quiz-questions.png | คำถามแบบต่างๆ |
| quiz-completed.png | Quiz Completed |

### Suite 03: Admin Flow
| ไฟล์ | คำอธิบาย |
|------|----------|
| admin-dashboard.png | All Users |
| admin-add-user.png | Modal เพิ่มผู้ใช้ |
| admin-courses.png | Course Management |
| admin-process.png | Process tab |
| admin-import.png | Modal Import Document |
| admin-course-detail.png | Course detail (admin) |
| admin-course-users.png | Enrolled Users tab |
| admin-user-detail.png | User detail |
| admin-view-answers.png | Modal View Answers |
| admin-settings.png | Gemini Settings |
| admin-quizzes.png | All Quiz Scores |

## Configuration

ปรับค่าได้ใน `resources/common.resource`:

| Variable | Default | Description |
|----------|---------|-------------|
| `${BASE_URL}` | http://localhost:3000 | Frontend URL |
| `${API_URL}` | http://localhost:5000 | Backend API URL |
| `${BROWSER}` | chromium | Browser (chromium/firefox/webkit) |
| `${VIEWPORT_WIDTH}` | 1920 | ความกว้างหน้าจอ |
| `${VIEWPORT_HEIGHT}` | 1080 | ความสูงหน้าจอ |
| `${ADMIN_EMAIL}` | admin@admin.com | Admin email |
| `${ADMIN_PASSWORD}` | admin | Admin password |
| `${USER_EMAIL}` | user@test.com | User email |
| `${USER_PASSWORD}` | password | User password |

## Troubleshooting

- **rfbrowser init ไม่สำเร็จ**: ลอง `pip install --upgrade robotframework-browser` แล้วรันใหม่
- **Test timeout**: เพิ่ม `${DEFAULT_TIMEOUT}` ใน common.resource
- **Missing screenshots**: บาง test ต้องมี data ใน database - ดูที่ tag `requires-*`
- **Browser ไม่เปิด**: ตรวจสอบว่ารัน `rfbrowser init` แล้ว
