#!/bin/bash
# =============================================================================
# Setup Automated ChromaDB Backup Cron Job
# ติดตั้ง cron job สำหรับ backup ChromaDB อัตโนมัติบน VM
# Default: ทุกวัน เวลา 03:00 น.
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_SCRIPT="${PROJECT_DIR}/backup-chromadb.sh"
CRON_SCHEDULE="${1:-0 3 * * *}"  # Default: daily at 03:00
CRON_LOG="${PROJECT_DIR}/backups/chromadb/cron.log"
CRON_MARKER="# hai-nida-chromadb-backup"

# --- Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# --- Main ---
echo "============================================"
echo "  Setup ChromaDB Backup Cron Job"
echo "============================================"
echo ""

# Check backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    error_exit "Backup script not found: $BACKUP_SCRIPT"
fi

# Ensure backup script is executable
chmod +x "$BACKUP_SCRIPT"
log "✅ Backup script is executable"

# Create log directory
mkdir -p "$(dirname "$CRON_LOG")"

# Build cron entry
CRON_ENTRY="${CRON_SCHEDULE} ${BACKUP_SCRIPT} >> ${CRON_LOG} 2>&1 ${CRON_MARKER}"

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRON" | grep -q "$CRON_MARKER"; then
    log "Updating existing cron job..."
    # Remove old entry and add new one
    NEW_CRON=$(echo "$EXISTING_CRON" | grep -v "$CRON_MARKER")
    echo "${NEW_CRON}
${CRON_ENTRY}" | crontab -
else
    log "Installing new cron job..."
    # Append to existing crontab
    (echo "$EXISTING_CRON"; echo "$CRON_ENTRY") | crontab -
fi

log "✅ Cron job installed successfully!"
echo ""
echo "  Schedule:  ${CRON_SCHEDULE}"
echo "  Script:    ${BACKUP_SCRIPT}"
echo "  Log:       ${CRON_LOG}"
echo ""

# Show current crontab for verification
echo "Current crontab:"
echo "-------------------------------------------"
crontab -l | grep -A0 "$CRON_MARKER" || true
echo "-------------------------------------------"
echo ""
echo "Useful commands:"
echo "  View logs:      tail -f ${CRON_LOG}"
echo "  Test backup:    ${BACKUP_SCRIPT}"
echo "  Remove cron:    crontab -l | grep -v '${CRON_MARKER}' | crontab -"
echo "  Edit schedule:  $0 '0 */6 * * *'  (every 6 hours)"
echo ""
echo "Common schedules:"
echo "  '0 3 * * *'      - Daily at 03:00 (default)"
echo "  '0 */6 * * *'    - Every 6 hours"
echo "  '0 3 * * 0'      - Weekly on Sunday at 03:00"
echo "  '0 3,15 * * *'   - Twice daily at 03:00 and 15:00"
echo ""
echo "============================================"
