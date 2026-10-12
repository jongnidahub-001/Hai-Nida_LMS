#!/bin/bash
# ติดตั้ง Hai-Nida บน GCP project ใหม่ด้วยคำสั่งเดียว รันซ้ำได้ ทรัพยากรที่มีอยู่แล้วจะถูกข้าม
#
# ใช้: ./scripts/bootstrap-gcp.sh --project <PROJECT_ID> [ตัวเลือก]
# ตัวเลือกทั้งหมดตั้งในไฟล์ deploy.env ได้ (ดู deploy.env.example) ค่าจาก command line มีผลก่อน
# รันจาก Cloud Shell หรือเครื่องที่มี gcloud, git และ ssh-keygen ใน clone ของ repo นี้
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

usage() {
  cat <<'EOF'
ใช้: ./scripts/bootstrap-gcp.sh --project <PROJECT_ID> [ตัวเลือก]

  --project ID          GCP project (บังคับ)
  --region REGION       default: asia-southeast1
  --zone ZONE           default: asia-southeast1-b
  --vm-name NAME        default: hai-nida
  --machine-type TYPE   default: e2-medium
  --disk-size SIZE      default: 30GB
  --network NAME        default: default
  --domain DOMAIN       ใช้โดเมนและ HTTPS (default: ใช้ IP และ HTTP)
  --gemini-key KEY      Gemini API key (default: สร้าง key ใหม่ใน project)
  --admin-email EMAIL   default: admin@<domain หรือ example.com>
  --repo URL            default: git remote origin ของ clone นี้
  --branch BRANCH       branch ที่ VM ติดตาม (default: release)
  --poll-interval SPAN  ความถี่ที่ VM เช็กโค้ดใหม่ เช่น 5min, 1h (default: 5min)
  --dry-run             พิมพ์คำสั่งที่จะรัน โดยไม่สร้างหรือแก้ทรัพยากร
  -h, --help            แสดงข้อความนี้
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project) need_value "$@"; PROJECT_ID="$2"; shift 2 ;;
    --region) need_value "$@"; REGION="$2"; shift 2 ;;
    --zone) need_value "$@"; ZONE="$2"; shift 2 ;;
    --vm-name) need_value "$@"; VM_NAME="$2"; shift 2 ;;
    --machine-type) need_value "$@"; MACHINE_TYPE="$2"; shift 2 ;;
    --disk-size) need_value "$@"; DISK_SIZE="$2"; shift 2 ;;
    --network) need_value "$@"; NETWORK="$2"; shift 2 ;;
    --domain) need_value "$@"; DOMAIN="$2"; shift 2 ;;
    --gemini-key) need_value "$@"; GEMINI_KEY="$2"; shift 2 ;;
    --admin-email) need_value "$@"; ADMIN_EMAIL="$2"; shift 2 ;;
    --repo) need_value "$@"; REPO_URL="$2"; shift 2 ;;
    --branch) need_value "$@"; BRANCH="$2"; shift 2 ;;
    --poll-interval) need_value "$@"; POLL_INTERVAL="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "ไม่รู้จักตัวเลือก $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$PROJECT_ID" ] || { usage >&2; exit 2; }
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@${DOMAIN:-example.com}}"
ADMIN_USERNAME="admin"
IAP_RANGE="35.235.240.0/20"
resource_names

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# ทำซ้ำสำหรับ IAM ที่เพิ่งสร้าง (มีช่วง propagate สั้นๆ)
retry() {
  local i
  for i in 1 2 3 4 5 6; do
    "$@" && return 0
    [ "$DRY_RUN" = true ] && return 0
    info "ยังไม่สำเร็จ ลองใหม่ใน 10 วินาที ($i/6)"
    sleep 10
  done
  return 1
}

# แปลง https://github.com/owner/repo(.git) เป็น git@github.com:owner/repo.git เพราะ deploy key ใช้กับ SSH เท่านั้น
to_ssh_url() {
  local url="$1"
  if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    echo "git@github.com:${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}.git"
  else
    echo "$url"
  fi
}

