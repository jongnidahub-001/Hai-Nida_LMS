# Implementation Tasks — Multi-Agent Hierarchical Architecture

รายการ Tasks สำหรับ implement ตาม [AGENT_ARCHITECTURE_REQUIREMENTS.md](./AGENT_ARCHITECTURE_REQUIREMENTS.md)

---

## Quick Win — Max Iterations Guard & Bug Fixes

### QW-1: เพิ่ม MaxMessageTermination ใน Course Agent
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - เพิ่ม `MaxMessageTermination` เป็น fallback termination condition ใน RoundRobinGroupChat
  - Course planning: max 6 messages (3 rounds)
  - Lesson writing: max 4 messages (2 rounds)
  - เมื่อ hit max → ใช้ last Expert output
- **สถานะ**: ✅ DONE

### QW-2: เพิ่ม MaxMessageTermination ใน Quiz Agent
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - Quiz planning: max 4 messages (2 rounds)
  - Question writing: max 4 messages (2 rounds)
- **สถานะ**: ✅ DONE

### QW-3: แก้ Bug — Shared `model_client` ใน Quiz Agent
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - ลบ module-level `model_client` variable
  - ลบ module-level `text_termination`
  - สร้าง model client ใหม่ทุก request ภายใน function
- **สถานะ**: ✅ DONE

---

## Phase 1 — Multi-Model Config + Planner Agent

### P1-1: Multi-Model Configuration
- **ไฟล์**: `backend/gemini_config.py`
- **รายละเอียด**:
  - เปลี่ยน config format เป็น `{planner_model, writer_model, grader_model, api_key}`
  - Backward compatible: ถ้ามีแค่ `"model"` ให้ใช้ค่านั้นทุก role
  - เพิ่ม functions:
    - `get_model_for_role(role: str) -> str`
    - `set_model_for_role(role: str, model: str)`
    - `get_all_role_models() -> dict`
  - Defaults: `planner=gemini-2.5-flash-lite`, `writer=gemini-2.5-flash-lite`, `grader=gemini-2.5-flash-lite`
- **สถานะ**: ✅ DONE

### P1-2: Admin API — Multi-Model Endpoints
- **ไฟล์**: `backend/app.py`
- **รายละเอียด**:
  - `GET /api/admin/gemini/role-models` → return models ทุก role + status
  - `PUT /api/admin/gemini/role-model` → body `{role, model}` + validate
  - แก้ `GET /api/admin/gemini/status` → return status per role
  - Backward compat: `PUT /api/admin/gemini/version` ยังใช้ได้ (set ทุก role)
- **สถานะ**: ✅ DONE

### P1-3: Frontend — Multi-Model Settings UI
- **ไฟล์**: `frontend/src/pages/AdminGeminiSettings.js`
- **รายละเอียด**:
  - แสดง 3 sections: Planner/Reviewer, Content Writer, Grader/Evaluator
  - แต่ละ section: model dropdown + status badge + description + Edit/Test button
  - Error display per role
  - API Key section คงเดิม (shared ทุก role)
- **สถานะ**: ✅ DONE

### P1-4: Course Planner Agent — Pydantic Models
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง `LessonStub` model: lesson_title, duration_hours, lesson_order, description, what_you_will_learn, relevant_doc_sections
  - สร้าง `CourseOutline` model: course (Course), lesson_stubs (List[LessonStub])
  - คงไว้: `FinalOutput`, `Course`, `Lesson`, `LessonContent` (backward compat)
- **สถานะ**: ✅ DONE

### P1-5: Course Planner Agent — Implementation
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง `planner_prompt` — focus on structure, topic mapping, time allocation
  - สร้าง `outline_reviewer_prompt` — ตรวจ coverage, difficulty, time balance
  - สร้าง Planner + Outline Reviewer RoundRobinGroupChat (max 6 messages)
  - ใช้ planner_model (Flash)
  - Output: `CourseOutline`
- **สถานะ**: ✅ DONE

### P1-6: แก้ `create_model_client()` ให้แยกตาม Role
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - แยกเป็น `create_planner_client()`, `create_writer_client()`
  - `_get_gemini_client()` ใช้ model ตาม role
- **สถานะ**: ✅ DONE

---

## Phase 2 — Parallel Lesson Writers + Assembler

### P2-1: Lesson Writer Agent — Prompts
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง `lesson_writer_prompt` — เขียน content ตาม stub + context + document section
  - สร้าง `lesson_reviewer_prompt` — ตรวจ quality, consistency, difficulty match
  - แต่ละ Writer ได้รับ: course context, lesson stub, relevant document section
- **สถานะ**: ✅ DONE

