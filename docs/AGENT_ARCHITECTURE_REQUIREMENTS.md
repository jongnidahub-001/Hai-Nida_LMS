# Agent Architecture Improvement Requirements

## Multi-Agent Hierarchical Architecture with Parallel Execution

---

## 1. สรุปภาพรวมการเปลี่ยนแปลง

ปรับ Architecture จาก **2-Agent RoundRobin** (Expert + Validator วนลูป) เป็น **Hierarchical Multi-Agent with Parallel Execution** (Planner → parallel Writers → Assembler) เพื่อเพิ่ม performance, quality, และ reliability

### เป้าหมาย

- **Latency**: ลด 2-3x (จาก ~60-90s เหลือ ~25-35s สำหรับ 6 lessons)
- **Token Efficiency**: ลด token waste 80% เมื่อ reject (แก้แค่ lesson ที่ fail ไม่ต้อง regenerate ทั้งหมด)
- **Quality**: Content คุณภาพสม่ำเสมอทุก lesson (ไม่ drop ท้ายๆ เพราะ output ยาว)
- **Reliability**: Isolated failure per lesson, max iterations guard, retry per-lesson
- **Flexibility**: Admin เลือก model แยกตาม role (Planner/Writer/Grader)

---

## 2. ไฟล์ที่ได้รับผลกระทบ

### Backend - Agent Modules (เขียนใหม่)

| ไฟล์ | สถานะ | สิ่งที่ต้องทำ |
|------|--------|-------------|
| `backend/agent/create_course/agent_autogen.py` | **เขียนใหม่** | เปลี่ยนจาก RoundRobin เป็น Planner→Writers→Assembler |
| `backend/agent/create_quiz/agent_autogen.py` | **เขียนใหม่** | เปลี่ยนจาก RoundRobin เป็น QuizPlanner→QuestionWriters→Assembler |
| `backend/agent/grader/agent_autogen.py` | **ลบ/รวม** | Dead code - ย้ายไปเป็น standalone grader service |

### Backend - Configuration (แก้ไข)

| ไฟล์ | สถานะ | สิ่งที่ต้องทำ |
|------|--------|-------------|
| `backend/gemini_config.py` | **แก้ไข** | เพิ่ม multi-model config (planner_model, writer_model, grader_model) |
| `backend/document_chunking.py` | **แก้ไข** | เพิ่ม `split_by_sections()` สำหรับ route document sections ไปแต่ละ lesson writer |

### Backend - API Layer (แก้ไข)

| ไฟล์ | สถานะ | สิ่งที่ต้องทำ |
|------|--------|-------------|
| `backend/app.py` | **แก้ไข** | ปรับ 7 endpoints + background task ให้ใช้ agent interface ใหม่ |

### Frontend (แก้ไข)

| ไฟล์ | สถานะ | สิ่งที่ต้องทำ |
|------|--------|-------------|
| `frontend/src/pages/AdminGeminiSettings.js` | **แก้ไข** | UI เลือก model แยก 3 roles |
| `frontend/src/pages/AdminAllCourse.js` | **แก้ไข** | LogCard รองรับ agent ใหม่ + progress per-lesson + background task UI |

---

## 3. Impact Analysis — ทุก Function ที่ได้รับผลกระทบ

### 3.1 `backend/agent/create_course/agent_autogen.py`

| Function/Class | การเปลี่ยนแปลง |
|---------------|----------------|
| `create_team_for_request()` | **ลบ** — แทนด้วย pipeline ใหม่ (planner → writers → assembler) |
| `create_model_client()` | **แก้** — แยกเป็น `create_planner_client()`, `create_writer_client()` |
| `_get_gemini_client()` | **แก้** — ใช้ model ตาม role |
| `CreateCourse.create_course()` | **เขียนใหม่** — เป็น multi-step pipeline: plan → parallel write → assemble |
| `CreateCourse.regenerate_lesson()` | **คงเดิม** (single LLM call, ใช้ writer model) |
| `CreateCourse.question_answer()` | **คงเดิม** (chat, ใช้ writer model) |
| `CreateCourse.evaluate()` | **คงเดิม** (ใช้ grader model) |
| `CreateCourse.suggest_course()` | **คงเดิม** (single LLM call) |
| `primary_agent_prompt` | **ลบ** — แทนด้วย prompts แยก: `planner_prompt`, `lesson_writer_prompt`, `lesson_reviewer_prompt` |
| `critic_agent_prompt` | **ลบ** — แทนด้วย `outline_reviewer_prompt`, `lesson_reviewer_prompt` |
| `FinalOutput` (Pydantic) | **คงเดิม** — output schema เดิมเพื่อ backward compatible กับ frontend/database |
| `Course`, `Lesson`, `LessonContent` | **คงเดิม** |
| **ใหม่** `CourseOutline` (Pydantic) | **เพิ่ม** — schema สำหรับ Planner output (course meta + lesson stubs) |
| **ใหม่** `LessonWithContent` (Pydantic) | **เพิ่ม** — schema สำหรับ Writer output (1 lesson + contents) |

