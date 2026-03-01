# Course & Quiz Difficulty Level Criteria & Prompt Guidelines

เอกสารนี้กำหนดเกณฑ์ที่ชัดเจนเพื่อให้ **Course** และ **Quiz** แต่ละ Level (Casual, Regular, Intense) มีความแตกต่างกันอย่างเห็นได้ชัด

---

## ปัญหาปัจจุบัน

- เกณฑ์ใน Prompt ปัจจุบันกว้างเกินไป (เช่น "basic concepts", "intermediate concepts")
- ไม่มีการวัดผลที่ชัดเจน
- ไม่มีตัวอย่างเปรียบเทียบให้ AI โฟกัส
- Critic Agent ไม่ได้ตรวจว่า Level แยกจากกันเพียงพอ

---

# ส่วนที่ 1: Course

## 1. เกณฑ์หลัก 5 ด้าน (Differentiation Dimensions)

### 1.1 ความลึกของเนื้อหา (Content Depth)

| Casual | Regular | Intense |
|--------|---------|---------|
| **What & Why** – เน้นคำจำกัดความ หลักการพื้นฐาน | **How & When** – เน้นการนำไปใช้และเงื่อนไข | **Why Not & Trade-offs** – เน้นข้อจำกัด, การเปรียบเทียบทางเลือก |
| 1-2 หัวข้อหลักต่อ Lesson | 2-3 หัวข้อ + ความเชื่อมโยง | 3-4 หัวข้อ + การวิเคราะห์เชิงลึก |
| บอก "คืออะไร" | บอก "ทำอย่างไร" พร้อมตัวอย่าง | บอก "ทำไมต้องเลือกอย่างนี้ และไม่ใช่อย่างอื่น" |

### 1.2 ความซับซ้อนของภาษา (Language Complexity)

| Casual | Regular | Intense |
|--------|---------|---------|
| ประโยคสั้น 10–15 คำ | ประโยคปานกลาง 15–25 คำ | ประโยคยาว ซับซ้อน 20–35 คำ |
| คำศัพท์ง่าย, หลีกเลี่ยงศัพท์เทคนิค | ศัพท์เทคนิคพอสมควร + อธิบาย | ศัพท์เทคนิคเต็มรูปแบบ, สมมติว่าผู้อ่านเคยเห็นแล้ว |
| ใช้ analogies บ่อย | analogies สลับกับคำอธิบายตรง | เน้นคำอธิบายเทคนิค, analogies น้อย |

### 1.3 Cognitive Level (Bloom's Taxonomy)

| Casual | Regular | Intense |
|--------|---------|---------|
| Remember, Understand | Apply, Analyze | Evaluate, Create |
| เน้นจำและเข้าใจ | เน้นนำไปใช้และวิเคราะห์ | เน้นประเมินและสร้างสิ่งใหม่ |
| คำถาม: "คืออะไร", "ทำไมสำคัญ" | คำถาม: "ใช้ยังไง", "ต่างกันตรงไหน" | คำถาม: "เปรียบเทียบได้ไหม", "จะออกแบบเองได้อย่างไร" |

### 1.4 โครงสร้างหลักสูตร (Course Structure)

| Casual | Regular | Intense |
|--------|---------|---------|
| 4–6 Lessons, 1–2 ชม./Lesson | 5–8 Lessons, 2–3 ชม./Lesson | 6–10 Lessons, 3–4 ชม./Lesson |
| Total: 6–12 ชม. | Total: 12–24 ชม. | Total: 18–40 ชม. |
| prerequisites: น้อยหรือไม่มี | prerequisites: 2–3 รายการ | prerequisites: 4+ รายการ |
| learning_objectives: 3–5 ข้อ | learning_objectives: 5–8 ข้อ | learning_objectives: 7–12 ข้อ |

### 1.5 กิจกรรมและ Reflection Questions

| Casual | Regular | Intense |
|--------|---------|---------|
| ทำตามขั้นตอนง่าย, แบบฝึกหัดตรงจากเนื้อหา | case study แบบมีทางเลือก 2–3 แบบ | กรณีศึกษา open-ended, ต้องออกแบบแนวทางเอง |
| reflection: "คุณเข้าใจ X อย่างไร?" | reflection: "คุณจะนำ X มาใช้ในกรณี Y ได้อย่างไร?" | reflection: "เปรียบเทียบ X กับ Z ในบริบท... อะไรคือข้อดี-ข้อเสีย?" |

---

