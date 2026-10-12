# การติดตั้งและดูแลระบบ Hai-Nida บน Google Cloud

เอกสารนี้อธิบายการติดตั้ง Hai-Nida ลงใน Google Cloud project ของท่าน การรับเวอร์ชันใหม่ และการดูแลระบบหลังติดตั้ง

ระบบทำงานบน VM เครื่องเดียว ภายในรัน Docker 4 container ได้แก่ Caddy (รับ request จากภายนอกและออกใบรับรอง HTTPS), frontend, backend และ ChromaDB (ฐานข้อมูล) ค่าลับทั้งหมด เช่น Gemini API key และรหัส admin เก็บใน Secret Manager ของ project ท่าน ไม่มีอยู่ใน repo

VM ดึงโค้ดจาก branch `release` ของ repo เองทุก 5 นาที เมื่อทีมพัฒนาปล่อยเวอร์ชันใหม่ ระบบจะ backup ข้อมูล build และตรวจว่าใช้งานได้ ถ้าตรวจไม่ผ่านจะกลับไปใช้เวอร์ชันเดิมให้อัตโนมัติ

## 1. สิ่งที่ต้องมีก่อนเริ่ม

1. Google Cloud project ที่ผูก billing account แล้ว และบัญชีของผู้ติดตั้งมีบทบาท Owner ใน project นั้น (หรือ Editor ร่วมกับ Security Admin และ Secret Manager Admin)
2. บัญชี GitHub ที่รับคำเชิญเข้า repo นี้แล้ว
3. Cloud Shell ใน Google Cloud Console (มี `gcloud` และ `git` พร้อมใช้) หรือเครื่องที่ติดตั้ง Google Cloud CLI แล้ว

## 2. ติดตั้งครั้งแรก

เปิด Cloud Shell แล้ว clone repo (ระบบจะถามชื่อผู้ใช้ GitHub และให้ใช้ personal access token แทนรหัสผ่าน)

```bash
git clone https://github.com/<เจ้าของ repo>/Hai-Nida.git
cd Hai-Nida
```

สั่งติดตั้ง โดยแทน `<PROJECT_ID>` ด้วย ID ของ project

```bash
./scripts/bootstrap-gcp.sh --project <PROJECT_ID>
```

ถ้าต้องการดูก่อนว่าสคริปต์จะสร้างอะไรบ้าง ให้เพิ่ม `--dry-run` ระบบจะแสดงคำสั่งทั้งหมดโดยไม่สร้างอะไรจริง

ระหว่างติดตั้ง สคริปต์จะแสดง public key ของ deploy key และหยุดรอ ให้ส่ง key นี้ให้ทีมพัฒนาเพิ่มเข้า repo (key นี้อ่าน repo ได้อย่างเดียว) เมื่อทีมพัฒนาแจ้งว่าเพิ่มแล้วให้กด Enter สคริปต์จะทำงานต่อ ถ้าปิดหน้าจอไปก่อน รันคำสั่งเดิมซ้ำได้ ส่วนที่สร้างแล้วจะถูกข้าม

การติดตั้งใช้เวลาประมาณ 10 ถึง 20 นาที เมื่อเสร็จจะแสดง URL ของระบบ อีเมลและรหัสผ่านของ admin ให้บันทึกรหัสผ่านไว้ทันที เพราะจะแสดงเพียงครั้งเดียว แล้วเปลี่ยนรหัสหลัง login ครั้งแรก

สคริปต์จะสร้างทรัพยากรเหล่านี้ใน project

| ทรัพยากร | ชื่อ |
|---|---|
| VM (Ubuntu 24.04, e2-medium, disk 30 GB) | `hai-nida` |
| Static IP | `hai-nida-ip` |
| Firewall | `hai-nida-allow-web` (port 80, 443), `hai-nida-allow-iap-ssh` (port 22 เฉพาะผ่าน IAP) |
| Service account ของ VM | `hai-nida-vm` อ่านได้เฉพาะ secret ของระบบ |
| Secret Manager | `hai-nida-google-api-key`, `hai-nida-secret-key`, `hai-nida-admin-password`, `hai-nida-app-config`, `hai-nida-repo-deploy-key` |
| Gemini API key | `hai-nida-gemini` ใช้ได้เฉพาะ Gemini API |
| Snapshot ของ disk | `hai-nida-daily-snapshot` ทุกวัน 02:00 น. เก็บ 7 วัน |
| Bucket สำหรับ backup | `<PROJECT_ID>-hai-nida-backups` เก็บไฟล์ 30 วัน |

