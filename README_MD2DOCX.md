# คู่มือการใช้งาน md_to_docx.py

สคริปต์ Python สำหรับแปลงไฟล์ Markdown (.md) เป็นไฟล์ Word (.docx)

## การติดตั้ง

### วิธีที่ 1: ใช้ pypandoc (แนะนำ)

1. ติดตั้ง pandoc:
   - **Windows**: ดาวน์โหลดจาก https://pandoc.org/installing.html
   - **macOS**: `brew install pandoc`
   - **Linux**: `sudo apt-get install pandoc` หรือ `sudo yum install pandoc`

2. ติดตั้งไลบรารี Python:
   ```bash
   pip install pypandoc
   ```

### วิธีที่ 2: ใช้ markdown + python-docx (ไม่ต้องติดตั้ง pandoc)

```bash
pip install python-docx markdown beautifulsoup4
```

หรือติดตั้งทั้งหมด:

```bash
pip install -r requirements_md2docx.txt
```

## การใช้งาน

### คำสั่งพื้นฐาน

```bash
python md_to_docx.py input.md
```

จะสร้างไฟล์ `input.docx` ในโฟลเดอร์เดียวกัน

### ระบุไฟล์ output

```bash
python md_to_docx.py input.md -o output.docx
```

หรือ

```bash
python md_to_docx.py input.md --output output.docx
```

## ตัวอย่างการใช้งาน

```bash
# สร้างคู่มือผู้ใช้ฉบับ Word จาก USER_MANUAL.md
python md_to_docx.py USER_MANUAL.md -o คู่มือการใช้งาน.docx

# สร้างคู่มือติดตั้งฉบับ Word จาก DEPLOY.md
python md_to_docx.py DEPLOY.md -o คู่มือการติดตั้งและดูแลระบบ.docx
```

## ฟีเจอร์ที่รองรับ

- ✅ หัวข้อ (H1-H6)
- ✅ ย่อหน้า
- ✅ รายการ (Bullet และ Numbered)
- ✅ รูปภาพ (จากโฟลเดอร์ images/)
- ✅ ตาราง
- ✅ Code blocks
- ✅ Bold, Italic
- ✅ Links

## หมายเหตุ

- รูปภาพจะถูกค้นหาใน:
  1. path ที่ระบุใน markdown
  2. โฟลเดอร์เดียวกับไฟล์ .md
  3. โฟลเดอร์ `images/` ในโฟลเดอร์เดียวกับไฟล์ .md

- ถ้าไม่พบรูปภาพ จะแสดง warning แต่จะยังคงแปลงไฟล์ต่อ

## Troubleshooting

### Error: pypandoc not available
- ติดตั้ง pypandoc: `pip install pypandoc`
- หรือติดตั้ง pandoc แล้วติดตั้ง pypandoc

### Error: pandoc not found
- ติดตั้ง pandoc จาก https://pandoc.org/installing.html
- หรือใช้วิธีที่ 2 (markdown + python-docx)

### Error: python-docx not found
- ติดตั้ง: `pip install python-docx markdown beautifulsoup4`

### รูปภาพไม่แสดง
- ตรวจสอบว่าไฟล์รูปภาพอยู่ใน path ที่ถูกต้อง
- ตรวจสอบว่า path ใน markdown ถูกต้อง (เช่น `images/logo.png`)