### 3.2 `backend/agent/create_quiz/agent_autogen.py`

| Function/Class | การเปลี่ยนแปลง |
|---------------|----------------|
| `model_client` (module-level) | **ลบ** — bug fix: ต้องสร้างใหม่ทุก request |
| `create_team_for_quiz_request()` | **ลบ** — แทนด้วย pipeline ใหม่ |
| `_create_model_client()` | **แก้** — แยกตาม role |
| `CreateCourse.create_quiz()` | **เขียนใหม่** — QuizPlanner → parallel QuestionWriters → Assembler |
| `CreateCourse.regenerate_question()` | **คงเดิม** (single LLM call, ใช้ writer model) |
| `primary_agent_prompt` | **ลบ** — แทนด้วย `quiz_planner_prompt`, `question_writer_prompt` |
| `critic_agent_prompt` | **ลบ** — แทนด้วย `question_reviewer_prompt` |
| `FinalOutput` (Pydantic) | **คงเดิม** |
| **ใหม่** `QuizBlueprint` (Pydantic) | **เพิ่ม** — schema สำหรับ QuizPlanner output |
| **ใหม่** `QuestionBatch` (Pydantic) | **เพิ่ม** — schema สำหรับ QuestionWriter output |

### 3.3 `backend/gemini_config.py`

| Function | การเปลี่ยนแปลง |
|----------|----------------|
| `get_gemini_model()` | **แก้** — เป็น `get_model(role)` หรือเพิ่ม `get_planner_model()`, `get_writer_model()`, `get_grader_model()` |
| `set_gemini_model()` | **แก้** — เป็น `set_model(role, model)` |
| `DEFAULT_MODEL` | **แก้** — เป็น dict: `DEFAULT_MODELS = {planner: ..., writer: ..., grader: ...}` |
| Config JSON format | **แก้** — จาก `{"model": "..."}` เป็น `{"planner_model": "...", "writer_model": "...", "grader_model": "..."}` + backward compat |

### 3.4 `backend/document_chunking.py`

| Function | การเปลี่ยนแปลง |
|----------|----------------|
| `split_document()` | **คงเดิม** |
| `map_reduce_compress_document()` | **คงเดิม** |
| **ใหม่** `split_document_by_topics()` | **เพิ่ม** — ให้ Planner output กำหนดว่าแต่ละ lesson มาจาก section ไหน แล้ว route ส่วนของ document ไปให้ writer ที่ถูกตัว |

### 3.5 `backend/app.py` — Endpoints ที่ได้รับผลกระทบ

| Endpoint | Line | การเปลี่ยนแปลง |
|----------|------|----------------|
| `POST /api/create-course/preview` | ~764 | **แก้** — ใช้ `CreateCourse().create_course()` interface ใหม่ (return format เดิม) |
| `POST /api/lesson/regenerate` | ~840 | **ไม่แก้** — ใช้ `regenerate_lesson()` ที่ interface เดิม |
| `POST /api/create-quiz/preview` | ~1064 | **แก้** — ใช้ `CreateQuiz().create_quiz()` interface ใหม่ |
| `POST /api/question/regenerate` | ~912 | **ไม่แก้** — ใช้ `regenerate_question()` ที่ interface เดิม |
| `POST /api/lesson/chat` | ~1580 | **ไม่แก้** — ใช้ `question_answer()` เดิม |
| `POST /api/quiz/evaluate` | ~1625 | **ไม่แก้** — ใช้ `evaluate()` เดิม |
| `process_single_task()` | ~2966 | **แก้** — progress callback ละเอียดกว่าเดิม (per-lesson progress) |
| `PUT /api/admin/gemini/version` | ~1945 | **แก้** — รับ role param สำหรับ set model แยก role |
| `GET /api/admin/gemini/status` | ~1901 | **แก้** — return status ต่อ role |
| **ใหม่** `PUT /api/admin/gemini/role-model` | - | **เพิ่ม** — API สำหรับ set model per role |
| **ใหม่** `GET /api/admin/gemini/role-models` | - | **เพิ่ม** — API สำหรับ get models ทุก role |

