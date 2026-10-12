#!/bin/bash
# อัปเดตระบบบน VM จาก branch ที่ตั้งไว้ใน metadata repo-branch (default: release)
# systemd timer hai-nida-update.timer เรียกสคริปต์นี้ทุก poll-interval ในนาม user deploy
# ใช้: scripts/vm-update.sh [--force]
#   --force  render .env.prod และ build ใหม่แม้ commit ไม่เปลี่ยน (ใช้ตอน boot และหลังเปลี่ยน secret)
#
# ถ้า health check ไม่ผ่านจะกลับไป commit เดิม และจะไม่ลอง commit ที่ล้มเหลวซ้ำจนกว่าจะมี commit ใหม่
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${HAI_NIDA_STATE_DIR:-/var/lib/hai-nida}"
METADATA="http://metadata.google.internal/computeMetadata/v1"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

branch() {
  local b
  b=$(curl -fsS -H "Metadata-Flavor: Google" "$METADATA/instance/attributes/repo-branch" 2>/dev/null) || b=""
  echo "${b:-release}"
}

compose() {
  docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" "$@"
}

# ตรวจที่ตัว container โดยตรง ไม่ผ่าน Caddy เพราะเมื่อตั้ง SITE_ADDRESS เป็นโดเมน
# Caddy จะไม่ตอบ localhost และใบรับรองอาจยังไม่พร้อมถ้ายังไม่ได้ชี้ DNS
# ใช้ 127.0.0.1 ไม่ใช้ localhost เพราะ localhost ใน container resolve เป็น ::1 ก่อน แต่ nginx ฟังแค่ IPv4
health_check() {
  local _
  for _ in $(seq 1 36); do
    if compose exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/openapi.json', timeout=5)" \
        >/dev/null 2>&1 &&
      compose exec -T frontend wget -q -O /dev/null http://127.0.0.1/ >/dev/null 2>&1 &&
      [ -n "$(compose ps --status running -q caddy)" ]; then
      return 0
    fi
    sleep 5
  done
  return 1
}

# build และ start ตาม source ปัจจุบัน แล้ว restart caddy ถ้า Caddyfile เปลี่ยนจาก from_rev
# ถูกเรียกใน if ซึ่ง set -e ไม่มีผล จึงต้องเช็กผลทีละขั้น
start_stack() {
  local from_rev="$1"
  "$PROJECT_DIR/scripts/render-env.sh" || return 1
  compose up -d --build --remove-orphans || return 1
  # Caddyfile เป็น bind mount แบบไฟล์เดียว ต้อง restart ถึงจะเห็นไฟล์ใหม่
  if [ "$from_rev" != "$(git rev-parse HEAD)" ] &&
    git diff --name-only "$from_rev" HEAD | grep -qx Caddyfile; then
    log "Caddyfile เปลี่ยน restart caddy"
    compose restart caddy || return 1
  fi
}

main() {
  local force=false
  [ "${1:-}" = "--force" ] && force=true

  mkdir -p "$STATE_DIR"
  exec 9>"$STATE_DIR/update.lock"
  flock -w 1800 9 || { log "รอ lock เกิน 30 นาที ข้ามรอบนี้"; exit 1; }

  cd "$PROJECT_DIR"
  local br old_rev new_rev failed_rev=""

  # รอบที่สอง: ถูก exec มาจากสคริปต์ฉบับเดิมหลัง git reset แล้ว ทำต่อจาก build
  if [ -n "${HAI_NIDA_PREV_REV:-}" ]; then
    old_rev="$HAI_NIDA_PREV_REV"
    new_rev=$(git rev-parse HEAD)
    unset HAI_NIDA_PREV_REV
    deploy "$old_rev" "$new_rev"
  fi

  br=$(branch)
  git fetch --quiet --prune origin "+refs/heads/$br:refs/remotes/origin/$br"
  old_rev=$(git rev-parse HEAD)
  new_rev=$(git rev-parse "origin/$br")
  [ -f "$STATE_DIR/failed-rev" ] && failed_rev=$(cat "$STATE_DIR/failed-rev")

  if [ "$force" = false ]; then
    [ "$old_rev" = "$new_rev" ] && exit 0
    if [ "$new_rev" = "$failed_rev" ]; then
      log "ข้าม $new_rev เพราะเคยล้มเหลวแล้ว รอ commit ใหม่ใน $br"
      exit 0
    fi
  fi

  log "อัปเดต $br: $old_rev -> $new_rev"

  if [ -n "$(compose ps --status running -q chromadb 2>/dev/null)" ]; then
    log "backup ChromaDB"
    "$PROJECT_DIR/backup-chromadb.sh" || log "WARNING: backup ไม่สำเร็จ อัปเดตต่อ"
  fi

  git reset --quiet --hard "$new_rev"

  # รันต่อด้วยสคริปต์ฉบับใหม่ การแก้สคริปต์นี้จะได้มีผลตั้งแต่รอบที่อัปเดต
  HAI_NIDA_PREV_REV="$old_rev" exec "$PROJECT_DIR/scripts/vm-update.sh"
}

# build, health check และกลับไป old_rev ถ้าไม่ผ่าน (source อยู่ที่ new_rev แล้ว)
deploy() {
  local old_rev="$1" new_rev="$2"
  if start_stack "$old_rev" && health_check; then
    rm -f "$STATE_DIR/failed-rev"
    log "อัปเดตสำเร็จ $(git log -1 --format='%h %s')"
    docker image prune -f >/dev/null
    docker builder prune -f --filter "until=168h" >/dev/null
    exit 0
  fi

  log "ERROR: อัปเดตเป็น $new_rev ไม่สำเร็จ"
  compose ps || true
  compose logs --tail=50 backend || true
  echo "$new_rev" >"$STATE_DIR/failed-rev"

  if [ "$old_rev" != "$new_rev" ]; then
    log "กลับไปใช้ $old_rev"
    git reset --quiet --hard "$old_rev"
    if start_stack "$new_rev" && health_check; then
      log "กลับไปเวอร์ชันเดิมสำเร็จ"
    else
      log "ERROR: กลับไปเวอร์ชันเดิมแล้วระบบยังไม่ผ่าน health check"
    fi
  fi
  exit 1
}

# เรียกผ่าน main เพื่อให้ bash อ่านสคริปต์ครบก่อน git reset จะเปลี่ยนไฟล์นี้ระหว่างรัน
main "$@"
