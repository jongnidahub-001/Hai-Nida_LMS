#!/bin/bash
# สั่ง VM ดึงโค้ดล่าสุดและอัปเดตทันที ไม่ต้องรอ timer
# ใช้: ./scripts/update-now.sh --project <PROJECT_ID> [--zone ZONE] [--vm-name NAME] [--force]
#   --force  build ใหม่และอ่าน secret ใหม่แม้ไม่มี commit ใหม่
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

FORCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) need_value "$@"; PROJECT_ID="$2"; shift 2 ;;
    --zone) need_value "$@"; ZONE="$2"; shift 2 ;;
    --vm-name) need_value "$@"; VM_NAME="$2"; shift 2 ;;
    --force) FORCE=" --force"; shift ;;
    -h | --help) sed -n '2,4p' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "ไม่รู้จักตัวเลือก $1" >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT_ID" ] || die "ต้องระบุ --project (หรือ PROJECT_ID ใน deploy.env)"

vm_ssh "sudo -u deploy /opt/hai-nida/scripts/vm-update.sh$FORCE"