# ---------------------------------------------------------------------------
# 1. ตรวจเงื่อนไข
# ---------------------------------------------------------------------------
preflight() {
  step "ตรวจเงื่อนไข"
  local cmd
  for cmd in gcloud git ssh-keygen openssl curl; do
    command -v "$cmd" >/dev/null || die "ไม่พบคำสั่ง $cmd"
  done
  [ -f "$REPO_ROOT/deploy/vm-startup.sh" ] || die "ไม่พบ deploy/vm-startup.sh ต้องรันจาก clone ของ repo นี้"
  [[ "$POLL_INTERVAL" =~ ^[0-9]+(s|min|h)$ ]] || die "--poll-interval ต้องอยู่ในรูปแบบ เช่น 300s, 5min, 1h"

  local account
  account=$(gcloud config get-value account 2>/dev/null || true)
  [ -n "$account" ] || die "ยังไม่ได้ login gcloud ให้รัน: gcloud auth login"
  info "บัญชี: $account"

  gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null 2>&1 ||
    die "ไม่พบ project $PROJECT_ID หรือไม่มีสิทธิ์เข้าถึง"

  local billing
  billing=$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || true)
  case "$billing" in
    True) info "billing: เปิดแล้ว" ;;
    False) die "project $PROJECT_ID ยังไม่ได้ผูก billing account" ;;
    *) info "billing: ตรวจไม่ได้ (ข้ามการตรวจ ถ้ายังไม่ได้ผูก billing ขั้นเปิด API จะล้มเหลว)" ;;
  esac

  check_permissions

  if [ -z "$REPO_URL" ]; then
    REPO_URL=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null) || die "หา URL ของ repo ไม่ได้ ให้ระบุ --repo"
  fi
  REPO_URL=$(to_ssh_url "$REPO_URL")
  info "repo: $REPO_URL (branch $BRANCH)"
}

