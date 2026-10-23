import { test, expect } from '@playwright/test';
import { QUESTION_PATTERN, createLearner, deleteCourse, deleteUserByEmail, Learner, SeededCourse, seedCourse, signInPage } from './support/api';

// เส้นทางของผู้เรียนตั้งแต่หาคอร์สจนเรียนจบบทเรียน ไม่มีขั้นตอนที่เรียก Gemini
test.describe.configure({ mode: 'serial' });

let learner: Learner;
let course: SeededCourse;

test.beforeAll(async ({ request }) => {
  course = await seedCourse(request, 'Learner');
  learner = await createLearner(request, 'learner');
});

test.afterAll(async ({ request }) => {
  await deleteUserByEmail(request, learner.email);
  await deleteCourse(request, course.courseId);
});

test.beforeEach(async ({ page }) => {
  await signInPage(page, learner.token);
});

test('Dashboard ของผู้เรียนแสดงเมนูผู้เรียนและไม่มีเมนู admin', async ({ page }) => {
  await page.goto('/home');
  const nav = page.locator('nav');
  await expect(nav.getByText('Dashboard')).toBeVisible();
  await expect(nav.getByText('All Courses')).toBeVisible();
  await expect(nav.getByText('All Users')).toHaveCount(0);
  await expect(nav.getByText('Setting')).toHaveCount(0);
});

test('หน้า All Courses ค้นหาและกรองระดับความยากได้', async ({ page }) => {
  await page.goto('/courses');
  const search = page.getByPlaceholder('Search courses by name or description...');
  const card = page.locator('.column.is-4', { hasText: course.name });

  await search.fill(course.name);
  await expect(card).toBeVisible();
  await expect(card.getByText('2 lessons')).toBeVisible();

  await page.locator('select').first().selectOption('Intense');
  await expect(card).toHaveCount(0);
  await page.locator('select').first().selectOption('Casual');
  await expect(card).toBeVisible();

  await search.fill('no-such-course-xyz');
  await expect(page.getByText('No courses found')).toBeVisible();
});

test('เปิดรายละเอียดคอร์สแล้วลงทะเบียนด้วย Start Course', async ({ page }) => {
  await page.goto('/courses');
  await page.getByPlaceholder('Search courses by name or description...').fill(course.name);
  await page.locator('.column.is-4', { hasText: course.name }).getByRole('button').click();
  await expect(page).toHaveURL(new RegExp(`/course/${course.courseId}$`));

  const header = page.locator('.course-header-card');
  await expect(header).toContainText(course.name);
  await expect(header).toContainText('Not Enrolled');
  for (const title of course.lessons) {
    await expect(page.locator('.lesson-item', { hasText: title })).toBeVisible();
  }

  await page.getByRole('button', { name: 'Start Course' }).click();
  await expect(page.getByRole('button', { name: 'Continue Course' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Take Assessment' })).toBeVisible();
});

test('เรียนบทเรียน กด Mark as Complete และเปลี่ยนบทจากแถบด้านข้าง', async ({ page }) => {
  await page.goto(`/course/${course.courseId}`);
  await page.getByRole('button', { name: 'Continue Course' }).click();
  await expect(page).toHaveURL(/\/lesson\//);

  const content = page.locator('.lesson-content-card');
  await expect(content).toContainText('The capital of France is Paris');
  await expect(page.getByText('0 of 2 lessons completed')).toBeVisible();

  await page.getByRole('button', { name: 'Mark as Complete' }).click();
  await expect(page.getByRole('button', { name: 'Mark as Complete' })).toBeHidden();
  await expect(page.getByText('1 of 2 lessons completed')).toBeVisible();

  await page.locator('.lesson-nav-item', { hasText: course.lessons[1] }).click();
  await expect(content).toContainText('The Danube flows through Vienna');
  await expect(page.getByRole('button', { name: 'Mark as Complete' })).toBeVisible();
});

test('คอร์สที่ลงทะเบียนแล้วขึ้นใน Dashboard', async ({ page }) => {
  await page.goto('/home');
  await expect(page.locator('.home-courses-card').getByText(course.name).first()).toBeVisible();
  await page.getByRole('link', { name: 'Resume' }).click();
  await expect(page.locator('.home-courses-card').getByText(course.name).first()).toBeVisible();
  await page.getByRole('link', { name: 'Complete' }).click();
  await expect(page.locator('.home-courses-card').getByText('No courses found')).toBeVisible();
});

test('ยังไม่ทำ quiz คอร์สจะขึ้นสถานะ Not Attempted', async ({ page }) => {
  await page.goto('/home');
  const row = page.locator('.home-course-row', { hasText: course.name }).filter({ hasText: 'Score' });
  await expect(row.getByText('Not Attempted')).toBeVisible();
});

test('เปิดหน้า quiz เห็นคำถามข้อแรกและเลื่อนไปข้อถัดไปได้', async ({ page }) => {
  await page.goto(`/course/${course.courseId}`);
  await page.getByRole('button', { name: 'Take Assessment' }).click();
  await expect(page).toHaveURL(/\/quiz$/);
  await expect(page.getByRole('heading', { name: `${course.name} Quiz` })).toBeVisible();

  // ลำดับคำถามที่ API ส่งมาไม่คงที่ จึงตรวจจากหัวข้อคำถามที่แสดงอยู่
  const heading = page.locator('h3');
  await expect(heading).toHaveText(QUESTION_PATTERN);
  const first = await heading.textContent();
  await page.getByRole('button', { name: 'Next Question' }).click();
  await expect(heading).toHaveText(QUESTION_PATTERN);
  await expect(heading).not.toHaveText(first!);
  await page.getByRole('button', { name: 'Previous Question' }).click();
  await expect(heading).toHaveText(first!);
});
