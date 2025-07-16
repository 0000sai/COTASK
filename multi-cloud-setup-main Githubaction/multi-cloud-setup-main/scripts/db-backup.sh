#!/bin/bash

# Configuration
BACKUP_DIR="./backup" # Can be custumized to another location
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Check for required environment variables
if [ -z "${POSTGRES_PASSWORD}" ]; then
    echo "Error: POSTGRES_PASSWORD environment variable is not set"
    echo "Please run: export POSTGRES_PASSWORD=your_password"
    exit 1
fi

if [ -z "${MYSQL_ROOT_PASSWORD}" ]; then
    echo "Error: MYSQL_ROOT_PASSWORD environment variable is not set"
    echo "Please run: export MYSQL_ROOT_PASSWORD=your_password"
    exit 1
fi

# Database configurations
declare -A DB_CONFIGS=(
    ["postgres"]="-h localhost -p 5432 -U postgres -d myapp"
    ["mysql"]="--protocol=TCP -h 127.0.0.1 -P 3306 -u root -pmy-secret-pw my_database"
)

# Function to backup PostgreSQL database
backup_postgres() {
    local conn_string=$1
    local backup_file="${BACKUP_DIR}/postgres_${DATE}.sql.gz"
    local base_conn_string=$(echo ${conn_string} | sed 's/-d [^ ]*//')  # Remove database name from connection string
    
    echo "Starting PostgreSQL backup..."
    PGPASSWORD=${POSTGRES_PASSWORD} pg_dump ${conn_string} | gzip > ${backup_file}
    
    if [ $? -eq 0 ]; then
        echo "Backup created successfully: ${backup_file}"
        
        # Test restoration to a temporary database
        local test_db="test_restore_${DATE}"
        echo "Creating test database ${test_db}..."
        PGPASSWORD=${POSTGRES_PASSWORD} createdb ${base_conn_string} ${test_db}
        
        if [ $? -eq 0 ]; then
            echo "Restoring backup to test database..."
            gunzip -c ${backup_file} | PGPASSWORD=${POSTGRES_PASSWORD} psql ${base_conn_string} -d ${test_db}
            
            if [ $? -eq 0 ]; then
                echo "Restoration test successful"
                echo "Cleaning up test database..."
                PGPASSWORD=${POSTGRES_PASSWORD} dropdb ${base_conn_string} ${test_db}
                echo "PostgreSQL backup and restoration test successful"
                return 0
            else
                echo "Restoration to test database failed"
            fi
        else
            echo "Failed to create test database"
        fi
    else
        echo "Backup creation failed"
    fi
    
    echo "PostgreSQL backup verification failed"
    return 1
}

# Function to backup MySQL database
backup_mysql() {
    local conn_string=$1
    local backup_file="${BACKUP_DIR}/mysql_${DATE}.sql.gz"
    local base_conn_string=$(echo ${conn_string} | sed 's/my_database//')  # Remove database name
    
    echo "Starting MySQL backup..."
    # First check if MySQL is accessible
    if ! mysql ${base_conn_string} -e "SELECT 1;" > /dev/null 2>&1; then
        echo "Error: Cannot connect to MySQL. Please check if the server is running and credentials are correct."
        return 1
    fi
    
    echo "Creating backup with mysqldump..."
    mysqldump --single-transaction --routines --triggers --events ${conn_string} | gzip > ${backup_file}
    
    if [ $? -eq 0 ]; then
        echo "Backup created successfully: ${backup_file}"
        
        # Test restoration to a temporary database
        local test_db="test_restore_${DATE}"
        echo "Creating test database ${test_db}..."
        mysql ${base_conn_string} -e "CREATE DATABASE ${test_db}"
        
        if [ $? -eq 0 ]; then
            echo "Restoring backup to test database..."
            gunzip -c ${backup_file} | mysql ${base_conn_string} ${test_db}
            
            if [ $? -eq 0 ]; then
                echo "Restoration test successful"
                echo "Cleaning up test database..."
                mysql ${base_conn_string} -e "DROP DATABASE ${test_db}"
                echo "MySQL backup and restoration test successful"
                return 0
            else
                echo "Restoration to test database failed"
            fi
        else
            echo "Failed to create test database"
        fi
    else
        echo "Backup creation failed"
    fi
    
    echo "MySQL backup verification failed"
    return 1
}

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Perform backups
for db_type in "${!DB_CONFIGS[@]}"; do
    if [ ${db_type} == "postgres" ]; then
        backup_postgres "${DB_CONFIGS[${db_type}]}"
    elif [ ${db_type} == "mysql" ]; then
        backup_mysql "${DB_CONFIGS[${db_type}]}"
    fi
done

# Cleanup old backups
find ${BACKUP_DIR} -type f -mtime +${RETENTION_DAYS} -delete

# Upload to cloud storage
aws s3 sync ${BACKUP_DIR} s3://my-backup-bucket/database-backups/
gsutil -m rsync -r ${BACKUP_DIR} gs://my-backup-bucket/database-backups/