### P2-2: Parallel Lesson Writing — asyncio.gather()
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง Writer + Reviewer pair per lesson (RoundRobinGroupChat, max 4 messages)
  - ใช้ `asyncio.gather()` run parallel ทุก lessons พร้อมกัน
  - ใช้ writer_model (Pro)
  - Handle partial failure: ถ้า 1 lesson fail → retry ไม่กระทบ lessons อื่น (max 2 retries)
- **สถานะ**: ✅ DONE

### P2-3: Assembler — Deterministic Merge
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - Function (ไม่ใช้ LLM):
    - รวม lessons จาก parallel writers
    - จัด lesson_order, content_order
    - Assign IDs (course_id ตรงกันทุก lesson)
    - Validate: ครบทุก lesson ที่ plan ไว้
  - Output: `FinalOutput` schema เดิม → backward compatible
- **สถานะ**: ✅ DONE

### P2-4: Document Section Routing
- **ไฟล์**: `backend/document_chunking.py`
- **รายละเอียด**:
  - เพิ่ม `split_document_by_topics()` function
  - ใช้ Planner output (`relevant_doc_sections`) ตัด document ส่งเฉพาะ section ที่เกี่ยวข้อง
  - ถ้า document สั้น (< max_doc_chars) → ส่งทั้งหมดให้ทุก Writer
  - ถ้า document ยาว → route ตาม section headers หลัง Map-Reduce
- **สถานะ**: ✅ DONE

### P2-5: Rewrite `CreateCourse.create_course()` — Full Pipeline
- **ไฟล์**: `backend/agent/create_course/agent_autogen.py`
- **รายละเอียด**:
  - เขียนใหม่เป็น multi-step pipeline: plan → parallel write → assemble
  - ลบ `create_team_for_request()` เดิม
  - ลบ `primary_agent_prompt`, `critic_agent_prompt`
  - คง `regenerate_lesson()`, `question_answer()`, `evaluate()`, `suggest_course()` (interface เดิม)
- **สถานะ**: ✅ DONE

### P2-6: Granular Progress Reporting
- **ไฟล์**: `backend/app.py` — `process_single_task()`
- **รายละเอียด**:
  - Progress callback ละเอียด:
    - 5%: Starting
    - 10-20%: Extracting/Compressing document
    - 25%: Planning course outline
    - 30%: Outline approved
    - 35-75%: Writing Lesson X/N
    - 80%: Assembling final output
    - 90%: Validating
    - 100%: Done
  - Backend response format เพิ่ม: `stage`, `lessons_completed`, `lessons_total`, `current_lesson`
- **สถานะ**: ✅ DONE

### P2-7: Frontend — Agent Log Display Update
- **ไฟล์**: `frontend/src/pages/AdminAllCourse.js`
- **รายละเอียด**:
  - แก้ `getAgentIcon()` / `getAgentColor()` ใช้ pattern matching (includes/startsWith)
  - รองรับ agents: planner_agent, outline_reviewer, lesson_writer_LX, lesson_reviewer_LX, assembler
  - Group logs ตาม pipeline stage (Planning / Writing / Assembly)
  - Collapsible sections, default collapsed
- **สถานะ**: ✅ DONE

### P2-8: Frontend — Granular Progress Display
- **ไฟล์**: `frontend/src/pages/AdminAllCourse.js`
- **รายละเอียด**:
  - Parse `task.progress` แสดง per-lesson breakdown
  - Progress bar + current stage label
  - Stage = "writing" → แสดง lesson list พร้อม status (✅/🔄/⏳)
  - Polling interval คง 5 วินาที
- **สถานะ**: ✅ DONE

---

## Phase 3 — Quiz Pipeline + Cleanup

### P3-1: Quiz Planner Agent
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง `QuizBlueprint` Pydantic model: quiz_meta, topic_allocations[]
  - สร้าง `quiz_planner_prompt` — วิเคราะห์ document → identify topics → allocate question types
  - QuizPlanner + Reviewer pair (max 4 messages)
  - ใช้ planner_model
- **สถานะ**: ✅ DONE

### P3-2: Parallel Question Writers
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - สร้าง `QuestionBatch` Pydantic model
  - สร้าง `question_writer_prompt`, `question_reviewer_prompt`
  - QuestionWriter per topic (parallel via asyncio.gather)
  - ใช้ writer_model
  - Max 4 messages per topic batch
- **สถานะ**: ✅ DONE

### P3-3: Quiz Assembler
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - Deterministic function: merge questions, deduplicate, balance types, assign IDs, validate total count
  - Output: `FinalOutput` schema เดิม → backward compatible