### 3.6 Frontend

| ไฟล์ | Component/Function | การเปลี่ยนแปลง |
|------|-------------------|----------------|
| `AdminGeminiSettings.js` | `fetchData()` | **แก้** — เรียก API ใหม่ `GET /api/admin/gemini/role-models` |
| `AdminGeminiSettings.js` | `handleSaveVersion()` | **แก้** — เรียก API ใหม่ `PUT /api/admin/gemini/role-model` พร้อม role param |
| `AdminGeminiSettings.js` | JSX render | **แก้** — เพิ่ม 3 sections สำหรับ 3 roles (Planner, Writer, Grader) |
| `AdminAllCourse.js` | `LogCard` component | **แก้** — `getAgentIcon()` / `getAgentColor()` รองรับ agent ใหม่ (planner, writers, reviewers, assembler) |
| `AdminAllCourse.js` | `getStatusBadge()` | **แก้** — แสดง per-lesson progress breakdown |
| `AdminAllCourse.js` | Agent Logs tab (Course Preview) | **แก้** — Group logs ตาม pipeline stage (Planning / Writing / Assembly) |
| `AdminAllCourse.js` | Agent Logs tab (Quiz Preview) | **แก้** — Group logs ตาม pipeline stage (Planning / Question Writing / Assembly) |
| `AdminAllCourse.js` | Background Task Process tab | **แก้** — แสดง stage + lesson-level progress |
| `AdminAllCourse.js` | `fetchBackgroundTasks()` | **ไม่แก้** — API response format เดิม (เพิ่มแค่ fields ใหม่) |
| `AdminAllCourse.js` | `handleCreateQuiz()` | **ไม่แก้** — API interface เดิม |
| `AdminAllCourse.js` | `handleSubmitQuiz()` | **ไม่แก้** — output schema (`FinalOutput`) เดิม |

---

## 4. Architecture ใหม่ — Course Creation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Course Creation Pipeline                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Document] ──→ [Map-Reduce Compress (if large)] ──→ [Compressed Text]   │
│                                                                          │
│  Stage 1: PLANNING (Flash model — fast, cheap)                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Planner Agent ──→ Outline Reviewer ──→ (loop max 4 msgs)        │    │
│  │  Output: CourseOutline {course_meta, lesson_stubs[]}              │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Stage 2: WRITING (Pro model — creative, detailed) — PARALLEL            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Writer L1 │  │ Writer L2 │  │ Writer L3 │  │ Writer L4 │  ...       │
│  │  + Review │  │  + Review │  │  + Review │  │  + Review │           │
│  │(max 4 msg)│  │(max 4 msg)│  │(max 4 msg)│  │(max 4 msg)│           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │               │               │               │                 │
│        └───────────────┴───────────────┴───────────────┘                 │
│                                    │                                      │
│  Stage 3: ASSEMBLY (deterministic — no LLM needed)                       │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Assembler: merge lessons, fix IDs, validate consistency          │    │
│  │  Output: FinalOutput (same schema as before → backward compat)    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5. Architecture ใหม่ — Quiz Creation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Quiz Creation Pipeline                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Stage 1: PLANNING (Flash model)                                         │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  QuizPlanner: analyze doc → identify topics → allocate questions   │    │
│  │  Output: QuizBlueprint {quiz_meta, topic_allocations[]}            │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Stage 2: QUESTION WRITING (Pro model) — PARALLEL by topic               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                        │
│  │ QWriter    │  │ QWriter    │  │ QWriter    │                        │
│  │ Topic A    │  │ Topic B    │  │ Topic C    │  ...                   │
│  │ (MC+Subj+  │  │ (MC+Subj+  │  │ (MC+Subj+  │                        │
│  │  Fill)     │  │  Fill)     │  │  Fill)     │                        │
│  │  + Review  │  │  + Review  │  │  + Review  │                        │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                        │
│        │                │                │                                │
│        └────────────────┴────────────────┘                                │
│                         │                                                 │
│  Stage 3: ASSEMBLY (deterministic)                                        │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  QuizAssembler: merge questions, deduplicate, balance types,       │    │
│  │  assign IDs, validate total count                                  │    │
│  │  Output: FinalOutput (same schema → backward compat)               │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Detailed Requirements

### REQ-1: Multi-Model Configuration

**File**: `backend/gemini_config.py`

