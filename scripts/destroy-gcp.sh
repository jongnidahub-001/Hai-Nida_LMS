#!/bin/bash
# ลบทรัพยากรทั้งหมดที่ scripts/bootstrap-gcp.sh สร้างไว้ใน project
# ใช้: ./scripts/destroy-gcp.sh --project <PROJECT_ID> [--region REGION] [--zone ZONE] [--vm-name NAME] [--dry-run]
#
# ต้องพิมพ์ชื่อ project ยืนยันก่อนลบ และจะถามแยกว่าจะลบ backup (bucket และ snapshot ของ disk) ด้วยหรือไม่
# การลบย้อนกลับไม่ได้ ข้อมูลในระบบ (ChromaDB) จะหายไปพร้อม VM
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --project) need_value "$@"; PROJECT_ID="$2"; shift 2 ;;
    --region) need_value "$@"; REGION="$2"; shift 2 ;;
    --zone) need_value "$@"; ZONE="$2"; shift 2 ;;
    --vm-name) need_value "$@"; VM_NAME="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "ไม่รู้จักตัวเลือก $1" >&2; usage >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT_ID" ] || { usage >&2; exit 2; }
resource_names
command -v gcloud >/dev/null || die "ไม่พบคำสั่ง gcloud"

FAILED=()

# ลบเมื่อมีทรัพยากรอยู่ ถ้าลบไม่สำเร็จจะจดไว้แล้วทำขั้นต่อไป
# ใช้: delete <ชื่อที่แสดง> <อาร์กิวเมนต์ของ describe...> -- <อาร์กิวเมนต์ของ delete...>
delete() {
  local label="$1" describe=() remove=()
  shift
  while [ "$1" != "--" ]; do describe+=("$1"); shift; done
  shift
  remove=("$@")
  if ! exists "${describe[@]}"; then
    info "ไม่มี $label"
    return 0
  fi
  if run gc "${remove[@]}" >/dev/null; then
    [ "$DRY_RUN" = true ] || info "ลบ $label แล้ว"
  else
    info "ลบ $label ไม่สำเร็จ"
    FAILED+=("$label")
  fi
}

ask() {
  local answer
  read -r -p "$1 " answer
  printf '%s' "$answer"
}

# ---------------------------------------------------------------------------
# ยืนยัน
# ---------------------------------------------------------------------------
cat <<EOF
จะลบระบบ Hai-Nida ใน project $PROJECT_ID:
  VM $VM_NAME และ disk (ข้อมูลในระบบจะหายทั้งหมด), static IP $ADDRESS_NAME,
  firewall $FW_WEB และ $FW_SSH, service account $SA_EMAIL,
  secret hai-nida-* ทั้ง 5 ตัว, Gemini API key ที่ bootstrap สร้าง, snapshot schedule $SNAPSHOT_POLICY
EOF

DELETE_BACKUPS=false
if [ "$DRY_RUN" = true ]; then
  echo "โหมด dry-run: แสดงคำสั่งโดยไม่ลบจริง (รวมคำสั่งลบ backup)"
  DELETE_BACKUPS=true
else
  [ -t 0 ] || die "ต้องรันในเทอร์มินัลเพื่อยืนยันการลบ"
  [ "$(ask "พิมพ์ชื่อ project ($PROJECT_ID) เพื่อยืนยัน:")" = "$PROJECT_ID" ] || die "ชื่อ project ไม่ตรง ยกเลิก"
  case "$(ask "ลบ backup ด้วยหรือไม่ (bucket gs://$BACKUP_BUCKET และ snapshot ของ disk) [y/N]:")" in
    y | Y) DELETE_BACKUPS=true ;;
  esac
fi

# หา repo ก่อนลบ VM เพราะอ่านจาก metadata ของ VM
REPO_SLUG=$(vm_repo_slug)

# ---------------------------------------------------------------------------
# ลบ
# ---------------------------------------------------------------------------
step "VM และเครือข่าย"
delete "VM $VM_NAME" compute instances describe "$VM_NAME" --zone "$ZONE" -- \
  compute instances delete "$VM_NAME" --zone "$ZONE" --delete-disks all
delete "snapshot schedule $SNAPSHOT_POLICY" compute resource-policies describe "$SNAPSHOT_POLICY" --region "$REGION" -- \
  compute resource-policies delete "$SNAPSHOT_POLICY" --region "$REGION"
