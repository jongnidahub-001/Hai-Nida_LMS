import { APIRequestContext, Page, expect } from '@playwright/test';
import { API_URL, ADMIN_EMAIL, ADMIN_PASSWORD, DEFAULT_USER_PASSWORD } from './env';

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export async function loginToken(request: APIRequestContext, email: string, password: string) {
  const res = await request.post(`${API_URL}/api/login`, { data: { email, password } });
  expect(res.status(), `login ${email}`).toBe(200);
  return (await res.json()).token as string;
}

export function adminToken(request: APIRequestContext) {
  return loginToken(request, ADMIN_EMAIL, ADMIN_PASSWORD);
}

/** ใส่ token ลง localStorage ให้หน้าเว็บถือว่า login แล้ว */
export async function signInPage(page: Page, token: string) {
  await page.goto('/login');
  await page.evaluate((t) => localStorage.setItem('authToken', t), token);
}

export async function findUser(request: APIRequestContext, email: string) {
  const res = await request.get(`${API_URL}/api/admin/users`, { headers: auth(await adminToken(request)) });
  const { users } = await res.json();
  return users.find((u: { email: string }) => u.email === email) as { user_id: string; username: string } | undefined;
}

/** ลบผู้ใช้ตามอีเมลผ่าน admin API ถ้าไม่พบก็ไม่ทำอะไร */
export async function deleteUserByEmail(request: APIRequestContext, email: string) {
  const user = await findUser(request, email);
  if (user) {
    await request.delete(`${API_URL}/api/admin/user/${user.user_id}`, { headers: auth(await adminToken(request)) });
  }
}

export type Learner = { email: string; username: string; password: string; token: string };

/** สร้างผู้ใช้ที่ตั้งค่าครั้งแรกเสร็จแล้ว พร้อม login */
export async function createLearner(request: APIRequestContext, tag: string): Promise<Learner> {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const email = `e2e-${tag}-${stamp}@playwright.test`;
  const username = `e2e${tag}${stamp}`;
  const password = 'e2e-pass-123';

  const add = await request.post(`${API_URL}/api/admin/add-user`, {
    headers: auth(await adminToken(request)),
    data: { email },
  });
  expect(add.ok(), 'add user').toBeTruthy();

  const firstToken = await loginToken(request, email, DEFAULT_USER_PASSWORD);
  const setup = await request.post(`${API_URL}/api/first-time-setup`, {
    headers: auth(firstToken),
    data: { username, full_name: `E2E ${tag}`, new_password: password },
  });
  expect(setup.ok(), 'first-time setup').toBeTruthy();

  return { email, username, password, token: await loginToken(request, email, password) };
}

export type SeededCourse = {
  courseId: string;
  quizId: string;
  name: string;
  lessons: string[];
};

/**
 * สร้างคอร์สพร้อมบทเรียน 2 บทและ quiz 3 ข้อ (ปรนัย เติมคำ อัตนัย) ผ่าน API เดียวกับที่ปุ่ม Submit Quiz ใช้
 * ไม่เรียก Gemini คำตอบที่ถูกของแต่ละข้ออยู่ใน SEED_ANSWERS
 */
