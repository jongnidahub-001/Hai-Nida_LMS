import { test, expect, Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { ADMIN_STATE } from './support/env';
import { deleteCourse, deleteTask, findCoursesByName, listTasks } from './support/api';

// สร้างคอร์สจาก PDF ด้วย Gemini จริงตั้งแต่ Import จนบันทึกลงฐานข้อมูล ใช้เวลาหลายนาทีและมีค่า API
test.use({ storageState: ADMIN_STATE });
test.describe.configure({ mode: 'serial' });

const stamp = Date.now();
const docName = `e2e-${stamp}.pdf`;
const brokenDocName = `e2e-broken-${stamp}.pdf`;
const courseName = `E2E AI Generated ${stamp}`;
const samplePdf = fs.readFileSync(path.resolve(__dirname, '../../tests/Marketing Research.pdf'));

const field = (page: Page, label: string) =>
  page.locator(`.modal.is-active label:text-is("${label}")`).locator('xpath=following::input[1]');

async function importDocument(page: Page, name: string, buffer: Buffer) {
  await page.goto('/admin/courses');
  await page.getByRole('button', { name: 'Import Document' }).first().click();
  const modal = page.locator('.modal.is-active');
  await modal.locator('input[type="file"]').setInputFiles({ name, mimeType: 'application/pdf', buffer });
  // ลดจำนวนคำถามให้น้อยที่สุดเพื่อประหยัดเวลาและค่า API
  await field(page, 'Total Questions').fill('3');
  await field(page, 'Multiple Choice Questions').fill('1');
  await field(page, 'Subjective Questions').fill('1');
  await field(page, 'Fill in the Blank Questions').fill('1');
  await modal.getByRole('button', { name: 'Generate All Levels' }).click();
  await expect(modal).toBeHidden({ timeout: 60_000 });
  await expect(page.getByText('Background Tasks')).toBeVisible();
  return page.locator('tbody tr', { hasText: name });
}

/** รอจนสถานะในแถวตรงกับที่ต้องการ กด Refresh เป็นระยะ */
async function waitForRow(page: Page, rows: ReturnType<Page['locator']>, text: string, timeout: number) {
  await expect(async () => {
    await page.getByRole('button', { name: 'Refresh' }).click();
    await expect(rows.filter({ hasText: text }).first()).toBeVisible({ timeout: 5_000 });
  }).toPass({ timeout, intervals: [15_000] });
  return rows.filter({ hasText: text }).first();
}

async function waitForIdle(button: ReturnType<Page['locator']>, timeout: number) {
  await expect(button).toHaveClass(/is-loading/, { timeout: 10_000 }).catch(() => {});
  await expect(button).not.toHaveClass(/is-loading/, { timeout });
}

test.afterAll(async ({ request }) => {
  for (const c of await findCoursesByName(request, courseName)) await deleteCourse(request, c.course_id);
  for (const t of await listTasks(request)) {
    if (t.document_name === docName || t.document_name === brokenDocName) await deleteTask(request, t.task_id);
  }
});

test.describe('สร้างคอร์สด้วย AI', { tag: '@ai' }, () => {
  test('Import PDF สร้างงาน 3 ระดับ แก้คอร์สและ quiz แล้วบันทึกลงระบบ', async ({ page }) => {
    test.setTimeout(45 * 60_000);

    const rows = await importDocument(page, docName, samplePdf);
    await expect(rows).toHaveCount(3);
    for (const level of ['Casual', 'Regular', 'Intense']) {
      await expect(rows.filter({ hasText: level })).toHaveCount(1);
    }

    const done = await waitForRow(page, rows, 'Completed', 25 * 60_000);
    await done.getByRole('button', { name: 'Preview' }).click();
    await expect(page.getByText('Review the generated course content')).toBeVisible();

    // แท็บ log และ diagram ของ agent
    await page.locator('.tabs').getByText('Agent Logs').first().click();
    await expect(page.getByText('Agent Processing Logs')).toBeVisible();
    await page.locator('.tabs').getByText('Agent Diagram').first().click();
    await expect(page.getByText('Agent Pipeline Flow')).toBeVisible();
    await page.locator('.tabs').getByText('Course Preview').first().click();

    // สร้างเนื้อหาคอร์สใหม่ทั้งชุด
    const regenCourse = page.getByRole('button', { name: 'Re-Generate' });
    await regenCourse.click();
    await waitForIdle(regenCourse, 15 * 60_000);
    await expect(page.getByText('Review the generated course content')).toBeVisible();

    await page.getByPlaceholder('Enter course name').fill(courseName);

    // แก้บทเรียนแรกด้วยคำสั่งให้ AI
    const lesson = page.locator('.card', { has: page.locator('.card-header') }).first();
    await lesson.getByRole('button', { name: 'Edit' }).click();
    await lesson.getByPlaceholder(/Make the content more beginner-friendly/).fill('Make this lesson shorter and add one real-world example.');
    await lesson.getByRole('button', { name: 'Regenerate Lesson' }).click();
    await expect(lesson.getByRole('button', { name: 'Save Changes' })).toBeVisible({ timeout: 5 * 60_000 });
    await lesson.getByRole('button', { name: 'Save Changes' }).click();
    await expect(lesson.getByRole('button', { name: 'Save Changes' })).toBeHidden();

    // สร้าง quiz
    await page.getByRole('button', { name: 'Create Quiz' }).click();
    await expect(page.getByText('Review the generated quiz content')).toBeVisible({ timeout: 15 * 60_000 });

    const regenQuiz = page.getByRole('button', { name: 'Re-Generate' });
    await regenQuiz.click();
    await waitForIdle(regenQuiz, 15 * 60_000);

    // แก้คำถามข้อแรกด้วยคำสั่งให้ AI
    // ปุ่ม Edit หายไปเมื่อเข้าโหมดแก้ไข จึงหาการ์ดใหม่จากช่องพิมพ์คำสั่งแทน
    await page.locator('.card', { has: page.getByRole('button', { name: 'Edit' }) }).first()
      .getByRole('button', { name: 'Edit' }).click();
    const question = page.locator('.card', { has: page.getByPlaceholder(/Make the question harder/) });
    await question.getByPlaceholder(/Make the question harder/).fill('Make this question a little harder.');
    await question.getByRole('button', { name: 'Regenerate Question' }).click();
    await expect(question.getByRole('button', { name: 'Save Changes' })).toBeVisible({ timeout: 5 * 60_000 });
    await question.getByRole('button', { name: 'Save Changes' }).click();

    // กลับไปหน้าคอร์สแล้วกลับมาที่ quiz ได้
    await page.getByRole('button', { name: 'Back to Course Preview' }).click();
    await expect(page.getByText('Review the generated course content')).toBeVisible();
    await page.getByRole('button', { name: 'Create Quiz' }).click();
    await expect(page.getByText('Review the generated quiz content')).toBeVisible({ timeout: 15 * 60_000 });

    await page.getByRole('button', { name: 'Submit Quiz' }).click();
    await expect(page.getByText('Course and Quiz saved to database successfully!')).toBeVisible({ timeout: 5 * 60_000 });
    await page.getByRole('button', { name: 'OK' }).click();

    // คอร์สใหม่ขึ้นในรายการ และงานเปลี่ยนเป็น Generated
    await page.locator('.tabs').getByText('Courses', { exact: true }).click();
    await page.getByPlaceholder('Search courses by name or description...').fill(courseName);
    await expect(page.locator('.column.is-4', { hasText: courseName })).toBeVisible();
    await page.locator('.tabs').getByText('Process', { exact: true }).click();
    await waitForRow(page, rows, 'Generated', 60_000);
  });

  test('งานที่ล้มเหลวกด Retry ได้และลบงานผ่านหน้าจอได้', async ({ page }) => {
    test.setTimeout(20 * 60_000);
    const rows = await importDocument(page, brokenDocName, Buffer.from('this is not a real pdf file'));
    await expect(rows).toHaveCount(3);

    const failed = await waitForRow(page, rows, 'Failed', 15 * 60_000);
    await failed.getByRole('button', { name: 'Retry' }).click();
    await expect(page.getByText(/Task queued for retry/)).toBeVisible();

    const count = await rows.count();
    // ปุ่มลบของงานที่ล้มเหลวไม่มี title จึงหาจากไอคอนถังขยะ
    await rows.first().locator('button:has(.fa-trash)').click();
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(page.getByText('Task deleted successfully')).toBeVisible();
    await expect(rows).toHaveCount(count - 1);
  });
});
