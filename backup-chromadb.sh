#!/bin/bash
# =============================================================================
# ChromaDB Automated Backup Script
# ใช้สำหรับ backup ข้อมูล ChromaDB จาก Docker named volume
# รองรับ rotation (เก็บ backup ล่าสุด N ชุด)
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

# --- Functions ---
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
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
if ! docker compose -f "$COMPOSE_FILE" ps chromadb 2>/dev/null | grep -q "running"; then
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
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/chromadb_backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$RETAIN_COUNT" ]; then
    log "Rotating backups (keeping latest ${RETAIN_COUNT})..."
    ls -1t "${BACKUP_DIR}"/chromadb_backup_*.tar.gz | tail -n +$((RETAIN_COUNT + 1)) | while read -r old_backup; do
        log "  Removing old backup: $(basename "$old_backup")"
        rm -f "$old_backup"
    done
fi

log "Done. Backups stored in: ${BACKUP_DIR}"
echo "============================================"