ปรับค่าตั้งต้นได้ด้วยตัวเลือกของสคริปต์ (ดูทั้งหมดด้วย `--help`) หรือคัดลอก `deploy.env.example` เป็น `deploy.env` แล้วแก้ค่า ตัวเลือกที่ใช้บ่อยได้แก่ `--domain` สำหรับใช้โดเมน, `--gemini-key` ถ้ามี Gemini API key อยู่แล้ว, `--machine-type` และ `--zone`

คำสั่งในหัวข้อถัดไปอ่าน project จาก `deploy.env` ได้ ถ้าใส่ `PROJECT_ID` ไว้ในไฟล์นั้นก็ไม่ต้องพิมพ์ `--project` ทุกครั้ง

## 3. การรับเวอร์ชันใหม่

ไม่ต้องทำอะไร VM จะตรวจ branch `release` ทุก 5 นาที และอัปเดตเมื่อมี commit ใหม่ ระหว่างอัปเดตระบบอาจหยุดตอบสนองประมาณ 1 ถึง 3 นาที

ถ้าต้องการอัปเดตทันที

```bash
./scripts/update-now.sh --project <PROJECT_ID>
```

ดู log การอัปเดต

```bash
gcloud compute ssh hai-nida --zone asia-southeast1-b --project <PROJECT_ID> --tunnel-through-iap \
  --command 'journalctl -u hai-nida-update -n 100 --no-pager'
```

ถ้าเวอร์ชันใหม่ตรวจไม่ผ่าน ระบบจะกลับไปใช้เวอร์ชันเดิม และจะไม่ลองเวอร์ชันนั้นซ้ำจนกว่าทีมพัฒนาจะปล่อย commit ใหม่ ให้แจ้งทีมพัฒนาพร้อม log ข้างต้น

## 4. การเปลี่ยน API key และรหัสผ่าน

ใช้ `scripts/rotate-secret.sh` สคริปต์จะบันทึกค่าใหม่ใน Secret Manager แล้วสั่ง VM ใช้ค่าใหม่ทันที

```bash
./scripts/rotate-secret.sh google-api-key --project <PROJECT_ID>
```

| ค่าที่เปลี่ยน | คำสั่ง | หมายเหตุ |
|---|---|---|
| Gemini API key | `rotate-secret.sh google-api-key` | ถ้า admin เคยใส่ API key ในหน้า Admin > Settings ระบบจะใช้ key ในหน้านั้นก่อน |
| Secret key สำหรับ login | `rotate-secret.sh secret-key` | ผู้ใช้ทุกคนต้อง login ใหม่ |
| ค่าตั้งค่าทั่วไป | `rotate-secret.sh app-config` | เปิดไฟล์ให้แก้ เช่น `SITE_ADDRESS` |
| deploy key ของ repo | `rotate-secret.sh repo-deploy-key` | ต้องให้ทีมพัฒนาเพิ่ม key ใหม่และลบ key เก่า |

รหัสผ่านของ admin ให้เปลี่ยนผ่านหน้าเว็บ ค่า `hai-nida-admin-password` ใช้สร้าง admin คนแรกตอนติดตั้งเท่านั้น การเปลี่ยนค่านี้ภายหลังไม่มีผลกับ admin ที่มีอยู่แล้ว

## 5. การใช้โดเมนและ HTTPS

1. สร้าง DNS record ชนิด A ให้โดเมน (เช่น `lms.example.com`) ชี้ไปที่ static IP ของระบบ ดู IP ได้ด้วย `gcloud compute addresses describe hai-nida-ip --region asia-southeast1 --project <PROJECT_ID> --format='value(address)'`
2. รัน `./scripts/rotate-secret.sh app-config --project <PROJECT_ID>` แล้วเพิ่มบรรทัด `SITE_ADDRESS=lms.example.com`
3. Caddy จะออกใบรับรอง HTTPS ให้อัตโนมัติภายในไม่กี่นาทีหลัง DNS มีผล

