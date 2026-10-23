import { test, expect } from '@playwright/test';
import { ADMIN_STATE } from './support/env';
import {
  createLearner, deleteCourse, deleteUserByEmail, enroll, findCoursesByName, findUser, Learner, SeededCourse, seedCourse,
} from './support/api';

// การจัดการผู้ใช้และคอร์สของ admin ใช้ข้อมูลที่สร้างผ่าน API ไม่มีขั้นตอนที่เรียก Gemini
test.use({ storageState: ADMIN_STATE });

let learner: Learner;
let course: SeededCourse;

test.beforeAll(async ({ request }) => {
  course = await seedCourse(request, 'Admin');
  learner = await createLearner(request, 'admin');
  await enroll(request, learner.token, course.courseId);
});

test.afterAll(async ({ request }) => {
  await deleteUserByEmail(request, learner.email);
  await deleteCourse(request, course.courseId);
});

test.describe('คอร์ส', () => {
  test('ค้นหาคอร์สในหน้า Course Management ได้', async ({ page }) => {
    await page.goto('/admin/courses');
    const search = page.getByPlaceholder('Search courses by name or description...');
    const card = page.locator('.column.is-4', { hasText: course.name });

    await search.fill(course.name);
    await expect(card).toBeVisible();
    await expect(card.getByText('Casual')).toBeVisible();
    await expect(card.getByText('1 enrolled')).toBeVisible();

    await search.fill('no-such-course-xyz');
    await expect(page.getByText('No courses found')).toBeVisible();
  });

  test('รายละเอียดคอร์สแสดงบทเรียน quiz และผู้ลงทะเบียน', async ({ page }) => {
    await page.goto('/admin/courses');
    await page.getByPlaceholder('Search courses by name or description...').fill(course.name);
    await page.locator('.column.is-4', { hasText: course.name }).getByRole('button', { name: 'View Details' }).click();
    await expect(page).toHaveURL(new RegExp(`/admin/course/${course.courseId}$`));
    await expect(page.getByRole('heading', { name: course.name })).toBeVisible();

    await expect(page.getByText('Lessons (2)')).toBeVisible();
    for (const title of course.lessons) await expect(page.getByText(title).first()).toBeVisible();

    await page.locator('.tabs').getByText('Quiz', { exact: true }).click();
    await expect(page.getByText('Quiz Content')).toBeVisible();
    await expect(page.getByText('What is the capital of Japan?')).toBeVisible();
    await expect(page.getByText('The capital of France is ____.')).toBeVisible();

    await page.locator('.tabs').getByText('Enrolled Users (1)').click();
    const row = page.locator('tbody tr', { hasText: learner.email });
    await expect(row).toBeVisible();
    await expect(row.getByText('Not Attempted')).toBeVisible();
  });

  test('ลบคอร์สผ่านปุ่ม Delete Course', async ({ page, request }) => {
    const temp = await seedCourse(request, 'Delete');
    try {
      await page.goto(`/admin/course/${temp.courseId}`);
      await expect(page.getByRole('heading', { name: temp.name })).toBeVisible();
      await page.getByRole('button', { name: 'Delete Course' }).click();
      await page.getByRole('button', { name: 'Yes, Delete Course' }).click();

      await expect(page).toHaveURL(/\/admin\/courses$/);
      await expect.poll(async () => (await findCoursesByName(request, temp.name)).length).toBe(0);
    } finally {
      await deleteCourse(request, temp.courseId);
    }
  });
});