- **สถานะ**: ✅ DONE

### P3-4: Rewrite `CreateCourse.create_quiz()` — Full Pipeline
- **ไฟล์**: `backend/agent/create_quiz/agent_autogen.py`
- **รายละเอียด**:
  - เขียนใหม่เป็น: QuizPlanner → parallel QuestionWriters → QuizAssembler
  - ลบ `create_team_for_quiz_request()` เดิม
  - คง `regenerate_question()` (interface เดิม)
- **สถานะ**: ✅ DONE

### P3-5: Frontend — Quiz Agent Log Grouping
- **ไฟล์**: `frontend/src/pages/AdminAllCourse.js`
- **รายละเอียด**:
  - Group logs ตาม pipeline stage (Planning / Question Writing / Assembly)
  - รองรับ agents: quiz_planner, question_writer_TopicX, question_reviewer_TopicX, assembler
- **สถานะ**: ✅ DONE

### P3-6: Cleanup Dead Code
- **รายละเอียด**:
  - ลบ `backend/agent/grader/agent_autogen.py` (ซ้ำกับ `CreateCourse.evaluate()`)
  - ลบ module-level `model_client` ใน quiz agent (ถ้ายังเหลือจาก QW-3)
  - ลบ `text_termination` module-level ใน quiz agent
- **สถานะ**: ✅ DONE

---

## Phase 4 — Testing & Validation

### T-1: Integration Test — Course Pipeline
- **รายละเอียด**:
  - ทดสอบ full pipeline: document → plan → parallel write → assemble
  - ตรวจ output format = `FinalOutput` schema เดิม
  - ทดสอบ partial failure + retry
  - ทดสอบ MaxMessageTermination fallback
- **สถานะ**: ✅ DONE

### T-2: Integration Test — Quiz Pipeline
- **รายละเอียด**:
  - ทดสอบ full pipeline: document → quiz plan → parallel question write → assemble
  - ตรวจ output format เดิม
  - ทดสอบ deduplication + type balancing
- **สถานะ**: ✅ DONE

### T-3: Backward Compatibility Test
- **รายละเอียด**:
  - Config เดิม (`{"model": "..."}`) ยัง fallback ได้
  - Endpoints เดิมทำงานได้ (ไม่เปลี่ยน URL/method)
  - `regenerate_lesson()`, `regenerate_question()` interface ไม่เปลี่ยน
  - Background tasks ที่ pending ใน DB ยัง process ได้
- **สถานะ**: ✅ DONE

### T-4: Performance Benchmark
- **รายละเอียด**:
  - วัด latency: target 25-35s สำหรับ 6 lessons (ลดจาก 60-90s)
  - วัด token usage: target ลด 80% เมื่อ reject (แก้แค่ lesson ที่ fail)
  - ทดสอบ parallel execution throughput
- **สถานะ**: ✅ DONE

---

## ลำดับ Dependencies

```
QW-1, QW-2, QW-3  (ทำได้เลย — ไม่มี dependency)
       │
       ▼
P1-1 → P1-2 → P1-3  (Config → API → Frontend)
P1-1 → P1-6 → P1-4 → P1-5  (Config → Client → Models → Planner)
       │
       ▼
P2-4 → P2-1 → P2-2 → P2-3 → P2-5  (Routing → Writer → Parallel → Assembler → Pipeline)
P2-5 → P2-6 → P2-8  (Pipeline → Progress Backend → Progress Frontend)
P2-5 → P2-7  (Pipeline → Log Display)
       │
       ▼
P3-1 → P3-2 → P3-3 → P3-4  (QuizPlanner → Writers → Assembler → Pipeline)
P3-4 → P3-5  (Pipeline → Log Display)
P3-4 → P3-6  (Pipeline → Cleanup)
       │
       ▼
T-1, T-2, T-3, T-4  (Testing — หลังทุก Phase เสร็จ)
```

---

## Estimated Timeline

| Phase | Tasks | ระยะเวลา |
|-------|-------|----------|
| Quick Win | QW-1, QW-2, QW-3 | 1-2 ชั่วโมง |
| Phase 1 | P1-1 ถึง P1-6 | 1 วัน |
| Phase 2 | P2-1 ถึง P2-8 | 1 วัน |
| Phase 3 | P3-1 ถึง P3-6 | 1 วัน |
| Testing | T-1 ถึง T-4 | 0.5 วัน |
| **รวม** | **23 tasks** | **~3.5-4 วัน** |

---

*สร้างจาก: [AGENT_ARCHITECTURE_REQUIREMENTS.md](./AGENT_ARCHITECTURE_REQUIREMENTS.md)*
*Created: July 2026*