ถ้าติดตั้งใหม่และมีโดเมนอยู่แล้ว ใส่ `--domain lms.example.com` ตอนรัน bootstrap ได้เลย ห้ามใส่ `SITE_ADDRESS=` แบบไม่มีค่า ถ้าเลิกใช้โดเมนให้ลบทั้งบรรทัด

## 6. Backup และ restore

ข้อมูลของระบบมี 2 ส่วน คือฐานข้อมูล ChromaDB (ผู้ใช้ คอร์ส ผลแบบทดสอบ) และไฟล์ PDF ที่อัปโหลด ระบบ backup ให้ 3 ชั้น

1. ChromaDB ทุกวัน 03:00 น. เก็บในเครื่อง 7 ชุดที่ `/opt/hai-nida/backups/chromadb/` และอัปโหลดขึ้น bucket `<PROJECT_ID>-hai-nida-backups` เก็บ 30 วัน ทุกครั้งที่อัปเดตเวอร์ชันจะ backup ก่อนด้วย
2. Snapshot ของ disk ทั้งเครื่องทุกวัน 02:00 น. เก็บ 7 วัน ครอบคลุมทั้ง ChromaDB และไฟล์ PDF
3. VM ลบหรือแก้ไฟล์ใน bucket ไม่ได้ ถ้าเครื่องถูกบุกรุก backup ใน bucket จะยังอยู่

restore ChromaDB จาก backup ในเครื่อง

```bash
gcloud compute ssh hai-nida --zone asia-southeast1-b --project <PROJECT_ID> --tunnel-through-iap
sudo -u deploy /opt/hai-nida/restore-chromadb.sh
```

สคริปต์จะแสดงรายการ backup ให้เลือก และถามยืนยันก่อนเขียนทับข้อมูลปัจจุบัน

restore จาก bucket (เช่น เมื่อ backup ในเครื่องไม่มีแล้ว) ให้ดาวน์โหลดไฟล์มาที่ Cloud Shell ก่อน แล้วส่งขึ้น VM

```bash
gcloud storage ls gs://<PROJECT_ID>-hai-nida-backups/chromadb/
gcloud storage cp gs://<PROJECT_ID>-hai-nida-backups/chromadb/<ชื่อไฟล์> .
gcloud compute scp <ชื่อไฟล์> hai-nida:/tmp/ --zone asia-southeast1-b --project <PROJECT_ID> --tunnel-through-iap
```

จากนั้น SSH เข้า VM แล้วรัน `sudo -u deploy /opt/hai-nida/restore-chromadb.sh /tmp/<ชื่อไฟล์>`

ถ้าต้องกู้ทั้งเครื่อง (เช่น disk เสียหาย) ให้สร้าง disk ใหม่จาก snapshot ตามคู่มือ Compute Engine เรื่อง restoring from a snapshot

## 7. การลบระบบ

```bash
./scripts/destroy-gcp.sh --project <PROJECT_ID>
```

สคริปต์จะให้พิมพ์ชื่อ project เพื่อยืนยัน และถามแยกว่าจะลบ backup (bucket และ snapshot) ด้วยหรือไม่ การลบ VM ทำให้ข้อมูลในระบบหายทั้งหมดและย้อนกลับไม่ได้ ดูก่อนได้ด้วย `--dry-run` หลังลบแล้วให้แจ้งทีมพัฒนาลบ deploy key ของ project นี้ออกจาก repo

## 8. ค่าใช้จ่ายโดยประมาณ

ตัวเลขด้านล่างเป็นค่าประมาณสำหรับ region asia-southeast1 (สิงคโปร์) แบบไม่มีส่วนลด ราคาจริงขึ้นกับการใช้งานและอาจเปลี่ยนแปลง ให้ตรวจสอบกับ [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator) ก่อนใช้อ้างอิง

| รายการ | ประมาณต่อเดือน (USD) |
|---|---|
| VM e2-medium | 30 |
| Disk pd-balanced 30 GB | 3.3 |
| Static IP ที่ผูกกับ VM | 3.7 |
| Snapshot, bucket backup, Secret Manager | ต่ำกว่า 2 ในการใช้งานปกติ |
| รวม | ประมาณ 40 |

ค่า Gemini API คิดตามปริมาณการใช้งานจริง ไม่รวมในตารางนี้ ตรวจได้ที่หน้า Billing ของ project

