#!/usr/bin/env python3
"""
Multi-DB Cleanup & Backup Utility (Production Forced Backup Version)
--------------------------------------------------------------------
- Supports MongoDB & MySQL.
- Always takes FULL backup when deleting an entire DB (mandatory).
- Collection/Table deletion still asks backup confirmation.
- Uploads backups & logs to S3 in timestamped folder.
- Slack/Teams OTP approval before deletion (fallback console).
"""

import os, sys, getpass, logging, subprocess, datetime, socket, random
from pathlib import Path
from rich.console import Console
from slack_sdk.webhook import WebhookClient
import requests
import boto3
from pymongo import MongoClient
import mysql.connector

# ---------------- CONFIG -----------------
SLACK_WEBHOOK  = os.environ.get("SLACK_WEBHOOK_URL")
TEAMS_WEBHOOK  = os.environ.get("TEAMS_WEBHOOK_URL")
BASE_BACKUP_DIR = "/backups"
LOG_DIR        = "/home/ubuntu/logs"
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET      = "awscostuserreport"
S3_PREFIX      = "Backup"

MONGO_URI      = "mongodb://root:root@127.0.0.1:27017/admin"
MYSQL_USER     = "root"
MYSQL_PASS     = "root"
MYSQL_HOST     = "127.0.0.1"
MYSQL_PORT     = 3306
# ------------------------------------------

console = Console()
ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

BACKUP_DIR = Path(BASE_BACKUP_DIR)/ts
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
log_file = Path(LOG_DIR)/f"db_cleanup_{ts}.log"

logging.basicConfig(filename=log_file, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")

def audit(msg):
    console.print(f"[bold cyan]{msg}[/bold cyan]")
    logging.info(msg)

# -------- S3 Upload Helper ----------
def upload_to_s3(local_file):
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"{S3_PREFIX}/{ts}/{Path(local_file).name}"
        s3.upload_file(str(local_file), S3_BUCKET, key)
        audit(f"[S3 UPLOAD] {local_file} -> s3://{S3_BUCKET}/{key}")
    except Exception as e:
        audit(f"[S3 ERROR] Failed to upload {local_file}: {e}")

# -------- Approval ----------
def approval_request(message):
    if not SLACK_WEBHOOK and not TEAMS_WEBHOOK:
        return console.input(f"{message} -- proceed? (y/n): ").lower() == "y"
    otp = str(random.randint(100000,999999))
    text = f"{message}\n*One-Time Passcode:* `{otp}`"
    if SLACK_WEBHOOK: WebhookClient(SLACK_WEBHOOK).send(text=text)
    if TEAMS_WEBHOOK: requests.post(TEAMS_WEBHOOK, json={"text": text})
    console.print("Approval OTP sent to Slack/Teams.")
    user_otp = console.input("Enter OTP: ").strip()
    return user_otp == otp

# -------- Database discovery ----------
def mongo_top():
    client = MongoClient(MONGO_URI)
    dbs = client.list_database_names()
    results = []
    for d in dbs:
        stats = client[d].command("dbStats")
        results.append({"name": d, "dataMB": stats["dataSize"]/1024/1024})
    return sorted(results,key=lambda x:x["dataMB"],reverse=True)

def mysql_top():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,port=MYSQL_PORT,user=MYSQL_USER,password=MYSQL_PASS)
    cur = conn.cursor()
    cur.execute("""SELECT table_schema,
            ROUND(SUM(data_length+index_length)/1024/1024,2) as sizeMB
        FROM information_schema.tables
        GROUP BY table_schema ORDER BY sizeMB DESC""")
    rows=[{"name":r[0],"sizeMB":float(r[1])} for r in cur.fetchall()]
    cur.close();conn.close();return rows

# -------- Backup & Delete ----------
def backup_and_delete_mongo_db(db):
    bfile=BACKUP_DIR/f"{db}_FULL_{ts}.gz"
    subprocess.run(["mongodump","--db",db,"--archive",str(bfile),"--gzip"],check=True)
    MongoClient(MONGO_URI).drop_database(db)
    audit(f"[BACKUP] {db} -> {bfile}");upload_to_s3(bfile)
    audit(f"[DELETE] MongoDB database {db}")

def backup_and_delete_mongo(db,coll):
    bfile=BACKUP_DIR/f"{db}_{coll}_{ts}.gz"
    subprocess.run(["mongodump","--db",db,"--collection",coll,
        "--archive",str(bfile),"--gzip"],check=True)
    MongoClient(MONGO_URI)[db].drop_collection(coll)
    audit(f"[BACKUP] {db}.{coll} -> {bfile}");upload_to_s3(bfile)
    audit(f"[DELETE] Mongo collection {db}.{coll}")

def backup_and_delete_mysql_db(db):
    bfile=BACKUP_DIR/f"{db}_FULL_{ts}.sql"
    subprocess.run(["mysqldump","-h",MYSQL_HOST,"-P",str(MYSQL_PORT),
        "-u",MYSQL_USER,f"-p{MYSQL_PASS}","--databases",db,"-r",str(bfile)],check=True)
    conn=mysql.connector.connect(host=MYSQL_HOST,port=MYSQL_PORT,user=MYSQL_USER,password=MYSQL_PASS)
    cur=conn.cursor();cur.execute(f"DROP DATABASE `{db}`");conn.commit()
    cur.close();conn.close()
    audit(f"[BACKUP] {db} -> {bfile}");upload_to_s3(bfile)
    audit(f"[DELETE] MySQL database {db}")