## 2. ตัวอย่างเปรียบเทียบ (Same Topic, Different Levels)

### ตัวอย่าง: "Encryption" ในหัวข้อ Cybersecurity

**Casual:**
> การเข้ารหัส (Encryption) คือการเปลี่ยนข้อมูลให้เป็นรหัสที่คนอื่นอ่านยาก เปรียบเหมือนการใส่ข้อมูลในตู้เซฟ พอใส่รหัสแล้ว มีแค่คนที่รู้รหัสเท่านั้นที่เปิดดูได้

**Regular:**
> การเข้ารหัสใช้ algorithm เช่น AES เพื่อแปลง plaintext เป็น ciphertext ด้วย cryptographic key การเลือก symmetric vs asymmetric encryption ขึ้นอยู่กับ use case: symmetric เหมาะกับข้อมูลปริมาณมาก, asymmetric เหมาะกับการแลกเปลี่ยน key

**Intense:**
> การออกแบบระบบ encryption ต้องพิจารณา key management, algorithm choice (AES-256-GCM vs ChaCha20-Poly1305), และการจัดการ trade-offs ระหว่าง performance กับ security level. การ implement ที่ผิดพลาด เช่น reusing nonce หรือ weak key derivation อาจทำให้ระบบเสี่ยงแม้ใช้ strong algorithm

---

## 3. Suggested Prompts สำหรับ Agent

### 3.1 Primary Agent (Course Creator) – Enhanced Difficulty Section

```
**Difficulty Level Guidelines (STRICT – Must Be Visibly Different):**

**CASUAL (Beginner-friendly, Foundation):**
- Content Depth: Explain WHAT and WHY only. 1-2 main topics per lesson.
- Language: Short sentences (10-15 words). Simple vocabulary. Use analogies frequently.
- Cognitive: Remember + Understand (Bloom's levels 1-2).
- Structure: 4-6 lessons, 1-2 hours each. Total 6-12 hours. Minimal/no prerequisites.
- Activities: Simple step-by-step exercises. Reflection: "What did you understand about X?"
- AVOID: Technical jargon, trade-off analysis, multi-step reasoning.

**REGULAR (Intermediate, Application-focused):**
- Content Depth: Explain HOW and WHEN. 2-3 topics + connections. Include case studies.
- Language: Medium sentences (15-25 words). Moderate technical terms with brief explanations.
- Cognitive: Apply + Analyze (Bloom's levels 3-4).
- Structure: 5-8 lessons, 2-3 hours each. Total 12-24 hours. 2-3 prerequisites.
- Activities: Case studies with 2-3 options. Reflection: "How would you apply X in scenario Y?"
- AVOID: Over-simplification (Casual style). Deep theoretical proofs (Intense style).

**INTENSE (Advanced, Critical Thinking):**
- Content Depth: Explain WHY NOT, trade-offs, alternatives. 3-4 topics + deep analysis.
- Language: Longer, complex sentences (20-35 words). Full technical vocabulary assumed.
- Cognitive: Evaluate + Create (Bloom's levels 5-6).
- Structure: 6-10 lessons, 3-4 hours each. Total 18-40 hours. 4+ prerequisites.
- Activities: Open-ended case studies, design-your-own scenarios. Reflection: "Compare X and Z. What are trade-offs? How would you design...?"
- AVOID: Basic definitions (assume prior knowledge). Hand-holding step-by-step.

**CRITICAL:** For the SAME document, Casual content must read 50% shorter and simpler than Regular. Regular must read 40% less technical than Intense.
```

### 3.2 Critic/Validator Agent – เพิ่มเกณฑ์ตรวจความต่างของ Level

```
**Difficulty Level Validation (Check before APPROVE):**

For CASUAL course:
- [ ] No unexplained technical jargon
- [ ] Lessons are 1-2 hours each, total course 6-12 hours
- [ ] Content answers "what is it?" not "how to compare alternatives"
- [ ] Prerequisites are minimal (0-2 items)
- [ ] Reflection questions ask for understanding, not application design

For REGULAR course:
- [ ] Mix of theory and application, with case studies
- [ ] Lessons are 2-3 hours each, total 12-24 hours
- [ ] Content includes "how to apply" with examples
- [ ] Prerequisites are moderate (2-3 items)
- [ ] Reflection questions ask for application in scenarios

For INTENSE course:
- [ ] Deep analysis, trade-offs, multiple viewpoints
- [ ] Lessons are 3-4 hours each, total 18-40 hours
- [ ] Content assumes prior knowledge, no basic definitions
- [ ] Prerequisites are substantial (4+ items)
- [ ] Reflection questions ask for evaluation, comparison, or design

If the course reads like it could be another level, REJECT and specify: "Content does not match {level}. Specifically: [list what makes it too easy or too hard]."
```

