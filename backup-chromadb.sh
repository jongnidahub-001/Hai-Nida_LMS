#!/bin/bash
# =============================================================================
# ChromaDB Automated Backup Script
# ใช้สำหรับ backup ข้อมูล ChromaDB จาก Docker named volume
# รองรับ rotation (เก็บ backup ล่าสุด N ชุด)
#
# ถ้าตั้ง bucket ไว้ (env BACKUP_BUCKET หรือ metadata backup-bucket ของ VM ที่ bootstrap ตั้งให้)
# จะอัปโหลดไฟล์ขึ้น gs://<bucket>/chromadb/ ด้วย ใช้ --no-upload เพื่อข้ามการอัปโหลด
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups/chromadb"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
VOLUME_NAME="hai-nida_chroma-data"
RETAIN_COUNT=7  # จำนวน backup ที่เก็บไว้ (ลบอันเก่าออก)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="chromadb_backup_${TIMESTAMP}.tar.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"
METADATA="http://metadata.google.internal/computeMetadata/v1"
UPLOAD=true
[ "${1:-}" = "--no-upload" ] && UPLOAD=false

# --- Functions ---
log() {
    local msg
    msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    # Unpause if we paused
    if [ "${PAUSED:-false}" = "true" ]; then
        docker compose -f "$COMPOSE_FILE" unpause chromadb 2>/dev/null || true
    fi
    exit 1
}

# --- Main ---
echo "============================================"
echo "  ChromaDB Backup - $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    error_exit "Docker is not running"
fi

# Check if ChromaDB container is running
# (compose v2 แสดงสถานะเป็น "Up ..." จึงใช้ --status running แทนการ grep คำว่า running)
if [ -z "$(docker compose -f "$COMPOSE_FILE" ps --status running -q chromadb 2>/dev/null)" ]; then
    log "WARNING: ChromaDB container is not running. Backing up volume directly..."
    SKIP_PAUSE=true
else
    SKIP_PAUSE=false
fi

# Check if volume exists
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    error_exit "Volume '$VOLUME_NAME' not found. Is the project deployed?"
fi

# Pause ChromaDB to ensure consistent snapshot
if [ "$SKIP_PAUSE" = "false" ]; then
    log "Pausing ChromaDB container..."
    docker compose -f "$COMPOSE_FILE" pause chromadb
    PAUSED=true
    sleep 2  # Give SQLite time to flush WAL
fi

# Create backup via temporary alpine container
log "Creating backup: $BACKUP_FILE ..."
docker run --rm \
    -v "${VOLUME_NAME}":/data:ro \
    -v "${BACKUP_DIR}":/backup \
    alpine tar czf "/backup/${BACKUP_FILE}" -C /data .

# Unpause ChromaDB
if [ "${PAUSED:-false}" = "true" ]; then
    log "Resuming ChromaDB container..."
    docker compose -f "$COMPOSE_FILE" unpause chromadb
    PAUSED=false
fi

# Verify backup file
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log "Backup complete: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Rotation: keep only the latest N backups
# ชื่อไฟล์มาจากสคริปต์นี้ (ไม่มีช่องว่าง) ใช้ ls เพื่อเรียงตามเวลา
# shellcheck disable=SC2012
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/chromadb_backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$RETAIN_COUNT" ]; then
    log "Rotating backups (keeping latest ${RETAIN_COUNT})..."
    # shellcheck disable=SC2012
    ls -1t "${BACKUP_DIR}"/chromadb_backup_*.tar.gz | tail -n +$((RETAIN_COUNT + 1)) | while read -r old_backup; do
        log "  Removing old backup: $(basename "$old_backup")"
        rm -f "$old_backup"
    done
fi

# Upload to GCS (off-VM copy) using the VM service account token from the metadata server
if [ "$UPLOAD" = true ]; then
    BUCKET="${BACKUP_BUCKET:-$(curl -fsS --max-time 2 -H "Metadata-Flavor: Google" \
        "$METADATA/instance/attributes/backup-bucket" 2>/dev/null || true)}"
    if [ -n "$BUCKET" ]; then
        log "Uploading to gs://${BUCKET}/chromadb/${BACKUP_FILE} ..."
        TOKEN=$(curl -fsS -H "Metadata-Flavor: Google" \
            "$METADATA/instance/service-accounts/default/token" | jq -r '.access_token')
        if printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" |
            curl -fsS -K - -o /dev/null -X POST \
                -H "Content-Type: application/gzip" \
                --data-binary "@${BACKUP_DIR}/${BACKUP_FILE}" \
                "https://storage.googleapis.com/upload/storage/v1/b/${BUCKET}/o?uploadType=media&name=chromadb/${BACKUP_FILE}"; then
            log "Upload complete"
        else
            error_exit "Upload to gs://${BUCKET} failed (local backup kept: ${BACKUP_FILE})"
        fi
    fi
fi

log "Done. Backups stored in: ${BACKUP_DIR}"
echo "============================================"