- Config format ใหม่:
  ```json
  {
    "planner_model": "gemini-2.5-flash-lite",
    "writer_model": "gemini-2.5-pro",
    "grader_model": "gemini-2.5-flash-lite",
    "api_key": "..."
  }
  ```
- Backward compatible: ถ้ามีแค่ `"model"` (format เดิม) ให้ใช้ค่านั้นทุก role
- Functions ใหม่:
  - `get_model_for_role(role: str) -> str` — role = "planner" | "writer" | "grader"
  - `set_model_for_role(role: str, model: str)`
  - `get_all_role_models() -> dict`
- Defaults: `planner=gemini-2.5-flash-lite`, `writer=gemini-2.5-flash-lite`, `grader=gemini-2.5-flash-lite`

---

### REQ-2: Max Iterations Guard (Quick Win)

**Files**: `agent/create_course/agent_autogen.py`, `agent/create_quiz/agent_autogen.py`

- ทุก RoundRobinGroupChat ต้องมี `MaxMessageTermination` เป็น fallback
- Course planning: max 6 messages (3 rounds)
- Lesson writing: max 4 messages (2 rounds) — ต่อ lesson
- Quiz planning: max 4 messages (2 rounds)
- Question writing: max 4 messages (2 rounds) — ต่อ topic batch
- เมื่อ hit max → ใช้ last Expert output (ดีกว่า hang)

---

### REQ-3: Course Planner Agent (Phase 1)

**File**: `agent/create_course/agent_autogen.py`

- สร้าง `CourseOutline` Pydantic model:
  ```python
  class LessonStub(BaseModel):
      lesson_title: str
      duration_hours: int
      lesson_order: int
      description: str
      what_you_will_learn: List[str]
      relevant_doc_sections: str  # คำอธิบายว่ามาจากส่วนไหนของ document

  class CourseOutline(BaseModel):
      course: Course
      lesson_stubs: List[LessonStub]
  ```
- Planner Agent prompt: focus on structure, topic mapping, time allocation — ไม่ต้องสร้าง content
- Outline Reviewer prompt: ตรวจ coverage, difficulty consistency, time balance
- ใช้ planner_model (Flash — เร็ว, ถูก)

---

### REQ-4: Parallel Lesson Writers (Phase 2)

**File**: `agent/create_course/agent_autogen.py`

- แต่ละ Writer Agent ได้รับ:
  - Course context (ชื่อ, description, difficulty, objectives)
  - Lesson stub (จาก Planner)
  - Relevant document section (route จาก Planner output)
- Writer + Reviewer pair per lesson (RoundRobinGroupChat, max 4 messages)
- ใช้ `asyncio.gather()` ทำ parallel — ทุก lessons พร้อมกัน
- ใช้ writer_model (Pro — creative, quality)
- Handle partial failure: ถ้า 1 lesson fail, retry ได้โดยไม่กระทบ lessons อื่น

---

### REQ-5: Assembler (Phase 2)

**File**: `agent/create_course/agent_autogen.py`

- Deterministic function (ไม่ใช้ LLM):
  - รวม lessons จาก parallel writers
  - จัด lesson_order, content_order
  - Assign IDs (course_id ให้ตรงกันทุก lesson)
  - Validate: ครบทุก lesson ที่ plan ไว้
- Output: `FinalOutput` schema เดิม → backward compatible

---

### REQ-6: Quiz Planner + Parallel Question Writers (Phase 3)

**File**: `agent/create_quiz/agent_autogen.py`

- QuizPlanner: วิเคราะห์ document → ระบุ topics → กระจาย question types per topic
- QuestionWriter per topic (parallel): สร้าง questions + choices + answers สำหรับ 1 topic
- QuizAssembler: รวม, deduplicate, balance counts, assign IDs
- Fix shared `model_client` bug (สร้างใหม่ทุก request)

---

### REQ-7: Document Section Routing

**File**: `backend/document_chunking.py`

- เพิ่ม function ที่ใช้ Planner output (`relevant_doc_sections`) เพื่อตัด document ส่งเฉพาะ relevant section ไปให้แต่ละ Writer
- ถ้า document สั้น (< max_doc_chars) → ส่งทั้งหมดให้ทุก Writer (ไม่ต้อง route)
- ถ้า document ยาว → หลัง Map-Reduce แล้ว route ตาม section headers

---

### REQ-8: Granular Progress Reporting

**File**: `backend/app.py` — `process_single_task()`