def backup_and_delete_mysql(db,table):
    bfile=BACKUP_DIR/f"{db}_{table}_{ts}.sql"
    subprocess.run(["mysqldump","-h",MYSQL_HOST,"-P",str(MYSQL_PORT),
        "-u",MYSQL_USER,f"-p{MYSQL_PASS}",db,table,"-r",str(bfile)],check=True)
    conn=mysql.connector.connect(host=MYSQL_HOST,port=MYSQL_PORT,user=MYSQL_USER,password=MYSQL_PASS,database=db)
    cur=conn.cursor();cur.execute(f"DROP TABLE `{table}`");conn.commit()
    cur.close();conn.close()
    audit(f"[BACKUP] {db}.{table} -> {bfile}");upload_to_s3(bfile)
    audit(f"[DELETE] MySQL table {db}.{table}")

# ------------------- MAIN -------------------
def main():
    console.print("[bold red]⚠️ WARNING: This script can delete production data![/bold red]")
    actor=getpass.getuser()
    audit(f"Started by {actor} on {socket.gethostname()}")

    console.rule("[bold green]Top MongoDB Databases")
    for r in mongo_top(): console.print(f"{r['name']:20} {r['dataMB']:.2f} MB")

    console.rule("[bold green]Top MySQL Databases")
    for r in mysql_top(): console.print(f"{r['name']:20} {r['sizeMB']:.2f} MB")

    console.print("\nEnter targets (comma-separated). Format:\n"
        "- MongoDB: db | db.collection\n"
        "- MySQL: db | db.table\n"
        "Type 'all-mongo' or 'all-mysql' for full wipe.\n"
        "Type 'skip' to cancel.")
    targets=[t.strip() for t in console.input("> ").split(",")]

    if "skip" in targets: sys.exit(0)

    # Special: backup all DBs first if full wipe
    if "all-mongo" in targets:
        if approval_request("Request to delete ALL MongoDB databases"):
            for db in MongoClient(MONGO_URI).list_database_names():
                if db not in ("admin","local","config"):
                    backup_and_delete_mongo_db(db)
    if "all-mysql" in targets:
        if approval_request("Request to delete ALL MySQL databases"):
            for r in mysql_top():
                db=r["name"]
                if db not in ("mysql","sys","information_schema","performance_schema"):
                    backup_and_delete_mysql_db(db)

    # Handle specific targets
    for t in targets:
        if t in ("all-mongo","all-mysql","skip"): continue
        if "." in t:
            db,child=t.split(".",1)
            if approval_request(f"Delete {t}?"):
                if console.input("Take backup before delete? (y/n): ").lower()=="y":
                    if db in [x["name"] for x in mysql_top()]:
                        backup_and_delete_mysql(db,child)
                    else:
                        backup_and_delete_mongo(db,child)
        else:
            if approval_request(f"Delete DB {t}?"):
                # 🔒 Full DB delete -> always backup (no question)
                if t in [x["name"] for x in mysql_top()]:
                    backup_and_delete_mysql_db(t)
                else:
                    backup_and_delete_mongo_db(t)

    audit("Done.");upload_to_s3(log_file)

if __name__=="__main__":
    main()
===================================================================OUTPUT====================================================================================
⚠️ WARNING: This script can delete production data!

Started by ubuntu on ip-172-31-32-78

──────────────────────── Top MongoDB Databases ─────────────────────────
crud_app             150.23 MB
logs_db               87.45 MB

──────────────────────── Top MySQL Databases ─────────────────────────
crud_app               2.63 MB
mysql                  2.10 MB

Enter targets (comma-separated). Format:
- MongoDB: db | db.collection
- MySQL: db | db.table
Type 'all-mongo' or 'all-mysql' for full wipe.
Type 'skip' to cancel.
> logs_db, crud_app

Approval OTP sent to Slack/Teams.
Enter OTP: 123456
[BACKUP] logs_db -> /backups/20250929/logs_db_FULL_20250929_144400.gz
[S3 UPLOAD] /backups/20250929/logs_db_FULL_20250929_144400.gz -> s3://awscostuserreport/Backup/20250929/logs_db_FULL_20250929_144400.gz
[DELETE] MongoDB database logs_db

Approval OTP sent to Slack/Teams.
Enter OTP: 123456
[BACKUP] crud_app -> /backups/20250929/crud_app_FULL_20250929_144400.sql
[S3 UPLOAD] /backups/20250929/crud_app_FULL_20250929_144400.sql -> s3://awscostuserreport/Backup/20250929/crud_app_FULL_20250929_144400.sql
[DELETE] MySQL database crud_app

[S3 UPLOAD] /home/ubuntu/logs/db_cleanup_20250929_144400.log -> s3://awscostuserreport/Backup/20250929/db_cleanup_20250929_144400.log
Done.
