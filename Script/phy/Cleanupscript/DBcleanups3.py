#!/usr/bin/env python3
"""
Multi-DB Cleanup & Backup Utility (Final Version + S3 Upload)
-------------------------------------------------------------
- Lists top databases by size for MongoDB & MySQL.
- Detects unused DBs/collections/tables for 7,15,30,60,120,240,365 days.
- Prompts user for each deletion: database, collection, table, or record.
- Always offers backup or skip.
- Slack & Teams approval optional: if not set, falls back to console prompt.
- Logs all actions to /var/log/db_cleanup_<timestamp>.log.
- Backups & logs are saved locally + pushed to S3 (buckets/awscostuserreport).

Requires:
    pip install pymongo mysql-connector-python boto3 slack_sdk requests rich
"""

import os, sys, getpass, logging, subprocess, datetime, socket, json, random
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
BACKUP_DIR     = "/backups"
LOG_DIR        = "/home/ubuntu/logs"
DAYS_THRESHOLDS = [7, 15, 30, 60, 120, 240, 365]
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
DRY_RUN        = os.environ.get("DRY_RUN", "false").lower() == "true"
S3_BUCKET      = "buckets"
S3_PREFIX      = "awscostuserreport"

# ✅ Unified MongoDB & MySQL credentials (set once)
MONGO_USER     = os.environ.get("MONGO_USER", "root")
MONGO_PASS     = os.environ.get("MONGO_PASS", "root")
MONGO_URI      = f"mongodb://{MONGO_USER}:{MONGO_PASS}@127.0.0.1:27017/admin"

MYSQL_USER     = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS     = os.environ.get("MYSQL_PASS", "root")
MYSQL_HOST     = "127.0.0.1"
MYSQL_PORT     = 3306
# ------------------------------------------

console = Console()
ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
log_file = Path(LOG_DIR)/f"db_cleanup_{ts}.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def audit(msg):
    console.print(f"[bold cyan]{msg}[/bold cyan]")
    logging.info(msg)

# -------- S3 Upload Helper ----------
def upload_to_s3(local_file, bucket=S3_BUCKET, prefix=S3_PREFIX):
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"{prefix}/{Path(local_file).name}"
        s3.upload_file(str(local_file), bucket, key)
        audit(f"[S3 UPLOAD] {local_file} -> s3://{bucket}/{key}")
    except Exception as e:
        audit(f"[S3 ERROR] Failed to upload {local_file}: {e}")

# -------- Identity & Notification ----------
def get_iam_identity():
    try:
        sts = boto3.client('sts', region_name=AWS_REGION)
        return sts.get_caller_identity()['Arn']
    except Exception:
        return "N/A"

def send_slack(msg):
    if not SLACK_WEBHOOK: return False
    WebhookClient(SLACK_WEBHOOK).send(text=msg)
    return True

def send_teams(msg):
    if not TEAMS_WEBHOOK: return False
    requests.post(TEAMS_WEBHOOK, json={"text": msg})
    return True

def approval_request(message):
    """
    Slack/Teams OTP approval if webhooks configured,
    else fallback to console yes/no prompt.
    """
    if not SLACK_WEBHOOK and not TEAMS_WEBHOOK:
        console.print("Slack/Teams webhooks not set.")
        return console.input(f"{message} -- proceed? (y/n): ").lower() == "y"

    otp = str(random.randint(100000, 999999))
    text = f"{message}\n*One-Time Passcode:* `{otp}`"
    send_slack(text)
    send_teams(text)
    console.print(f"Approval OTP sent to Slack & Teams.")
    user_otp = console.input("Enter OTP from Slack/Teams to continue: ").strip()
    return user_otp == otp

# -------- Database discovery helpers ----------
def mongo_top():
    client = MongoClient(MONGO_URI)
    dbs = client.list_database_names()
    results = []
    for d in dbs:
        stats = client[d].command("dbStats")
        results.append({
            "name": d,
            "dataMB": stats["dataSize"] / 1024 / 1024,
            "storageMB": stats["storageSize"] / 1024 / 1024
        })
    results.sort(key=lambda x: x["dataMB"], reverse=True)
    return results