- Progress callback ละเอียดขึ้น:
  - 5%: "Starting..."
  - 10-20%: "Extracting document..." / "Compressing document..."
  - 25%: "Planning course outline..."
  - 30%: "Outline approved"
  - 35-75%: "Writing Lesson 1/6...", "Writing Lesson 2/6...", etc.
  - 80%: "Assembling final output..."
  - 90%: "Validating..."
  - 100%: "Done"

---

### REQ-9: Admin API — Multi-Model Management

**File**: `backend/app.py`

- `GET /api/admin/gemini/role-models` → return `{planner_model, writer_model, grader_model, status_per_role}`
- `PUT /api/admin/gemini/role-model` → body `{role: "planner"|"writer"|"grader", model: "gemini-..."}` + validate before save
- `GET /api/admin/gemini/status` → return status per role (ทดสอบแต่ละ model)
- Backward compat: `PUT /api/admin/gemini/version` ยังใช้ได้ (set ทุก role พร้อมกัน)

---

### REQ-10: Frontend — Multi-Model Settings UI

**File**: `frontend/src/pages/AdminGeminiSettings.js`

- แสดง 3 sections:
  1. **Planner / Reviewer** — model dropdown + status badge + description
  2. **Content Writer** — model dropdown + status badge + description
  3. **Grader / Evaluator** — model dropdown + status badge + description
- แต่ละ section มีปุ่ม "Edit" / "Test" แยก
- Error display per role (เช่น Writer model deprecated แต่ Planner ยัง active)
- API Key section คงเดิม (shared ทุก role)

---

### REQ-11: Frontend — Agent Log Display Update

**File**: `frontend/src/pages/AdminAllCourse.js` — Component `LogCard`

**ปัจจุบัน**: LogCard hardcode icon/color สำหรับ 2 agents เท่านั้น:
- `expert_agent` → brain icon, primary color
- `validator_agent` → check-circle icon, success color

**ต้องแก้**: รองรับ agents ใหม่ทั้งหมด:

| Agent Name | Icon | Color | Description |
|------------|------|-------|-------------|
| `planner_agent` | `fas fa-sitemap` | `is-link` | วาง outline |
| `outline_reviewer` | `fas fa-clipboard-check` | `is-info` | ตรวจ outline |
| `lesson_writer_L1`, `lesson_writer_L2`, ... | `fas fa-pen-fancy` | `is-primary` | เขียน lesson |
| `lesson_reviewer_L1`, `lesson_reviewer_L2`, ... | `fas fa-check-double` | `is-success` | ตรวจ lesson |
| `quiz_planner` | `fas fa-project-diagram` | `is-link` | วาง quiz blueprint |
| `question_writer_TopicA`, ... | `fas fa-pen-fancy` | `is-primary` | สร้าง questions |
| `question_reviewer_TopicA`, ... | `fas fa-check-double` | `is-success` | ตรวจ questions |
| `assembler` | `fas fa-puzzle-piece` | `is-warning` | รวม output |

**แก้ไข `getAgentIcon()` และ `getAgentColor()`:**
- ใช้ pattern matching แทน exact match (เช่น `includes('writer')`, `includes('reviewer')`, `startsWith('lesson_writer')`)
- เพิ่ม group label ให้ logs ที่มาจาก parallel agents เช่น "Parallel Lesson Writing (4 agents)"

---

### REQ-12: Frontend — Granular Progress Display

**File**: `frontend/src/pages/AdminAllCourse.js` — Component `getStatusBadge` + Background Task Process Tab

**ปัจจุบัน**: แสดง progress เป็น text generic เดียว (เช่น "Generating course content..." 30%)

**ต้องแก้**: แสดง progress ละเอียดตาม pipeline stages:

```
┌──────────────────────────────────────────────────────────────────┐
│ [████████████░░░░░░░░░░░░░░░░░] 45%                              │
│ Stage: Writing Lessons (3/6 completed)                           │
│                                                                   │
│ ✅ Planning outline... done                                       │
│ ✅ Outline approved                                               │
│ 🔄 Writing Lesson 3/6: "Control Structures"                      │
│ ⏳ Writing Lesson 4/6: "Functions and Modules"                   │
│ ⏳ Writing Lesson 5/6: "Error Handling"                          │
│ ⏳ Writing Lesson 6/6: "Final Project"                           │
└──────────────────────────────────────────────────────────────────┘
```

**Backend API response format** (from progress callback):
```json
{
  "progress": "Writing Lesson 3/6: Control Structures",
  "progress_percent": 45,
  "stage": "writing",
  "lessons_completed": 2,
  "lessons_total": 6,
  "current_lesson": "Control Structures"
}
```

