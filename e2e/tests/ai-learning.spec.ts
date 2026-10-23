import { test, expect } from '@playwright/test';
import {
  QUESTION_PATTERN, adminToken, answerCurrentQuestion, createLearner, deleteCourse, deleteUserByEmail, enroll, findUser, Learner, SeededCourse,
  seedCourse, signInPage,
} from './support/api';

// แชทกับ AI ในบทเรียน และทำ quiz ที่ Gemini ตรวจคำตอบและวิเคราะห์ผล
test.describe.configure({ mode: 'serial' });

let learner: Learner;
let course: SeededCourse;

test.beforeAll(async ({ request }) => {
  course = await seedCourse(request, 'AI Learning');
  learner = await createLearner(request, 'ailearn');
  await enroll(request, learner.token, course.courseId);
});

test.afterAll(async ({ request }) => {
  await deleteUserByEmail(request, learner.email);
  await deleteCourse(request, course.courseId);
});

test.describe('ผู้เรียนใช้ AI', { tag: '@ai' }, () => {
  test('ถาม AI ในหน้าบทเรียนแล้วได้คำตอบ และล้างประวัติแชทได้', async ({ page }) => {
    await signInPage(page, learner.token);
    await page.goto(`/course/${course.courseId}`);
    await page.getByRole('button', { name: 'Continue Course' }).click();
    await expect(page.locator('.lesson-content-card')).toContainText('Paris');

    await page.getByRole('button', { name: 'Chat with AI' }).click();
    const chat = page.locator('.chat-modal');
    await expect(chat.getByText("Hello! I'm your AI assistant.")).toBeVisible();

    await chat.getByPlaceholder('Ask me anything about this lesson...').fill('What is the capital of France according to this lesson?');
    await chat.locator('.chat-input button').click();
    await expect(chat.locator('.chat-message.user-message')).toHaveCount(1);
    const reply = chat.locator('.chat-message.ai-message .message-content').first();
    await expect(reply).toContainText(/\S{3,}/, { timeout: 120_000 });
    await expect(chat.locator('.typing-indicator')).toHaveCount(0, { timeout: 120_000 });

    await chat.getByTitle('Clear chat history').click();
    await expect(chat.getByText("Hello! I'm your AI assistant.")).toBeVisible();
    await chat.getByTitle('Close chat').click();
    await expect(chat).toBeHidden();
  });

  test('ทำ quiz ครบทุกประเภทคำถาม ส่งแล้วเห็นคะแนนและบทวิเคราะห์', async ({ page }) => {
    test.setTimeout(6 * 60_000);
    await signInPage(page, learner.token);
    await page.goto(`/course/${course.courseId}/quiz`);

    await expect(page.locator('h3')).toHaveText(QUESTION_PATTERN);
    for (let i = 0; i < 3; i++) {
      await answerCurrentQuestion(page);
      if (i < 2) await page.getByRole('button', { name: 'Next Question' }).click();
    }
    await page.getByRole('button', { name: 'Submit Quiz' }).click();

    const result = page.locator('.quiz-complete-card');
    await expect(result.getByRole('heading', { name: 'Quiz Completed!' })).toBeVisible({ timeout: 5 * 60_000 });
    await expect(result.locator('.score-percentage')).toHaveText(/\d+%/);
    await expect(result.locator('.quiz-analysis')).toBeVisible();
  });

  test('หลังทำ quiz ปุ่มในหน้าคอร์สเปลี่ยนเป็น Quiz Result และ Dashboard แสดงคะแนน', async ({ page }) => {
    await signInPage(page, learner.token);
    await page.goto(`/course/${course.courseId}`);
    await page.getByRole('button', { name: 'Quiz Result' }).click();
    await expect(page).toHaveURL(/\/quiz-result$/);
    await expect(page.getByRole('heading', { name: 'Quiz Result' })).toBeVisible({ timeout: 60_000 });

    await page.goto('/home');
    const row = page.locator('.home-course-row', { hasText: course.name }).filter({ hasText: 'Score' });
    await expect(row.getByText('Completed')).toBeVisible();
    await expect(row).toContainText(/Score: \d+ \/ 3/);
    await row.click();
    await expect(page).toHaveURL(/\/quiz-result$/);
  });

  test('admin เห็นผล quiz ของผู้เรียนและเปิดดูคำตอบได้', async ({ page, request }) => {
    await signInPage(page, await adminToken(request));
    const user = await findUser(request, learner.email);
    await page.goto(`/admin/user/${user!.user_id}`);
    await page.locator('.tabs').getByText('Quiz Results (1)').click();
    const row = page.locator('tbody tr', { hasText: course.name });
    await expect(row).toContainText(/\d+ \/ 3/);
    await row.getByRole('button', { name: 'View Answers' }).click();
    await expect(page.getByRole('heading', { name: 'Quiz Answers' })).toBeVisible();
    await expect(page.getByText('What is the capital of Japan?')).toBeVisible();

    await page.goto(`/admin/course/${course.courseId}`);
    await page.locator('.tabs').getByText('Enrolled Users (1)').click();
    await expect(page.locator('tbody tr', { hasText: learner.email }).getByText('Completed')).toBeVisible();
  });

  test('หน้า All Quiz Scores แสดงคะแนนของผู้เรียน', async ({ page, request }) => {
    await signInPage(page, await adminToken(request));
    await page.goto('/admin/quizzes');
    await page.getByPlaceholder('Search by username or course...').fill(learner.username);
    const row = page.locator('tbody tr', { hasText: course.name });
    await expect(row).toBeVisible();
    await expect(row).toContainText(/\d+ \/ 3/);
    await expect(row.getByText('Completed')).toBeVisible();
    await expect(row).not.toContainText('Invalid Date');
    await expect(page.locator('.pagination-link')).toHaveCount(1);
    await row.getByRole('button', { name: 'View Course' }).click();
    await expect(page).toHaveURL(new RegExp(`/admin/course/${course.courseId}$`));
  });
});
