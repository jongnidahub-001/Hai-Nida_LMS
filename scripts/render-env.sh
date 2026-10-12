#!/bin/bash
# สร้าง .env.prod จาก Secret Manager ใช้บน VM ที่ติดตั้งด้วย scripts/bootstrap-gcp.sh
# อ่าน token ของ service account จาก metadata server จึงไม่ต้องมี gcloud บนเครื่อง
# ใช้: scripts/render-env.sh [ไฟล์ปลายทาง]   (default: <repo>/.env.prod)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$PROJECT_DIR/.env.prod}"
METADATA="http://metadata.google.internal/computeMetadata/v1"

die() {
  echo "render-env: $*" >&2
  exit 1
}

metadata() {
  curl -fsS -H "Metadata-Flavor: Google" "$METADATA/$1"
}

# ส่ง token ผ่าน stdin ของ curl ไม่ให้ไปอยู่ใน argument ของ process
secret() {
  local name="$1" body
  body=$(printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" |
    curl -fsS -K - "https://secretmanager.googleapis.com/v1/projects/$PROJECT_ID/secrets/$name/versions/latest:access") ||
    die "อ่าน secret $name ไม่ได้ (ตรวจว่ามี secret และ service account ของ VM มีสิทธิ์ secretAccessor)"
  jq -r '.payload.data' <<<"$body" | base64 -d
}

PROJECT_ID=$(metadata project/project-id) || die "ติดต่อ metadata server ไม่ได้ สคริปต์นี้ต้องรันบน VM ของ GCP"
TOKEN=$(metadata instance/service-accounts/default/token | jq -r '.access_token')
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] || die "ขอ token ของ service account ไม่ได้"

GOOGLE_API_KEY=$(secret hai-nida-google-api-key)
SECRET_KEY=$(secret hai-nida-secret-key)
ADMIN_PASSWORD=$(secret hai-nida-admin-password)
APP_CONFIG=$(secret hai-nida-app-config)

TMP=$(mktemp "$OUT.XXXXXX")
trap 'rm -f "$TMP"' EXIT
chmod 600 "$TMP"

{
  echo "# สร้างโดย scripts/render-env.sh จาก Secret Manager ห้ามแก้ไฟล์นี้ด้วยมือ"
  # ค่าที่ไม่ลับจาก hai-nida-app-config ข้ามบรรทัดว่าง คอมเมนต์ ค่าว่าง และคีย์ที่เป็น secret
  # ค่าว่างต้องข้าม เพราะ SITE_ADDRESS= ทำให้ Caddy อ่าน Caddyfile ไม่ผ่าน
  while IFS= read -r line; do
    case "$line" in
      '' | '#'* | *=) continue ;;
      GOOGLE_API_KEY=* | SECRET_KEY=* | ADMIN_PASSWORD=*) continue ;;
    esac
    printf '%s\n' "$line"
  done <<<"$APP_CONFIG"
  printf 'GOOGLE_API_KEY=%s\n' "$GOOGLE_API_KEY"
  printf 'SECRET_KEY=%s\n' "$SECRET_KEY"
  printf 'ADMIN_PASSWORD=%s\n' "$ADMIN_PASSWORD"
} >"$TMP"

mv "$TMP" "$OUT"
trap - EXIT
echo "render-env: เขียน $OUT แล้ว"