check_permissions() {
  local perms=(
    compute.instances.create compute.addresses.create compute.firewalls.create
    compute.resourcePolicies.create iam.serviceAccounts.create storage.buckets.create
    resourcemanager.projects.setIamPolicy serviceusage.services.enable
    secretmanager.secrets.create secretmanager.secrets.setIamPolicy
  )
  [ -n "$GEMINI_KEY" ] || perms+=(apikeys.keys.create)

  local body response granted missing=() p
  body=$(printf '"%s",' "${perms[@]}")
  body="{\"permissions\":[${body%,}]}"
  # ส่ง token ผ่าน stdin ไม่ให้ไปอยู่ใน argument ของ process
  response=$(printf 'header = "Authorization: Bearer %s"\n' "$(gcloud auth print-access-token)" |
    curl -fsS -K - -H "Content-Type: application/json" -X POST -d "$body" \
      "https://cloudresourcemanager.googleapis.com/v1/projects/$PROJECT_ID:testIamPermissions" 2>/dev/null) || {
    info "ตรวจสิทธิ์ไม่ได้ ข้ามการตรวจ"
    return 0
  }
  granted=$(tr -d ' \n' <<<"$response")
  for p in "${perms[@]}"; do
    [[ "$granted" == *"\"$p\""* ]] || missing+=("$p")
  done
  if [ ${#missing[@]} -gt 0 ]; then
    die "สิทธิ์ไม่พอ ขาด: ${missing[*]}
ต้องมีบทบาท Owner หรือ Editor + Security Admin + Secret Manager Admin ใน project $PROJECT_ID"
  fi
  info "สิทธิ์: ครบ"
}

# ---------------------------------------------------------------------------
# 2. เปิด API
# ---------------------------------------------------------------------------
enable_apis() {
  step "เปิด API"
  run gc services enable compute.googleapis.com secretmanager.googleapis.com \
    apikeys.googleapis.com generativelanguage.googleapis.com iap.googleapis.com storage.googleapis.com
}

# ---------------------------------------------------------------------------
# 3. static IP และ firewall
# ---------------------------------------------------------------------------
setup_network() {
  step "static IP และ firewall"
  exists compute networks describe "$NETWORK" || [ "$DRY_RUN" = true ] ||
    die "ไม่พบ VPC network $NETWORK ให้ระบุ --network"

  if exists compute addresses describe "$ADDRESS_NAME" --region "$REGION"; then
    info "มี static IP $ADDRESS_NAME แล้ว"
  else
    run gc compute addresses create "$ADDRESS_NAME" --region "$REGION"
  fi
  if [ "$DRY_RUN" = true ] && ! exists compute addresses describe "$ADDRESS_NAME" --region "$REGION"; then
    VM_IP="<static-ip>"
  else
    VM_IP=$(gc compute addresses describe "$ADDRESS_NAME" --region "$REGION" --format='value(address)')
  fi
  info "IP: $VM_IP"

  if exists compute firewall-rules describe "$FW_WEB"; then
    info "มี firewall $FW_WEB แล้ว"
  else
    run gc compute firewall-rules create "$FW_WEB" --network "$NETWORK" --direction INGRESS \
      --allow tcp:80,tcp:443 --source-ranges 0.0.0.0/0 --target-tags "$VM_NAME"
  fi
  # SSH เปิดเฉพาะช่วง IP ของ IAP ใช้ผ่าน gcloud compute ssh --tunnel-through-iap
  if exists compute firewall-rules describe "$FW_SSH"; then
    info "มี firewall $FW_SSH แล้ว"
  else
    run gc compute firewall-rules create "$FW_SSH" --network "$NETWORK" --direction INGRESS \
      --allow tcp:22 --source-ranges "$IAP_RANGE" --target-tags "$VM_NAME"
  fi
}

# ---------------------------------------------------------------------------
# 4. secret
# ---------------------------------------------------------------------------
secret_exists() { exists secrets describe "$1"; }

create_secret() {
  local name="$1" value="$2"
  [ "$DRY_RUN" = true ] || [ -n "$value" ] || die "ค่าของ $name ว่าง ไม่สร้าง secret"
  run_with_stdin "$value" gc secrets create "$name" --replication-policy automatic --data-file=-
}

gemini_key() {
  if [ -n "$GEMINI_KEY" ]; then
    printf '%s' "$GEMINI_KEY"
    return
  fi
  local key_name
  key_name=$(gc services api-keys list --filter="displayName=$API_KEY_NAME" --format='value(name)' 2>/dev/null | head -n1)
  if [ -z "$key_name" ]; then
    run gc services api-keys create --display-name "$API_KEY_NAME" \
      --api-target service=generativelanguage.googleapis.com >/dev/null
    [ "$DRY_RUN" = true ] && return
    key_name=$(gc services api-keys list --filter="displayName=$API_KEY_NAME" --format='value(name)' | head -n1)
  fi
  gc services api-keys get-key-string "$key_name" --format='value(keyString)'
}

app_config() {
  printf 'ADMIN_EMAIL=%s\nADMIN_USERNAME=%s\nCORS_ORIGINS=\n' "$ADMIN_EMAIL" "$ADMIN_USERNAME"
  [ -z "$DOMAIN" ] || printf 'SITE_ADDRESS=%s\n' "$DOMAIN"
}

setup_secrets() {
  step "Secret Manager"
  ADMIN_PASSWORD_CREATED=""

  if secret_exists "$SECRET_API_KEY"; then
    info "มี $SECRET_API_KEY แล้ว"
    [ -z "$GEMINI_KEY" ] || info "ไม่เขียนทับ key เดิม ถ้าต้องการเปลี่ยนให้ใช้ scripts/rotate-secret.sh"
  else
    [ -n "$GEMINI_KEY" ] || info "สร้าง Gemini API key ($API_KEY_NAME) จำกัดเฉพาะ generativelanguage.googleapis.com"
    local api_key
    api_key=$(gemini_key) || die "สร้างหรืออ่าน Gemini API key ไม่สำเร็จ"
    create_secret "$SECRET_API_KEY" "$api_key"
  fi

  if secret_exists "$SECRET_SECRET_KEY"; then
    info "มี $SECRET_SECRET_KEY แล้ว"
  else
    create_secret "$SECRET_SECRET_KEY" "$(openssl rand -hex 32)"
  fi

  if secret_exists "$SECRET_ADMIN_PASSWORD"; then
    info "มี $SECRET_ADMIN_PASSWORD แล้ว"
  else
    ADMIN_PASSWORD_CREATED=$(random_password)
    create_secret "$SECRET_ADMIN_PASSWORD" "$ADMIN_PASSWORD_CREATED"
  fi

  if secret_exists "$SECRET_APP_CONFIG"; then
    info "มี $SECRET_APP_CONFIG แล้ว"
    local current
    current=$(gc secrets versions access latest --secret "$SECRET_APP_CONFIG" 2>/dev/null || true)
    if [ "$current" != "$(app_config)" ]; then
      info "ค่าใน $SECRET_APP_CONFIG ต่างจากตัวเลือกที่ส่งมา ระบบยังใช้ค่าเดิม"
      info "ถ้าต้องการเปลี่ยน (เช่น เพิ่มโดเมน) ให้ใช้ scripts/rotate-secret.sh $SECRET_APP_CONFIG"
    fi
  else
    create_secret "$SECRET_APP_CONFIG" "$(app_config)"
  fi
}

# ---------------------------------------------------------------------------
# 5. deploy key สำหรับให้ VM อ่าน repo
# ---------------------------------------------------------------------------
repo_reachable() {
  local key="$1"
  GIT_SSH_COMMAND="ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$TMP_DIR/known_hosts" \
    git ls-remote --heads "$REPO_URL" "$BRANCH" 2>/dev/null | grep -q "refs/heads/$BRANCH$"
}

setup_deploy_key() {
  step "deploy key ของ repo"
  local key="$TMP_DIR/deploy_key"

  if secret_exists "$SECRET_DEPLOY_KEY"; then
    info "มี $SECRET_DEPLOY_KEY แล้ว"
    if [ "$DRY_RUN" = true ]; then
      return
    fi
    gc secrets versions access latest --secret "$SECRET_DEPLOY_KEY" >"$key"
    chmod 600 "$key"
    ssh-keygen -y -f "$key" >"$key.pub"
  else
    if [ "$DRY_RUN" = true ]; then
      run ssh-keygen -t ed25519 -N "" -C "hai-nida-vm@$PROJECT_ID" -f "<tmp>/deploy_key"
      run gc secrets create "$SECRET_DEPLOY_KEY" --replication-policy automatic --data-file "<tmp>/deploy_key"
      info "[dry-run] เพิ่ม public key เป็น deploy key แบบ read-only ของ $REPO_URL"
      return
    fi
    ssh-keygen -q -t ed25519 -N "" -C "hai-nida-vm@$PROJECT_ID" -f "$key"
    gc secrets create "$SECRET_DEPLOY_KEY" --replication-policy automatic --data-file "$key" >/dev/null
    info "สร้าง $SECRET_DEPLOY_KEY แล้ว"
  fi

  if repo_reachable "$key"; then
    info "deploy key อ่าน repo และ branch $BRANCH ได้"
    return
  fi

  # เพิ่ม deploy key เองได้ถ้าผู้รันเป็น admin ของ repo
  local slug
  slug=$(github_slug "$REPO_URL" || true)
  if [ -n "$slug" ] && gh_is_admin "$slug"; then
    info "เพิ่ม deploy key ให้ $slug ด้วย gh"
    gh repo deploy-key add "$key.pub" --repo "$slug" --title "$DEPLOY_KEY_TITLE" >/dev/null
  else
    cat <<EOF

  ต้องให้เจ้าของ repo เพิ่ม deploy key นี้ก่อน VM จึงจะดึงโค้ดได้
  ที่ GitHub > ${slug:-repo} > Settings > Deploy keys > Add deploy key
    Title: $DEPLOY_KEY_TITLE
    Key:   $(cat "$key.pub")
    ไม่ต้องเลือก Allow write access

EOF
  fi

  local i
  for i in $(seq 1 60); do
    repo_reachable "$key" && { info "deploy key อ่าน repo และ branch $BRANCH ได้"; return; }
    if [ "$i" -eq 1 ] && [ -t 0 ]; then
      read -r -p "  กด Enter เมื่อเพิ่ม deploy key แล้ว (หรือ Ctrl+C เพื่อหยุดแล้วรันใหม่ภายหลัง) " _
    else
      sleep 10
    fi
  done
  die "ยังอ่าน $REPO_URL branch $BRANCH ด้วย deploy key ไม่ได้
ตรวจว่าเพิ่ม deploy key แล้ว และมี branch $BRANCH ใน repo จากนั้นรันสคริปต์นี้ใหม่"
}

# ---------------------------------------------------------------------------
# 6. service account ของ VM
# ---------------------------------------------------------------------------
setup_service_account() {
  step "service account $SA_NAME"
  if exists iam service-accounts describe "$SA_EMAIL"; then
    info "มี $SA_EMAIL แล้ว"
  else
    run gc iam service-accounts create "$SA_NAME" --display-name "Hai-Nida VM"
  fi

  local s
  for s in "${ALL_SECRETS[@]}"; do
    retry run gc secrets add-iam-policy-binding "$s" \
      --member "serviceAccount:$SA_EMAIL" --role roles/secretmanager.secretAccessor >/dev/null ||
      die "ให้สิทธิ์อ่าน $s ไม่สำเร็จ"
  done
  retry run gc projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:$SA_EMAIL" --role roles/logging.logWriter --condition None >/dev/null ||
    die "ให้สิทธิ์ logging.logWriter ไม่สำเร็จ"
  info "ให้สิทธิ์อ่านเฉพาะ secret ของระบบ และเขียน log"
}

# ---------------------------------------------------------------------------
# 7. VM
# ---------------------------------------------------------------------------
setup_vm() {
  step "VM $VM_NAME"
  local metadata="repo-url=$REPO_URL,repo-branch=$BRANCH,poll-interval=$POLL_INTERVAL,backup-bucket=$BACKUP_BUCKET"
  local startup="startup-script=$REPO_ROOT/deploy/vm-startup.sh"

  if exists compute instances describe "$VM_NAME" --zone "$ZONE"; then
    info "มี VM แล้ว อัปเดต metadata (startup script ใหม่มีผลเมื่อ reboot)"
    run gc compute instances add-metadata "$VM_NAME" --zone "$ZONE" \
      --metadata "$metadata" --metadata-from-file "$startup"
  else
    run gc compute instances create "$VM_NAME" --zone "$ZONE" \
      --machine-type "$MACHINE_TYPE" \
      --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
      --boot-disk-size "$DISK_SIZE" --boot-disk-type pd-balanced \
      --network "$NETWORK" --address "$VM_IP" --tags "$VM_NAME" \
      --service-account "$SA_EMAIL" --scopes cloud-platform \
      --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
      --metadata "$metadata" --metadata-from-file "$startup"
  fi
}

# ---------------------------------------------------------------------------
# 8. snapshot รายวันของ boot disk
# ---------------------------------------------------------------------------
setup_snapshots() {
  step "snapshot รายวัน"
  if exists compute resource-policies describe "$SNAPSHOT_POLICY" --region "$REGION"; then
    info "มี $SNAPSHOT_POLICY แล้ว"
  else
    # 19:00 UTC = 02:00 เวลาไทย
    run gc compute resource-policies create snapshot-schedule "$SNAPSHOT_POLICY" --region "$REGION" \
      --daily-schedule --start-time 19:00 --max-retention-days 7 \
      --on-source-disk-delete keep-auto-snapshots
  fi

  local attached=""
  attached=$(gc compute disks describe "$VM_NAME" --zone "$ZONE" --format='value(resourcePolicies)' 2>/dev/null || true)
  if [[ "$attached" == *"/$SNAPSHOT_POLICY"* ]]; then
    info "ผูกกับ disk $VM_NAME แล้ว"
  else
    run gc compute disks add-resource-policies "$VM_NAME" --zone "$ZONE" --resource-policies "$SNAPSHOT_POLICY"
  fi
}

# ---------------------------------------------------------------------------
# 9. bucket สำหรับ backup ChromaDB นอก VM
# ---------------------------------------------------------------------------
setup_backup_bucket() {
  step "bucket backup gs://$BACKUP_BUCKET"
  if exists storage buckets describe "gs://$BACKUP_BUCKET"; then
    info "มี bucket แล้ว"
  else
    run gc storage buckets create "gs://$BACKUP_BUCKET" --location "$REGION" \
      --uniform-bucket-level-access --public-access-prevention
  fi

  # ลบไฟล์ backup ที่เก่ากว่า 30 วันอัตโนมัติ
  local lifecycle="$TMP_DIR/lifecycle.json"
  echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}' >"$lifecycle"
  run gc storage buckets update "gs://$BACKUP_BUCKET" --lifecycle-file "$lifecycle" >/dev/null

  # VM สร้างไฟล์ได้อย่างเดียว ลบหรือเขียนทับ backup เดิมไม่ได้
  retry run gc storage buckets add-iam-policy-binding "gs://$BACKUP_BUCKET" \
    --member "serviceAccount:$SA_EMAIL" --role roles/storage.objectCreator >/dev/null ||
    die "ให้สิทธิ์เขียน bucket ไม่สำเร็จ"
  info "เก็บไฟล์ 30 วัน VM เพิ่มไฟล์ได้อย่างเดียว"
}

# ---------------------------------------------------------------------------
# 10. รอระบบพร้อม
# ---------------------------------------------------------------------------
wait_ready() {
  step "รอระบบพร้อม (สูงสุด 20 นาที)"
  if [ "$DRY_RUN" = true ]; then
    info "[dry-run] รอ startup script พิมพ์ 'hai-nida: ready' และ http://$VM_IP/ ตอบ 200"
    return
  fi

  local deadline=$((SECONDS + 1200)) serial state last=""
  while [ $SECONDS -lt $deadline ]; do
    serial=$(gc compute instances get-serial-port-output "$VM_NAME" --zone "$ZONE" 2>/dev/null |
      grep -a 'startup-script' || true)
    # เช็กเว็บจริงก่อน marker ใน serial log เพราะ timer อาจอัปเดตสำเร็จหลัง startup script รายงาน failed
    # และ serial log อาจมีผลจากการ boot ครั้งก่อน
    if site_up; then
      info "ระบบพร้อมแล้ว"
      return
    fi
    state=$(grep -aoE 'hai-nida: (ready|failed)' <<<"$serial" | tail -n 1 || true)
    if [ "$state" = "hai-nida: failed" ]; then
      tail -n 30 <<<"$serial"
      die "ติดตั้งบน VM ไม่สำเร็จ ดู log ด้านบน แก้แล้วรันสคริปต์นี้ใหม่หรือ reboot VM"
    fi
    # เมื่อใช้โดเมนแต่ยังไม่ได้ชี้ DNS จะเช็กเว็บไม่ได้ ใช้ marker ของ startup script แทน
    if [ "$state" = "hai-nida: ready" ] && [ -n "$DOMAIN" ]; then
      info "ระบบบน VM พร้อมแล้ว (เว็บจะเปิดได้หลังชี้ DNS)"
      return
    fi
    local now
    now=$(grep -a 'hai-nida:' <<<"$serial" | tail -n 1 || true)
    if [ -n "$now" ] && [ "$now" != "$last" ]; then
      info "${now##*hai-nida: }"
      last="$now"
    fi
    sleep 20
  done
  die "รอเกิน 20 นาที ดู log ด้วย: gcloud compute instances get-serial-port-output $VM_NAME --zone $ZONE --project $PROJECT_ID"
}

# ไม่ใช้โดเมน: เช็กผ่าน IP ตรงๆ, ใช้โดเมน: เช็ก HTTPS โดยบังคับให้โดเมนชี้มาที่ IP นี้
# (สำเร็จเมื่อชี้ DNS แล้วและ Caddy ออกใบรับรองได้)
site_up() {
  if [ -z "$DOMAIN" ]; then
    curl -fsS -o /dev/null --max-time 10 "http://$VM_IP/" &&
      curl -fsS -o /dev/null --max-time 10 "http://$VM_IP/openapi.json"
  else
    curl -fsS -o /dev/null --max-time 10 --resolve "$DOMAIN:443:$VM_IP" "https://$DOMAIN/openapi.json"
  fi
}

# ---------------------------------------------------------------------------
# 11. สรุป
# ---------------------------------------------------------------------------
summary() {
  local email="$ADMIN_EMAIL" url="http://$VM_IP"
  if [ "$DRY_RUN" = false ] && [ -z "$ADMIN_PASSWORD_CREATED" ]; then
    email=$(gc secrets versions access latest --secret "$SECRET_APP_CONFIG" 2>/dev/null |
      sed -n 's/^ADMIN_EMAIL=//p' || true)
    email="${email:-$ADMIN_EMAIL}"
  fi
  [ -z "$DOMAIN" ] || url="https://$DOMAIN"

  step "เสร็จแล้ว"
  cat <<EOF
  URL:          $url
  Admin email:  $email
EOF
  if [ "$DRY_RUN" = true ]; then
    echo "  Admin password: (สุ่มใหม่และแสดงที่นี่ ถ้ายังไม่มี secret $SECRET_ADMIN_PASSWORD)"
  elif [ -n "$ADMIN_PASSWORD_CREATED" ]; then
    echo "  Admin password: $ADMIN_PASSWORD_CREATED"
    echo "  (แสดงครั้งเดียว ให้เปลี่ยนรหัสหลัง login ครั้งแรก)"
  else
    echo "  Admin password: ใช้รหัสเดิม"
  fi
  [ -z "$DOMAIN" ] || echo "
  ให้ชี้ DNS record A ของ $DOMAIN มาที่ $VM_IP แล้ว Caddy จะออกใบรับรอง HTTPS ให้เอง"
  cat <<EOF

  VM ดึงโค้ดใหม่จาก branch $BRANCH ทุก $POLL_INTERVAL

  ดู log การอัปเดต:
    gcloud compute ssh $VM_NAME --zone $ZONE --project $PROJECT_ID --tunnel-through-iap \\
      --command 'journalctl -u hai-nida-update -n 100 --no-pager'
EOF
}

main() {
  [ "$DRY_RUN" = false ] || echo "โหมด dry-run: ไม่สร้างหรือแก้ทรัพยากรใดๆ"
  preflight
  enable_apis
  setup_network
  setup_secrets
  setup_deploy_key
  setup_service_account
  setup_backup_bucket
  setup_vm
  setup_snapshots
  wait_ready
  summary
}

main