---

## 4. Quick Reference Table

| Dimension | Casual | Regular | Intense |
|-----------|--------|---------|---------|
| **Main focus** | What & Why | How & When | Why Not & Trade-offs |
| **Sentence length** | 10-15 words | 15-25 words | 20-35 words |
| **Bloom's level** | 1-2 | 3-4 | 5-6 |
| **Lesson duration** | 1-2 hr | 2-3 hr | 3-4 hr |
| **Course total** | 6-12 hr | 12-24 hr | 18-40 hr |
| **Prerequisites** | 0-2 | 2-3 | 4+ |
| **Learning objectives** | 3-5 | 5-8 | 7-12 |
| **Reflection type** | Understanding | Application | Evaluation/Design |

---

# ส่วนที่ 2: Quiz

## 7. เกณฑ์ความยากของ Quiz (3 ระดับต้องต่างกันชัดเจน)

### 7.1 ประเภทคำถามและ Cognitive Level

| | Casual | Regular | Intense |
|---|--------|---------|---------|
| **Bloom's ระดับที่ทดสอบ** | Remember, Understand | Apply, Analyze | Evaluate, Create |
| **จุดมุ่งหมาย** | จำได้ + เข้าใจนิยาม | นำไปใช้ + วิเคราะห์สถานการณ์ | ประเมินทางเลือก + สร้างแนวทาง |
| **ความยาวคำถาม** | สั้น 10-20 คำ | ปานกลาง 25-40 คำ | ยาว 40-70 คำ (มี context/scenario) |

### 7.2 Multiple Choice – ความซับซ้อนของตัวเลือก (Distractors)

| Casual | Regular | Intense |
|--------|---------|---------|
| ตัวเลือกผิดชัดเจน (obviously wrong) | ตัวเลือกผิดมีความ plausibility ปานกลาง | ตัวเลือกผิดมีความน่าจะเป็นสูง ต้องคิดวิเคราะห์จึงแยกได้ |
| คำตอบถูกตรงจาก document (verbatim) | คำตอบถูกต้อง paraphrase หรือใช้ในบริบท | คำตอบถูกต้อง synthesis หลายแนวคิด |
| 1-step: อ่านแล้วตอบได้ทันที | 2-step: วิเคราะห์ scenario ก่อนตอบ | 3-step+: เปรียบเทียบ, หักล้าง, จึงตอบได้ |

### 7.3 Subjective Questions

| Casual | Regular | Intense |
|--------|---------|---------|
| "X คืออะไร?" / "ให้นิยาม X" | "ในกรณี Y คุณจะใช้ X อย่างไร?" | "เปรียบเทียบ X กับ Z ในบริบท... ข้อดี-ข้อเสีย?" |
| คำตอบสั้น 1-2 ประโยค | คำตอบปานกลาง 2-4 ประโยค มีตัวอย่าง | คำตอบยาว 4+ ประโยค ต้องอธิบายเหตุผลหลายมิติ |
| คะแนน 1-2 points | คะแนน 2-4 points | คะแนน 4-6 points |

### 7.4 Fill in the Blank

| Casual | Regular | Intense |
|--------|---------|---------|
| คำศัพท์สำคัญจาก document (keyword) | ศัพท์ที่ต้องเข้าใจบริบทประโยค | ศัพท์/ phrase ที่ต้องวิเคราะห์จาก context |
| มีคำใบ้ในประโยค (cloze) | ต้องเข้าใจความสัมพันธ์ในประโยค | ต้องเชื่อมหลาย concept เพื่อเติมให้ถูก |

### 7.5 Point Values และสัดส่วนคำถาม

| | Casual | Regular | Intense |
|---|--------|---------|---------|
| **Points ต่อข้อ** | 1-3 | 2-5 | 5-10 |
| **สัดส่วน Recall:Application:Analysis** | 70:30:0 | 40:40:20 | 20:30:50 |
| **Multiple Choice ง่าย vs ยาก** | ส่วนใหญ่เลือกถูกได้เร็ว | ผสมกัน | ส่วนใหญ่ต้องคิดก่อนตอบ |

---

## 8. ตัวอย่าง Quiz (Same Topic, Different Levels)

### ตัวอย่าง: หัวข้อ Encryption

