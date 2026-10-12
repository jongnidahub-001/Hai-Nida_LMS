#!/bin/bash
# เปลี่ยนค่า secret ใน Secret Manager แล้วสั่ง VM ใช้ค่าใหม่
# ใช้: ./scripts/rotate-secret.sh <ชื่อ secret> --project <PROJECT_ID> [--zone ZONE] [--vm-name NAME] [--no-apply]
#
# ชื่อ secret (ใส่หรือไม่ใส่ hai-nida- นำหน้าก็ได้)
#   google-api-key    Gemini API key (ถามค่าใหม่แบบไม่แสดงบนจอ)
#   secret-key        key สำหรับเซ็น token สุ่มใหม่ให้ ผู้ใช้ทุกคนต้อง login ใหม่
#   admin-password    ใช้สร้าง admin คนแรกเท่านั้น ไม่เปลี่ยนรหัสของ admin ที่มีอยู่แล้ว
#   app-config        ค่าที่ไม่ลับ เช่น SITE_ADDRESS (เปิดแก้ใน $EDITOR)
#   repo-deploy-key   deploy key ที่ VM ใช้อ่าน repo สร้างคู่ key ใหม่
#
# --no-apply  เปลี่ยนค่าอย่างเดียว ยังไม่สั่ง VM (ค่าใหม่มีผลเมื่อ VM boot ครั้งถัดไป)
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

usage() { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; }

NAME="" APPLY=true
while [ $# -gt 0 ]; do
  case "$1" in
    --project) need_value "$@"; PROJECT_ID="$2"; shift 2 ;;
    --zone) need_value "$@"; ZONE="$2"; shift 2 ;;
    --vm-name) need_value "$@"; VM_NAME="$2"; shift 2 ;;
    --no-apply) APPLY=false; shift ;;
    -h | --help) usage; exit 0 ;;
    -*) echo "ไม่รู้จักตัวเลือก $1" >&2; usage >&2; exit 2 ;;
    *) [ -z "$NAME" ] || { usage >&2; exit 2; }; NAME="${1#hai-nida-}"; shift ;;
  esac
done
[ -n "$NAME" ] || { usage >&2; exit 2; }
[ -n "$PROJECT_ID" ] || die "ต้องระบุ --project (หรือ PROJECT_ID ใน deploy.env)"
resource_names

SECRET="hai-nida-$NAME"
case "$SECRET" in
  "$SECRET_API_KEY" | "$SECRET_SECRET_KEY" | "$SECRET_ADMIN_PASSWORD" | "$SECRET_APP_CONFIG" | "$SECRET_DEPLOY_KEY") ;;
  *) die "ไม่รู้จัก secret $NAME" ;;
esac
exists secrets describe "$SECRET" || die "ไม่พบ secret $SECRET ใน project $PROJECT_ID"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

confirm() {
  local answer
  read -r -p "  $1 [y/N] " answer
  [ "$answer" = y ] || [ "$answer" = Y ]
}

add_version() {
  printf '%s' "$1" | gc secrets versions add "$SECRET" --data-file=- >/dev/null
  info "เพิ่ม version ใหม่ของ $SECRET แล้ว"
}

step "เปลี่ยน $SECRET"
case "$SECRET" in
  "$SECRET_API_KEY")
    info "ถ้า admin เคยตั้ง API key ผ่านหน้า Admin ระบบจะใช้ key นั้นก่อนค่านี้"
    read -r -s -p "  Gemini API key ใหม่: " value
    echo
    [ -n "$value" ] || die "ไม่ได้ใส่ค่า"
    add_version "$value"
    ;;
  "$SECRET_SECRET_KEY")
    info "หลังเปลี่ยน ผู้ใช้ทุกคนจะต้อง login ใหม่"
    confirm "ยืนยันการเปลี่ยน?" || exit 0
    add_version "$(openssl rand -hex 32)"
    ;;
  "$SECRET_ADMIN_PASSWORD")
    info "ค่านี้ใช้สร้าง admin คนแรกเท่านั้น ถ้ามี admin แล้วให้เปลี่ยนรหัสผ่านหน้าเว็บแทน"
    confirm "ยังต้องการเปลี่ยนค่าใน Secret Manager?" || exit 0
    value=$(random_password)
    add_version "$value"
    info "รหัสใหม่: $value"
    ;;
  "$SECRET_APP_CONFIG")
    gc secrets versions access latest --secret "$SECRET" >"$TMP_DIR/app-config.env"
    cp "$TMP_DIR/app-config.env" "$TMP_DIR/before.env"
    "${EDITOR:-vi}" "$TMP_DIR/app-config.env"
    if cmp -s "$TMP_DIR/before.env" "$TMP_DIR/app-config.env"; then
      info "ไม่มีการเปลี่ยนแปลง"
      exit 0
    fi
    add_version "$(cat "$TMP_DIR/app-config.env")"
    ;;
  "$SECRET_DEPLOY_KEY")
    key="$TMP_DIR/deploy_key"
    ssh-keygen -q -t ed25519 -N "" -C "hai-nida-vm@$PROJECT_ID" -f "$key"
    slug=$(vm_repo_slug)
    if [ -n "$slug" ] && gh_is_admin "$slug"; then
      gh repo deploy-key add "$key.pub" --repo "$slug" --title "$DEPLOY_KEY_TITLE $(date +%Y%m%d)" >/dev/null
      info "เพิ่ม deploy key ใหม่ให้ $slug แล้ว"
    else
      cat <<EOF

  ให้เจ้าของ repo เพิ่ม deploy key ใหม่ที่ GitHub > ${slug:-repo} > Settings > Deploy keys
    Key: $(cat "$key.pub")
EOF
      read -r -p "  กด Enter เมื่อเพิ่มแล้ว " _
    fi
    add_version "$(cat "$key")"
    info "หลัง VM ใช้ key ใหม่แล้ว ให้เจ้าของ repo ลบ deploy key อันเก่าออก"
    ;;
esac

if [ "$APPLY" = false ]; then
  info "ยังไม่สั่ง VM ค่าใหม่จะมีผลเมื่อ VM boot ครั้งถัดไป หรือรัน scripts/update-now.sh --force"
  exit 0
fi

# รัน startup script ซ้ำ: เขียน deploy key, สร้าง .env.prod ใหม่ และ build/restart ตามค่าใหม่
step "สั่ง VM ใช้ค่าใหม่"
vm_ssh "sudo google_metadata_script_runner startup"
info "เสร็จแล้ว"