**Frontend changes:**
1. Parse `task.progress` message ให้แสดง per-lesson breakdown
2. แสดง progress bar + current stage label
3. ถ้า stage = "writing" → แสดง lesson list พร้อม status (✅ done / 🔄 in-progress / ⏳ pending)
4. Polling interval ยังคง 5 วินาที (เหมาะกับ task ที่ใช้เวลา 25-35 วินาที)

---

### REQ-13: Frontend — Course Preview Log Grouping

**File**: `frontend/src/pages/AdminAllCourse.js` — Course/Quiz Preview "Agent Logs" tab

**ปัจจุบัน**: แสดง logs เรียงตาม index (Step 1, Step 2, Step 3...) ซึ่งเหมาะกับ 2 agents

**ต้องแก้**: Group logs ตาม pipeline stage เพื่อให้อ่านง่ายเมื่อมีหลาย agents:

```
┌─ Stage 1: Planning ────────────────────────────────────────┐
│  ▸ Planner Agent — Course outline generated                 │
│  ▸ Outline Reviewer — APPROVE                              │
└─────────────────────────────────────────────────────────────┘

┌─ Stage 2: Lesson Writing (Parallel) ───────────────────────┐
│  ▸ Lesson Writer L1 — "Python Basics" (2,341 chars)         │
│  ▸ Lesson Reviewer L1 — APPROVE                            │
│  ▸ Lesson Writer L2 — "Variables" (2,108 chars)             │
│  ▸ Lesson Reviewer L2 — APPROVE                            │
│  ... (expandable)                                            │
└─────────────────────────────────────────────────────────────┘

┌─ Stage 3: Assembly ────────────────────────────────────────┐
│  ▸ Assembler — Final output assembled (6 lessons, 14 contents) │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Backend ส่ง log entries พร้อม field `stage` (เช่น `{agent: "lesson_writer_L1", content: ..., stage: "writing"}`)
- Frontend group ตาม `stage` แล้วแสดง collapsible sections
- Default: collapsed (แสดงแค่ summary), expand ดูรายละเอียด

---

### REQ-14: Cleanup Dead Code

| ไฟล์ | Action |
|------|--------|
| `backend/agent/grader/agent_autogen.py` | ลบทั้งไฟล์ (ไม่ได้ใช้ ซ้ำกับ `CreateCourse.evaluate()`) |
| Module-level `model_client` ใน quiz agent | ลบ (ย้ายเป็น per-request) |
| `text_termination` module-level ใน quiz agent | ลบ (สร้างใน function แทน) |

---

## 7. Backward Compatibility Constraints

| Layer | Constraint |
|-------|-----------|
| **API Response format** | `FinalOutput` schema ต้องเหมือนเดิม — frontend/database ใช้ field เดิม |
| **Frontend calls** | Endpoints เดิมต้องทำงานได้ (**ไม่เปลี่ยน URL/method**) |
| **Config file** | ถ้า config มี format เดิม (`{"model": "..."}`) ต้อง fallback ได้ |
| **Background tasks** | Task ที่ pending ใน DB ต้อง process ได้หลัง upgrade |
| **Regenerate** | `regenerate_lesson()` และ `regenerate_question()` interface ไม่เปลี่ยน |

---

## 8. ลำดับการ Implement

| Phase | Tasks | Est. Effort |
|-------|-------|-------------|
| **Quick Win** | MaxMessageTermination + fix shared model_client | 1-2 ชั่วโมง |
| **Phase 1** | Multi-model config + Planner/Outline Reviewer + API + Frontend | 1 วัน |
| **Phase 2** | Parallel Lesson Writers + Assembler + progress reporting | 1 วัน |
| **Phase 3** | Quiz Planner + Parallel QuestionWriters + QuizAssembler + cleanup | 1 วัน |
| **Testing** | Integration test ทั้ง pipeline, backward compat, error cases | 0.5 วัน |

---

## 9. Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Parallel writers produce inconsistent style | Planner output provides style guidelines; Reviewer enforces |
| asyncio.gather partial failure | Retry failed lessons individually (max 2 retries) |
| Planner สร้าง outline ไม่ดี → Writer ได้ข้อมูลไม่พอ | Outline Reviewer ตรวจ coverage ก่อน approve |
| Model deprecated mid-request | Per-request model client creation + error handling with fallback |
| Longer total time due to planning step | Planning overhead (~5s) offset by parallel writing savings (~40s saved for 6 lessons) |

---

*Created: July 2026*