delete "static IP $ADDRESS_NAME" compute addresses describe "$ADDRESS_NAME" --region "$REGION" -- \
  compute addresses delete "$ADDRESS_NAME" --region "$REGION"
delete "firewall $FW_WEB" compute firewall-rules describe "$FW_WEB" -- compute firewall-rules delete "$FW_WEB"
delete "firewall $FW_SSH" compute firewall-rules describe "$FW_SSH" -- compute firewall-rules delete "$FW_SSH"

step "service account"
if exists iam service-accounts describe "$SA_EMAIL"; then
  run gc projects remove-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$SA_EMAIL" \
    --role roles/logging.logWriter --condition None >/dev/null || info "ถอนสิทธิ์ logging.logWriter ไม่สำเร็จ ข้ามไปลบ service account"
fi
delete "service account $SA_NAME" iam service-accounts describe "$SA_EMAIL" -- iam service-accounts delete "$SA_EMAIL"

step "secret และ API key"
for s in "${ALL_SECRETS[@]}"; do
  delete "secret $s" secrets describe "$s" -- secrets delete "$s"
done
key_names=$(gc services api-keys list --filter="displayName=$API_KEY_NAME" --format='value(name)' 2>/dev/null || true)
if [ -z "$key_names" ]; then
  info "ไม่มี API key $API_KEY_NAME"
fi
for k in $key_names; do
  if run gc services api-keys delete "$k" >/dev/null; then
    [ "$DRY_RUN" = true ] || info "ลบ API key $API_KEY_NAME แล้ว"
  else
    FAILED+=("API key $k")
  fi
done

step "backup"
if [ "$DELETE_BACKUPS" = true ]; then
  if exists storage buckets describe "gs://$BACKUP_BUCKET"; then
    if run gc storage rm --recursive "gs://$BACKUP_BUCKET" >/dev/null; then
      [ "$DRY_RUN" = true ] || info "ลบ bucket gs://$BACKUP_BUCKET แล้ว"
    else
      FAILED+=("bucket gs://$BACKUP_BUCKET")
    fi
  else
    info "ไม่มี bucket gs://$BACKUP_BUCKET"
  fi
  snapshots=$(gc compute snapshots list --filter="sourceDisk~/disks/$VM_NAME\$" --format='value(name)' 2>/dev/null || true)
  [ -n "$snapshots" ] || info "ไม่มี snapshot ของ disk $VM_NAME"
  for snap in $snapshots; do
    delete "snapshot $snap" compute snapshots describe "$snap" -- compute snapshots delete "$snap"
  done
else
  info "เก็บ bucket gs://$BACKUP_BUCKET และ snapshot ไว้ (มีค่าใช้จ่ายค่าพื้นที่เก็บ ลบเองได้ภายหลัง)"
fi

step "deploy key บน GitHub"
if [ -n "$REPO_SLUG" ] && gh_is_admin "$REPO_SLUG"; then
  ids=$(gh api "repos/$REPO_SLUG/keys" --jq ".[] | select(.title | startswith(\"$DEPLOY_KEY_TITLE\")) | .id" 2>/dev/null || true)
  [ -n "$ids" ] || info "ไม่มี deploy key ของ project นี้ใน $REPO_SLUG"
  for id in $ids; do
    run gh api -X DELETE "repos/$REPO_SLUG/keys/$id" >/dev/null && { [ "$DRY_RUN" = true ] || info "ลบ deploy key $id แล้ว"; }
  done
else
  info "ให้เจ้าของ repo ลบ deploy key ชื่อ \"$DEPLOY_KEY_TITLE\" ที่ GitHub > ${REPO_SLUG:-repo} > Settings > Deploy keys"
fi

step "สรุป"
if [ "$DRY_RUN" = true ]; then
  info "dry-run: ไม่ได้ลบอะไร"
elif [ ${#FAILED[@]} -eq 0 ]; then
  info "ลบเรียบร้อย"
else
  info "ลบไม่สำเร็จ: ${FAILED[*]}"
  info "ตรวจสาเหตุแล้วรันสคริปต์นี้ใหม่ได้ ทรัพยากรที่ลบแล้วจะถูกข้าม"
  exit 1
fi
