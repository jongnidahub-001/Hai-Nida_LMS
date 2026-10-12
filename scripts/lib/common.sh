#!/bin/bash
# ค่าตั้งต้น ชื่อทรัพยากร และ helper ที่ใช้ร่วมกันใน scripts/*-gcp.sh, rotate-secret.sh และ update-now.sh
# ใช้ด้วย: . "$(dirname "$0")/lib/common.sh"

# ให้ error ใน $(...) หยุดสคริปต์ด้วย (bash 4.4 ขึ้นไป บน bash ของ macOS จะข้าม)
shopt -s inherit_errexit 2>/dev/null || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ค่าตั้งต้น ถูกแทนด้วย deploy.env แล้วตามด้วย command line ของแต่ละสคริปต์
# shellcheck disable=SC2034
{
  PROJECT_ID="" REGION="asia-southeast1" ZONE="asia-southeast1-b" VM_NAME="hai-nida"
  MACHINE_TYPE="e2-medium" DISK_SIZE="30GB" NETWORK="default" DOMAIN="" GEMINI_KEY=""
  ADMIN_EMAIL="" REPO_URL="" BRANCH="release" POLL_INTERVAL="5min" DRY_RUN=false
}

if [ -f "$REPO_ROOT/deploy.env" ]; then
  # shellcheck disable=SC1091
  . "$REPO_ROOT/deploy.env"
fi

# ชื่อทรัพยากร เรียกหลังอ่าน command line แล้ว เพราะขึ้นกับ PROJECT_ID และ VM_NAME
# shellcheck disable=SC2034
resource_names() {
  SA_NAME="hai-nida-vm"
  SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
  ADDRESS_NAME="$VM_NAME-ip"
  FW_WEB="$VM_NAME-allow-web"
  FW_SSH="$VM_NAME-allow-iap-ssh"
  SNAPSHOT_POLICY="$VM_NAME-daily-snapshot"
  BACKUP_BUCKET="$PROJECT_ID-hai-nida-backups"
  API_KEY_NAME="hai-nida-gemini"
  SECRET_API_KEY="hai-nida-google-api-key"
  SECRET_SECRET_KEY="hai-nida-secret-key"
  SECRET_ADMIN_PASSWORD="hai-nida-admin-password"
  SECRET_APP_CONFIG="hai-nida-app-config"
  SECRET_DEPLOY_KEY="hai-nida-repo-deploy-key"
  ALL_SECRETS=("$SECRET_API_KEY" "$SECRET_SECRET_KEY" "$SECRET_ADMIN_PASSWORD" "$SECRET_APP_CONFIG" "$SECRET_DEPLOY_KEY")
  DEPLOY_KEY_TITLE="hai-nida-vm ($PROJECT_ID)"
}

need_value() {
  [ $# -ge 2 ] && [ -n "$2" ] || { echo "ตัวเลือก $1 ต้องมีค่า" >&2; exit 2; }
}

step() { printf '\n== %s ==\n' "$*"; }
info() { printf '  %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

gc() { gcloud --project "$PROJECT_ID" --quiet "$@"; }

exists() { gc "$@" >/dev/null 2>&1; }

# คำสั่งสำหรับแสดงใน dry-run แปลง gc เป็นคำสั่ง gcloud เต็ม
show_cmd() {
  [ "$1" = gc ] && { shift; set -- gcloud --project "$PROJECT_ID" "$@"; }
  printf ' %q' "$@"
  printf '\n'
}

# รันคำสั่งที่สร้าง แก้ หรือลบทรัพยากร ใน dry-run จะพิมพ์คำสั่งแทน (ออก stderr จะได้ไม่ปนกับค่าที่ capture)
run() {
  if [ "$DRY_RUN" = true ]; then
    {
      printf '  [dry-run]'
      show_cmd "$@"
    } >&2
  else
    "$@"
  fi
}

# เหมือน run แต่ส่งค่าลับทาง stdin ของคำสั่ง ใน dry-run จะไม่พิมพ์ค่า
run_with_stdin() {
  local value="$1"
  shift
  if [ "$DRY_RUN" = true ]; then
    {
      printf '  [dry-run] <ค่าลับ> |'
      show_cmd "$@"
    } >&2
  else
    printf '%s' "$value" | "$@"
  fi
}

random_password() { openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-20; }

github_slug() {
  [[ "$1" =~ github\.com[:/]([^/]+)/([^/]+)$ ]] && echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
}

# true ถ้ามี gh ที่ login แล้วและเป็น admin ของ repo
gh_is_admin() {
  command -v gh >/dev/null && [ "$(gh api "repos/$1" --jq '.permissions.admin' 2>/dev/null)" = "true" ]
}

# repo ที่ VM ใช้ อ่านจาก metadata ของ VM ถ้ามี ไม่งั้นใช้ git remote ของ clone นี้
vm_repo_slug() {
  local url
  url=$(gc compute instances describe "$VM_NAME" --zone "$ZONE" \
    --format='value(metadata.items.repo-url)' 2>/dev/null || true)
  [ -n "$url" ] || url=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
  github_slug "$url" || true
}

# รันคำสั่งบน VM ผ่าน IAP (ไม่ต้องเปิด port 22 สู่ภายนอก)
vm_ssh() {
  gcloud compute ssh "$VM_NAME" --project "$PROJECT_ID" --zone "$ZONE" --tunnel-through-iap --command "$1"
}