**คำถาม: การเข้ารหัสข้อมูล**

**CASUAL (Multiple Choice):**
> การเข้ารหัส (Encryption) คืออะไร?  
> A) การลบข้อมูล B) การเปลี่ยนข้อมูลให้อ่านยาก C) การสำรองข้อมูล D) การส่งข้อมูล

**REGULAR (Multiple Choice):**
> บริษัทต้องการส่งข้อมูลทางการเงินจำนวนมากให้สาขาต่างๆ อย่างปลอดภัย ควรเลือกวิธีเข้ารหัสแบบใด?  
> A) Symmetric – เร็ว, เหมาะกับข้อมูลปริมาณมาก  
> B) Asymmetric – ใช้ key เดียวกันทั้งส่งและรับ  
> C) Hashing – แปลงแล้วไม่สามารถ decode กลับได้  
> D) Plaintext – ส่งตรงๆ ผ่าน HTTPS แล้วเพียงพอ  

**INTENSE (Multiple Choice):**
> ระบบ A ใช้ AES-256-GCM กับ static key ที่ derive จาก password ผู้ใช้ระบบ B ใช้ ChaCha20-Poly1305 กับ per-session key จาก KMS ในบริบทที่ต้องรับมือกับทั้ง side-channel attacks และความต้องการ latency ต่ำ ข้อใดถูกที่สุด?  
> A) A ดีกว่าเพราะ AES แข็งแกร่งกว่า ChaCha20  
> B) B ดีกว่าเพราะ key management ลดความเสี่ยง key reuse  
> C) ทั้งคู่เทียบเท่าถ้าใช้ nonce แบบ random อย่างถูกต้อง  
> D) ขึ้นกับว่าใช้ hardware acceleration หรือไม่  

**CASUAL (Subjective):**
> การเข้ารหัสช่วยเพิ่มความปลอดภัยให้ข้อมูลอย่างไร? (1-2 ประโยค)

**REGULAR (Subjective):**
> ถ้าคุณออกแบบระบบแชทกลุ่มที่ต้องป้องกันไม่ให้ผู้ใช้คนอื่นอ่านข้อความ คุณจะใช้ encryption แบบ symmetric หรือ asymmetric อย่างไร และเพราะเหตุใด? (2-4 ประโยค พร้อมเหตุผล)

**INTENSE (Subjective):**
> เปรียบเทียบ trade-offs ระหว่าง end-to-end encryption กับ encryption-in-transit ในแอป enterprise ที่ต้อง audit ความสัมพันธ์ของข้อมูล กรณีใดควรเลือกแบบใด และมีความเสี่ยงอะไรที่ต้องพิจารณา? (4+ ประโยค วิเคราะห์หลายมิติ)

---

## 9. Suggested Prompts สำหรับ Quiz Agent

### 9.1 Primary Agent (Quiz Creator) – Enhanced Difficulty Section

```
**Difficulty Level Guidelines (STRICT – Must Be Visibly Harder Each Level):**

**CASUAL (Recall & Basic Understanding):**
- Bloom's: Remember + Understand only.
- Multiple Choice: Question 10-20 words. Correct answer is direct from document. Wrong answers are obviously wrong (definitions of unrelated terms).
- Subjective: "What is X?" or "Define X." Answer in 1-2 sentences. 1-2 points.
- Fill in the Blank: Single keyword from document. Strong context clues in sentence.
- Points: 1-3 per question. 70% of questions = recall.
- AVOID: Scenario-based questions, comparing options, multi-step reasoning.

**REGULAR (Application & Analysis):**
- Bloom's: Apply + Analyze.
- Multiple Choice: Question 25-40 words with a scenario. Correct answer requires understanding "how/when to use." Distractors are plausible but wrong for this scenario.
- Subjective: "In scenario Y, how would you apply X? Explain." Answer 2-4 sentences with reasoning. 2-4 points.
- Fill in the Blank: Term that requires understanding sentence context, not just keyword match.
- Points: 2-5 per question. Balance recall and application.
- AVOID: Trivial recall (Casual). Deep trade-off analysis (Intense).

**INTENSE (Evaluation & Synthesis):**
- Bloom's: Evaluate + Create.
- Multiple Choice: Question 40-70 words, complex scenario. Correct answer requires comparing options, eliminating wrong ones. All distractors are plausible; must reason to choose.
- Subjective: "Compare X and Z. What are trade-offs? When would you choose which? justify." Answer 4+ sentences, multiple factors. 4-6 points.
- Fill in the Blank: Phrase or term requiring synthesis of multiple concepts from context.
- Points: 5-10 per question. 50%+ questions = analysis/synthesis.
- AVOID: Definition-only questions. Simple scenario with obvious answer.

**CRITICAL:** Casual = answer in seconds. Regular = think 30+ seconds. Intense = think 1+ minute. If a Casual learner can answer an Intense question easily, it's not Intense.
```