def mysql_top():
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema,
               ROUND(SUM(data_length+index_length)/1024/1024,2) as sizeMB
        FROM information_schema.tables
        GROUP BY table_schema ORDER BY sizeMB DESC;
    """)
    rows = [{"name": r[0], "sizeMB": float(r[1])} for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def mongo_unused_dbs(days=30):
    client = MongoClient(MONGO_URI)
    dbs = client.list_database_names()
    now = datetime.datetime.utcnow()
    unused = []
    for d in dbs:
        if d in ("admin", "local", "config"):
            continue
        collections = client[d].list_collection_names()
        latest_update = None
        for coll in collections:
            doc = client[d][coll].find_one(
                {"updatedAt": {"$exists": True}},
                sort=[("updatedAt", -1)]
            )
            if doc and "updatedAt" in doc:
                if not latest_update or doc["updatedAt"] > latest_update:
                    latest_update = doc["updatedAt"]
        if not latest_update:
            unused.append({"db": d, "last_used": "Unknown"})
        else:
            delta = (now - latest_update).days
            if delta >= days:
                unused.append({"db": d, "last_used": str(latest_update)})
    return unused

def mysql_unused_dbs(days=30):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema, MAX(update_time)
        FROM information_schema.tables
        WHERE table_schema NOT IN ('mysql','information_schema','performance_schema','sys')
        GROUP BY table_schema;
    """)
    now = datetime.datetime.utcnow()
    unused = []
    for schema, last_update in cur.fetchall():
        if last_update is None:
            unused.append({"db": schema, "last_used": "Never"})
        else:
            delta = (now - last_update).days
            if delta >= days:
                unused.append({"db": schema, "last_used": str(last_update)})
    cur.close(); conn.close()
    return unused

def mongo_unused(days=30):
    client = MongoClient(MONGO_URI)
    dbs = client.list_database_names()
    unused = []
    now = datetime.datetime.utcnow()
    for d in dbs:
        if d in ("admin", "local", "config"):
            continue
        collections = client[d].list_collection_names()
        for coll in collections:
            doc = client[d][coll].find_one(
                {"updatedAt": {"$exists": True}},
                sort=[("updatedAt", -1)]
            )
            if not doc or "updatedAt" not in doc:
                unused.append({"db": d, "coll": coll, "last_used": "Unknown"})
                continue
            delta = (now - doc["updatedAt"]).days
            if delta >= days:
                unused.append({"db": d, "coll": coll, "last_used": str(doc["updatedAt"])})
    return unused