export async function seedCourse(request: APIRequestContext, tag: string, difficulty = 'Casual'): Promise<SeededCourse> {
  const name = `E2E ${tag} ${Date.now()}`;
  const lessons = ['Introduction to Capitals', 'Rivers of Europe'];
  const quizData = {
    course: {
      course_name: name,
      description: `Seeded course for Playwright tests (${tag})`,
      total_hour: 2,
      difficulty_level: difficulty,
      status: 'Active',
      learning_objectives: ['Name European capitals', 'Name European rivers'],
      prerequisites: ['None'],
    },
    lessons: lessons.map((title, i) => ({
      lesson_id: `l${i + 1}`,
      lesson_title: title,
      duration_hours: 1,
      lesson_order: i + 1,
      description: `${title} description`,
      what_you_will_learn: [`Key facts about ${title.toLowerCase()}`],
    })),
    lesson_contents: [
      { lesson_id: 'l1', content_order: 1, content_type: 'text', content: '## Capitals\n\nThe capital of France is **Paris**. The capital of Japan is Tokyo.' },
      { lesson_id: 'l2', content_order: 1, content_type: 'text', content: '## Rivers\n\nThe Danube flows through Vienna and Budapest.' },
    ],
    quiz: {
      quiz_title: `${name} Quiz`,
      description: 'Seeded quiz',
      status: 'Active',
      difficulty_level: difficulty,
    },
    questions: [
      { question_id: 'q1', question_text: 'What is the capital of Japan?', question_type: 'Multiple Choice', points: 1 },
      { question_id: 'q2', question_text: 'The capital of France is ____.', question_type: 'Fill in the Blank', points: 1 },
      { question_id: 'q3', question_text: 'Explain why capital cities are important.', question_type: 'Subjective', points: 1 },
    ],
    choices: [
      { question_id: 'q1', choice_text: 'Tokyo', is_correct: true },
      { question_id: 'q1', choice_text: 'Osaka', is_correct: false },
      { question_id: 'q1', choice_text: 'Kyoto', is_correct: false },
    ],
    answers: [
      { question_id: 'q2', answer_text: 'Paris' },
      { question_id: 'q3', answer_text: 'Capital cities host the government and are centres of politics, economy and culture.' },
    ],
  };

  const res = await request.post(`${API_URL}/api/create-quiz/submit`, {
    headers: auth(await adminToken(request)),
    data: { quiz_data: quizData },
    timeout: 120_000,
  });
  expect(res.ok(), `seed course: ${await res.text()}`).toBeTruthy();
  const { results } = await res.json();
  return { courseId: results.course_id, quizId: results.quiz_id, name, lessons };
}

export const SEED_ANSWERS = {
  choice: 'Tokyo',
  fill: 'Paris',
  subjective: 'Capital cities are where the national government sits, and they are usually the political, economic and cultural centre of the country.',
};

export const QUESTION_PATTERN = /capital of Japan|capital of France|capital cities are important/;

/** ตอบคำถามที่แสดงอยู่ตามประเภทของข้อ ใช้กับ quiz ที่สร้างจาก seedCourse */
export async function answerCurrentQuestion(page: Page) {
  const text = (await page.locator('h3').textContent()) ?? '';
  if (text.includes('Japan')) await page.getByLabel(SEED_ANSWERS.choice).check();
  else if (text.includes('France')) await page.locator('input[placeholder="Type your answer here..."]').fill(SEED_ANSWERS.fill);
  else await page.locator('textarea[placeholder="Type your answer here..."]').fill(SEED_ANSWERS.subjective);
}

export async function findCoursesByName(request: APIRequestContext, prefix: string) {
  const res = await request.get(`${API_URL}/api/admin/courses`, { headers: auth(await adminToken(request)) });
  const { courses } = await res.json();
  return (courses as { course_id: string; course_name: string }[]).filter((c) => c.course_name.startsWith(prefix));
}

export async function deleteCourse(request: APIRequestContext, courseId: string) {
  await request.delete(`${API_URL}/api/admin/courses/${courseId}`, { headers: auth(await adminToken(request)) });
}

export async function enroll(request: APIRequestContext, token: string, courseId: string) {
  const res = await request.post(`${API_URL}/api/enroll`, { headers: auth(token), data: { course_id: courseId } });
  expect(res.ok(), 'enroll').toBeTruthy();
}

export async function listTasks(request: APIRequestContext) {
  const res = await request.get(`${API_URL}/api/background-tasks`, { headers: auth(await adminToken(request)) });
  const body = await res.json();
  return (body.tasks ?? body) as { task_id: string; document_name: string; status: string }[];
}

export async function deleteTask(request: APIRequestContext, taskId: string) {
  await request.delete(`${API_URL}/api/background-tasks/${taskId}`, { headers: auth(await adminToken(request)) });
}