### 9.2 Quiz Critic/Validator Agent – เพิ่มเกณฑ์ตรวจความต่างของ Level

```
**Difficulty Level Validation (Check before APPROVE):**

For CASUAL quiz:
- [ ] MC questions: short (10-20 words), direct from document
- [ ] MC distractors: obviously wrong, not plausible
- [ ] Subjective: "what is" or "define" only, short answer
- [ ] Fill in the blank: single keyword with strong clues
- [ ] Points: 1-3 per question
- [ ] No scenario-based or comparison questions

For REGULAR quiz:
- [ ] MC questions: 25-40 words, scenario included
- [ ] MC distractors: plausible but wrong for the scenario
- [ ] Subjective: "how would you apply" with scenario, 2-4 sentences
- [ ] Points: 2-5 per question
- [ ] Mix of recall and application questions

For INTENSE quiz:
- [ ] MC questions: 40-70 words, complex multi-factor scenario
- [ ] MC distractors: all plausible, requires elimination/reasoning
- [ ] Subjective: "compare", "evaluate", "trade-offs", 4+ sentences
- [ ] Points: 5-10 per question
- [ ] Majority of questions require analysis/synthesis

If any question could fit a lower difficulty (e.g., Intense question is answerable by recall), REJECT: "Question X does not match {level}. Reason: [specific feedback]."
```

---

## 10. Quiz Quick Reference Table

| Dimension | Casual | Regular | Intense |
|-----------|--------|---------|---------|
| **Bloom's focus** | Remember, Understand | Apply, Analyze | Evaluate, Create |
| **MC question length** | 10-20 words | 25-40 words | 40-70 words |
| **MC distractor style** | Obviously wrong | Plausible | All plausible, need reasoning |
| **Time to answer** | Seconds | ~30 sec | 1+ min |
| **Subjective type** | Define/What is | How to apply | Compare/Evaluate |
| **Subjective length** | 1-2 sentences | 2-4 sentences | 4+ sentences |
| **Points per question** | 1-3 | 2-5 | 5-10 |
| **Recall:Apply:Analyze** | 70:30:0 | 40:40:20 | 20:30:50 |

---

## 5. การนำไปใช้

### Course

1. **อัปเดต `backend/agent/create_course/agent_autogen.py`**
   - แทนที่ section "**Difficulty Level Guidelines:**" ใน `primary_agent_prompt` ด้วยเนื้อหาจาก 3.1

2. **อัปเดต Course Critic Agent**
   - เพิ่ม "**Difficulty Level Validation**" ใน `critic_agent_prompt` จาก 3.2

### Quiz

3. **อัปเดต `backend/agent/create_quiz/agent_autogen.py`**
   - แทนที่ section "**Difficulty Level Guidelines:**" ใน `primary_agent_prompt` ด้วยเนื้อหาจาก 9.1

4. **อัปเดต Quiz Critic Agent**
   - เพิ่ม "**Difficulty Level Validation**" ใน `critic_agent_prompt` จาก 9.2

### ทดสอบ

5. **Course:** สร้างหลักสูตรจาก document เดียวกันทั้ง 3 levels → เปรียบเทียบความยาว, จำนวน lessons, ความซับซ้อนของภาษา

6. **Quiz:** สร้าง Quiz จาก document เดียวกันทั้ง 3 levels → เปรียบเทียบความยาวคำถาม, ความซับซ้อนของตัวเลือก, เวลาที่ใช้ตอบ (Casual = วินาที, Regular = ~30 วินาที, Intense = 1+ นาที)

---

## 6. หมายเหตุเพิ่มเติม

- Course และ Quiz ควรใช้ difficulty level เดียวกันเมื่อ generate จาก document เดียว (Casual course → Casual quiz)
- หากต้องการ Level เพิ่ม (เช่น 4 ระดับ) สามารถแยกระหว่าง Regular เป็น "Regular-" และ "Regular+" ได้
- ควรเก็บตัวอย่าง output ของแต่ละ level ไว้เป็น reference สำหรับ fine-tune prompt เพิ่มเติม