def mysql_unused(days=30):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema, table_name, update_time
        FROM information_schema.tables
        WHERE table_schema NOT IN ('mysql','information_schema','performance_schema','sys')
        ORDER BY update_time;
    """)
    now = datetime.datetime.utcnow()
    unused = []
    for schema, table, update_time in cur.fetchall():
        if update_time is None:
            unused.append({"db": schema, "table": table, "last_used": "Never"})
        else:
            delta = (now - update_time).days
            if delta >= days:
                unused.append({"db": schema, "table": table, "last_used": str(update_time)})
    cur.close(); conn.close()
    return unused

# -------- Backup & Delete Functions ----------
def backup_and_delete_mongo(db, coll):
    if DRY_RUN:
        audit(f"[DRY RUN] Would backup+delete Mongo collection {db}.{coll}")
        return
    bfile = Path(BACKUP_DIR)/f"{db}_{coll}_{ts}.gz"
    subprocess.run(
        ["mongodump", "--db", db, "--collection", coll,
         "--archive", str(bfile), "--gzip"], check=True
    )
    client = MongoClient(MONGO_URI)
    client[db].drop_collection(coll)
    audit(f"[BACKUP] -> {bfile}")
    upload_to_s3(bfile)
    audit(f"[DELETE] Mongo collection {db}.{coll}")

def backup_and_delete_mongo_db(db):
    if DRY_RUN:
        audit(f"[DRY RUN] Would backup+delete Mongo database {db}")
        return
    bfile = Path(BACKUP_DIR)/f"{db}_FULL_{ts}.gz"
    subprocess.run(
        ["mongodump", "--db", db, "--archive", str(bfile), "--gzip"], check=True
    )
    client = MongoClient(MONGO_URI)
    client.drop_database(db)
    audit(f"[BACKUP] -> {bfile}")
    upload_to_s3(bfile)
    audit(f"[DELETE] Mongo database {db}")

def backup_and_delete_mysql(db, table):
    if DRY_RUN:
        audit(f"[DRY RUN] Would backup+delete MySQL table {db}.{table}")
        return
    bfile = Path(BACKUP_DIR)/f"{db}_{table}_{ts}.sql"
    subprocess.run(
        ["mysqldump", "-h", MYSQL_HOST, "-P", str(MYSQL_PORT),
         "-u", MYSQL_USER, f"-p{MYSQL_PASS}", db, table, "-r", str(bfile)],
        check=True
    )
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS, database=db
    )
    cur = conn.cursor()
    cur.execute(f"DROP TABLE `{table}`")
    conn.commit()
    cur.close(); conn.close()
    audit(f"[BACKUP] -> {bfile}")
    upload_to_s3(bfile)
    audit(f"[DELETE] MySQL table {db}.{table}")

def backup_and_delete_mysql_db(db):
    if DRY_RUN:
        audit(f"[DRY RUN] Would backup+delete MySQL database {db}")
        return
    bfile = Path(BACKUP_DIR)/f"{db}_FULL_{ts}.sql"
    subprocess.run(
        ["mysqldump", "-h", MYSQL_HOST, "-P", str(MYSQL_PORT),
         "-u", MYSQL_USER, f"-p{MYSQL_PASS}", "--databases", db, "-r", str(bfile)],
        check=True
    )
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS
    )
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE `{db}`")
    conn.commit()
    cur.close(); conn.close()
    audit(f"[BACKUP] -> {bfile}")
    upload_to_s3(bfile)
    audit(f"[DELETE] MySQL database {db}")

# ------------------- MAIN -------------------
def main():
    console.print("[bold red]⚠️ WARNING: This script can delete production data![/bold red]")
    actor = getpass.getuser()
    iam_arn = get_iam_identity()
    audit(f"Started by Linux user: {actor}, IAM: {iam_arn}, Host: {socket.gethostname()}")

    # Show top DB sizes
    console.rule("[bold green]Top MongoDB Databases")
    for r in mongo_top():
        console.print(f"{r['name']:20} {r['dataMB']:.2f} MB")

    console.rule("[bold green]Top MySQL Databases")
    for r in mysql_top():
        console.print(f"{r['name']:20} {r['sizeMB']:.2f} MB")

    # Show unused DBs
    console.rule("[bold yellow]Unused MongoDB Databases (>=30 days)")
    for r in mongo_unused_dbs(30):
        console.print(f"{r['db']:20} last_used={r['last_used']}")

    console.rule("[bold yellow]Unused MySQL Databases (>=30 days)")
    for r in mysql_unused_dbs(30):
        console.print(f"{r['db']:20} last_used={r['last_used']}")

    # Show unused collections/tables
    console.rule("[bold yellow]Unused MongoDB Collections (>=30 days)")
    for r in mongo_unused(30):
        console.print(f"{r['db']}.{r['coll']:20} last_used={r['last_used']}")

    console.rule("[bold yellow]Unused MySQL Tables (>=30 days)")
    for r in mysql_unused(30):
        console.print(f"{r['db']}.{r['table']:20} last_used={r['last_used']}")

    # Prompt Mongo delete
    console.print("\nEnter Mongo target (db or db.collection) or 'skip':")
    to_del = console.input("> ").strip()
    if to_del.lower() != "skip":
        if "." in to_del:  # collection
            db, coll = to_del.split(".", 1)
            if approval_request(f"Request to delete Mongo collection {db}.{coll}"):
                if console.input("Take backup before delete? (y/n): ").lower() == "y":
                    backup_and_delete_mongo(db, coll)
        else:  # full DB
            db = to_del
            if approval_request(f"Request to delete Mongo database {db}"):
                if console.input("Take backup before delete? (y/n): ").lower() == "y":
                    backup_and_delete_mongo_db(db)

    # Prompt MySQL delete
    console.print("\nEnter MySQL target (db or db.table) or 'skip':")
    to_del = console.input("> ").strip()
    if to_del.lower() != "skip":
        if "." in to_del:  # table
            db, table = to_del.split(".", 1)
            if approval_request(f"Request to delete MySQL table {db}.{table}"):
                if console.input("Take backup before delete? (y/n): ").lower() == "y":
                    backup_and_delete_mysql(db, table)
        else:  # full DB
            db = to_del
            if approval_request(f"Request to delete MySQL database {db}"):
                if console.input("Take backup before delete? (y/n): ").lower() == "y":
                    backup_and_delete_mysql_db(db)

    audit("Done.")
    upload_to_s3(log_file)

if __name__ == "__main__":
    main()
======================================================================OUTPUT=======================================================================================

⚠️ WARNING: This script can delete production data!
Started by Linux user: ubuntu, IAM: arn:aws:iam::050943451137:user/tharunteja, Host: ip-172-31-32-78
────────────────────────────────────────────────────────────────────────── Top MongoDB Databases ───────────────────────────────────────────────────────────────────────────
config               0.01 MB
local                0.01 MB
admin                0.00 MB
─────────────────────────────────────────────────────────────────────────── Top MySQL Databases ────────────────────────────────────────────────────────────────────────────
mysql                2.63 MB
crud_app             0.03 MB
sys                  0.02 MB
information_schema   0.00 MB
performance_schema   0.00 MB
─────────────────────────────────────────────────────────────────── Unused MongoDB Databases (>=30 days) ───────────────────────────────────────────────────────────────────
──────────────────────────────────────────────────────────────────── Unused MySQL Databases (>=30 days) ────────────────────────────────────────────────────────────────────
crud_app             last_used=Never
────────────────────────────────────────────────────────────────── Unused MongoDB Collections (>=30 days) ──────────────────────────────────────────────────────────────────
───────────────────────────────────────────────────────────────────── Unused MySQL Tables (>=30 days) ──────────────────────────────────────────────────────────────────────
crud_app.users                last_used=Never

Enter Mongo target (db or db.collection) or 'skip':
>
Slack/Teams webhooks not set.
Request to delete Mongo database  -- proceed? (y/n):

Enter MySQL target (db or db.table) or 'skip':
>
Slack/Teams webhooks not set.
Request to delete MySQL database  -- proceed? (y/n):
Done.
[S3 UPLOAD] /home/ubuntu/logs/db_cleanup_20250929_151508.log -> s3://awscostuserreport/Backup/db_cleanup_20250929_151508.log
