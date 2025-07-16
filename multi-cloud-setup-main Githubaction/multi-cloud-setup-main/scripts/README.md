# Automation Scripts

This directory contains automation scripts for various maintenance and operational tasks.

## Directory Structure

```
scripts/
├── db-backup.sh       # Database backup automation
└── README.md         # This file
```

## Scripts Overview

### db-backup.sh
Automates database backup process with:
- Scheduled backups
- Compression
- Cloud storage upload
- Retention policy
- Error handling and notifications

## Usage Instructions

### Database Backup

1. Set up environment variables:
```bash
export DB_HOST="your-db-host"
export DB_USER="your-db-user"
export DB_NAME="your-db-name"
export BACKUP_PATH="/path/to/backups"
export AWS_BUCKET="your-backup-bucket"
```
* for this respective task, you only need to set up the POSTGRES_PASSWORD and MYSQL_ROOT_PASSWORD environment variables.

```
export POSTGRES_PASSWORD="<password>"
export MYSQL_ROOT_PASSWORD="<password>"
```

2. Make script executable:
```bash
chmod +x db-backup.sh
```

3. Run manually:
```bash
./db-backup.sh
```

4. Set up cron job for automation:
```bash
# Edit crontab
crontab -e

# Add line for daily backup at 2 AM
0 2 * * * /path/to/db-backup.sh
```