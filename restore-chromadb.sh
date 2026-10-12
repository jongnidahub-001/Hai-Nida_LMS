#!/bin/bash
# =============================================================================
# ChromaDB Restore Script
# ใช้สำหรับ restore ข้อมูล ChromaDB จาก backup file กลับเข้า Docker volume
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups/chromadb"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
VOLUME_NAME="hai-nida_chroma-data"

# --- Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

list_backups() {
    echo ""
    echo "Available backups:"
    echo "-------------------------------------------"
    local i=1 f size name
    # ชื่อไฟล์มาจาก backup-chromadb.sh (ไม่มีช่องว่าง) ใช้ ls เพื่อเรียงตามเวลา
    # shellcheck disable=SC2012
    ls -1t "${BACKUP_DIR}"/chromadb_backup_*.tar.gz 2>/dev/null | while read -r f; do
        size=$(du -sh "$f" | cut -f1)
        name=$(basename "$f")
        echo "  [$i] $name ($size)"
        i=$((i + 1))
    done
    echo "-------------------------------------------"
}

# --- Main ---
echo "============================================"
echo "  ChromaDB Restore - $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    error_exit "Docker is not running"
fi

# Determine which backup to restore
BACKUP_FILE=""

if [ $# -ge 1 ]; then
    # Argument provided: use it as backup file path
    if [ -f "$1" ]; then
        BACKUP_FILE="$1"
    elif [ -f "${BACKUP_DIR}/$1" ]; then
        BACKUP_FILE="${BACKUP_DIR}/$1"
    else
        error_exit "Backup file not found: $1"
    fi
else
    # No argument: show interactive menu
    if ! ls "${BACKUP_DIR}"/chromadb_backup_*.tar.gz >/dev/null 2>&1; then
        error_exit "No backups found in ${BACKUP_DIR}"
    fi

    list_backups

    echo ""
    read -rp "Enter backup number to restore (or 'q' to quit): " choice

    if [ "$choice" = "q" ]; then
        echo "Cancelled."
        exit 0
    fi

    # Validate input
    if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
        error_exit "Invalid input: $choice"
    fi

    # shellcheck disable=SC2012
    BACKUP_FILE=$(ls -1t "${BACKUP_DIR}"/chromadb_backup_*.tar.gz | sed -n "${choice}p")

    if [ -z "$BACKUP_FILE" ]; then
        error_exit "Invalid selection: $choice"
    fi
fi

log "Selected backup: $(basename "$BACKUP_FILE")"
echo ""

# Confirm restore (destructive operation)
echo "⚠️  WARNING: This will OVERWRITE all current ChromaDB data!"
echo "   Volume: ${VOLUME_NAME}"
echo "   Backup: $(basename "$BACKUP_FILE")"
echo ""
read -rp "Are you sure you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

# Stop ChromaDB container
log "Stopping ChromaDB container..."
docker compose -f "$COMPOSE_FILE" stop chromadb

# Clear existing volume data and restore
log "Restoring data from backup..."
docker run --rm \
    -v "${VOLUME_NAME}":/data \
    -v "$(dirname "$BACKUP_FILE")":/backup:ro \
    alpine sh -c "rm -rf /data/* /data/..?* /data/.[!.]* 2>/dev/null; tar xzf /backup/$(basename "$BACKUP_FILE") -C /data"

# Restart ChromaDB
log "Starting ChromaDB container..."
docker compose -f "$COMPOSE_FILE" up -d chromadb

# Wait for ChromaDB to be ready
log "Waiting for ChromaDB to be ready..."
for i in $(seq 1 30); do
    # image ของ chroma ไม่มี wget/curl จึงเช็กจาก container backend (API v1 ถูกยกเลิกใน chroma 1.x)
    if docker compose -f "$COMPOSE_FILE" exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://chromadb:8000/api/v2/heartbeat', timeout=3)" 2>/dev/null; then
        log "✅ ChromaDB is healthy and ready!"
        echo ""
        echo "============================================"
        echo "  Restore complete!"
        echo "============================================"
        exit 0
    fi
    sleep 2
done

log "⚠️  ChromaDB started but health check timed out. Check logs with:"
echo "   docker compose -f $COMPOSE_FILE logs chromadb"