test.describe('ผู้ใช้', () => {
  test('รายละเอียดผู้ใช้แสดงคอร์สที่ลงทะเบียนและลิงก์ไปหน้าคอร์ส', async ({ page }) => {
    await page.goto('/admin');
    await page.getByPlaceholder('Search users...').fill(learner.email);
    await page.locator('tbody tr', { hasText: learner.email }).getByRole('button', { name: 'View Details' }).click();
    await expect(page).toHaveURL(/\/admin\/user\//);
    await expect(page.locator('.tag', { hasText: learner.email })).toBeVisible();

    await expect(page.getByText('Enrolled Courses (1)')).toBeVisible();
    await expect(page.getByText(course.name)).toBeVisible();
    await page.locator('.tabs').getByText('Quiz Results (0)').click();

    await page.locator('.tabs').getByText('Enrolled Courses (1)').click();
    await page.getByRole('button', { name: 'View Course' }).click();
    await expect(page).toHaveURL(new RegExp(`/admin/course/${course.courseId}$`));
  });

  test('ปุ่ม Back to Users กลับไปหน้า All Users', async ({ page, request }) => {
    const user = await findUser(request, learner.email);
    await page.goto(`/admin/user/${user!.user_id}`);
    await page.getByRole('button', { name: 'Back to Users' }).click();
    await expect(page).toHaveURL(/\/admin$/);
  });

  test('ลบผู้ใช้จากตาราง All Users', async ({ page, request }) => {
    const temp = await createLearner(request, 'deltable');
    try {
      await page.goto('/admin');
      await page.getByPlaceholder('Search users...').fill(temp.email);
      await page.locator('tbody tr', { hasText: temp.email }).getByRole('button', { name: 'Delete' }).click();
      await page.locator('.modal.is-active').getByRole('button', { name: 'Delete User' }).click();
      await expect(page.locator('tbody tr', { hasText: temp.email })).toHaveCount(0);
      expect(await findUser(request, temp.email)).toBeUndefined();
    } finally {
      await deleteUserByEmail(request, temp.email);
    }
  });

  test('ลบผู้ใช้จากหน้ารายละเอียดผู้ใช้', async ({ page, request }) => {
    const temp = await createLearner(request, 'deldetail');
    try {
      const user = await findUser(request, temp.email);
      await page.goto(`/admin/user/${user!.user_id}`);
      await page.getByRole('button', { name: 'Delete User' }).first().click();
      await page.locator('.modal.is-active').getByRole('button', { name: 'Delete User' }).click();
      await expect(page).toHaveURL(/\/admin$/);
      expect(await findUser(request, temp.email)).toBeUndefined();
    } finally {
      await deleteUserByEmail(request, temp.email);
    }
  });

  test('ปุ่มลบของบัญชี admin ถูกปิดไว้', async ({ page }) => {
    await page.goto('/admin');
    const adminRow = page.locator('tbody tr', { has: page.locator('.tag.is-danger', { hasText: 'admin' }) }).first();
    await expect(adminRow.getByRole('button', { name: 'Delete' })).toBeDisabled();
  });
});

test.describe('หน้าอื่นของ admin', () => {
  test('หน้า All Quiz Scores เปิดได้และค้นหาได้', async ({ page }) => {
    await page.goto('/admin/quizzes');
    await expect(page.getByText('All Quiz Scores')).toBeVisible();
    await page.getByPlaceholder('Search by username or course...').fill('no-such-user-xyz');
    await expect(page.locator('tbody tr')).toHaveCount(0);
  });

  test('หน้า Setting แสดง API key แบบซ่อนและ model ของแต่ละ role', async ({ page }) => {
    await page.goto('/admin/settings');
    // หน้านี้ดึงรายชื่อ model จาก Google ก่อนแสดงผล จึงใช้เวลานานกว่าหน้าอื่น
    await expect(page.getByText('Gemini API Settings')).toBeVisible({ timeout: 60_000 });
    const key = page.locator('code').first();
    await expect(key).not.toHaveText('Not configured');
    await expect(key).not.toHaveText(/^AIza[\w-]{35}$/);
    await expect(page.getByText('Model Configuration by Role')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(3);
    await expect(page.getByText('Available Models')).toBeVisible();
  });

  test('หน้าต่าง Change Key ปิดได้โดยไม่บันทึก', async ({ page }) => {
    await page.goto('/admin/settings');
    await page.getByRole('button', { name: /Change Key|Set Key/ }).click({ timeout: 60_000 });
    const modal = page.locator('.modal.is-active');
    await expect(modal.getByPlaceholder(/Enter your Gemini API key/)).toBeVisible();
    await expect(modal.getByRole('button', { name: 'Save' })).toBeDisabled();
    await modal.getByRole('button', { name: 'Cancel' }).click();
    await expect(modal).toBeHidden();
  });
});
