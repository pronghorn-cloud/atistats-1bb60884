#!/bin/bash
# AI-Academy 3 ATI Stats - Database Backup Script
# Usage: ./backup.sh [backup_name]

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${1:-ati_stats_backup_${DATE}}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}ATI Stats - Database Backup${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Perform backup
echo -e "${YELLOW}📦 Starting backup...${NC}"
echo "   Database: ${PGDATABASE}"
echo "   Host: ${PGHOST}"
echo "   Output: ${BACKUP_FILE}"
echo ""

pg_dump -h "${PGHOST}" -U "${PGUSER}" -d "${PGDATABASE}" \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    | gzip > "${BACKUP_FILE}"

# Verify backup
if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(ls -lh "${BACKUP_FILE}" | awk '{print $5}')
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
    echo "   File: ${BACKUP_FILE}"
    echo "   Size: ${BACKUP_SIZE}"
else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Clean up old backups
echo ""
echo -e "${YELLOW}🧹 Cleaning up old backups (older than ${RETENTION_DAYS} days)...${NC}"
find "${BACKUP_DIR}" -name "ati_stats_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# List recent backups
echo ""
echo -e "${GREEN}📋 Recent backups:${NC}"
ls -lht "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -10 || echo "   No backups found"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Backup process complete!${NC}"
echo -e "${GREEN}======================================${NC}"