## 9. การแก้ปัญหาที่พบบ่อย

ถ้า bootstrap หยุดที่ขั้นตรวจสิทธิ์หรือ billing ให้ตรวจว่า project ผูก billing account แล้ว และบัญชีที่ใช้มีบทบาทตามหัวข้อที่ 1

ถ้า bootstrap รอ deploy key นาน แสดงว่าทีมพัฒนายังไม่ได้เพิ่ม key หรือ repo ยังไม่มี branch `release` กด Ctrl+C แล้วรันคำสั่งเดิมใหม่เมื่อพร้อม

ถ้า bootstrap แจ้งว่าติดตั้งบน VM ไม่สำเร็จ ให้ดู log ด้วย `gcloud compute instances get-serial-port-output hai-nida --zone asia-southeast1-b --project <PROJECT_ID>` แก้ตามสาเหตุแล้วรัน bootstrap ซ้ำ หรือ reboot VM (startup script จะทำงานใหม่ทุกครั้งที่ boot)

ถ้าเปิดเว็บไม่ได้ ให้ตรวจสถานะ container ด้วย `gcloud compute ssh ... --command 'cd /opt/hai-nida && sudo docker compose -f docker-compose.prod.yml ps'` และดู log ของ backend ด้วย `sudo docker compose -f docker-compose.prod.yml logs --tail=100 backend` (รันใน `/opt/hai-nida` บน VM)

ถ้า login admin ไม่ได้หลังติดตั้ง ดูรหัสผ่านที่ใช้สร้าง admin ได้ด้วย `gcloud secrets versions access latest --secret hai-nida-admin-password --project <PROJECT_ID>` ถ้าเปลี่ยนรหัสผ่านทางเว็บแล้วลืม ให้ติดต่อทีมพัฒนา

ถ้า HTTPS ไม่ทำงานหลังตั้งโดเมน ให้ตรวจว่า DNS ชี้ไปที่ static IP แล้ว (`dig +short lms.example.com`) และไม่มี proxy ขวางที่ port 80 และ 443 ดู log ของ Caddy ด้วย `sudo docker compose -f docker-compose.prod.yml logs caddy`

ถ้าระบบสร้างคอร์สไม่ได้ มักเกิดจาก Gemini API key ใช้ไม่ได้หรือเกินโควตา ตรวจ key ในหน้า Admin > Settings หรือเปลี่ยนด้วย `rotate-secret.sh google-api-key`

ถ้า disk เต็ม ระบบลบ Docker image เก่าหลังอัปเดตทุกครั้งอยู่แล้ว ถ้ายังเต็มให้เพิ่มขนาด disk ใน Compute Engine แล้ว reboot

## 10. สำหรับทีมพัฒนา (เจ้าของ repo)

การเชิญลูกค้า: ที่ GitHub > Settings > Collaborators เชิญด้วยสิทธิ์ Read ก็พอ ลูกค้าต้องการเพียง clone repo เพื่อรัน bootstrap

การเพิ่ม deploy key: เมื่อลูกค้าส่ง public key มา ให้เพิ่มที่ Settings > Deploy keys ตั้งชื่อตามที่ bootstrap แสดง (`hai-nida-vm (<PROJECT_ID>)`) และไม่ต้องเลือก Allow write access

การปล่อยเวอร์ชันใหม่: พัฒนาและทดสอบบน `main` ตามปกติ เมื่อพร้อมให้ลูกค้าใช้ ให้นำ `main` เข้า `release` (เปิด pull request จาก `main` ไป `release` หรือ `git push origin main:release`) ระบบของลูกค้าจะอัปเดตภายใน 5 นาที

การย้อนเวอร์ชัน: revert commit ที่มีปัญหาบน `release` แล้ว push ระบบของลูกค้าจะอัปเดตเป็นเวอร์ชันที่ revert แล้วเอง

การยกเลิกการเข้าถึง: ลบ deploy key ของ project นั้นออกจาก Settings > Deploy keys และลบ collaborator ระบบที่ติดตั้งแล้วจะยังทำงานต่อได้ แต่จะไม่ได้รับเวอร์ชันใหม่

workflow `.github/workflows/deploy.yml` ใช้ deploy ระบบของทีมพัฒนาเองเมื่อ push เข้า `main` ไม่เกี่ยวกับระบบของลูกค้า
