Mongodbbackup specific DB &Collection S3 using Corn Job                
==========================================================================================================================================================================
Prerequisite : ec2 instance 
Type : t3.2xlarge are more 
volume : 100 gb base on usage 
install docker : apt-install docker.io   and docker compose 
install python 
Requirements
AWS CLI configured (aws configure)
Access to MongoDB tools like mongodump and oplog for incremental   Cron installed 
Python Scripts
If you’d rather have Python handle “dump + upload” (perhaps to add more logic later), you can use the AWS SDK (boto3) in concert with a subprocess‐based mongodump. Below are two standalone Python scripts—one for full and one for oplog (incremental). You’ll still call them from cron every 5 minutes.
==========================================================================================================================================================================================================================================================================================================================


===================================================== MONGODB DOCKERFILE FULL INCREMENTAL ========================================================================================================
version: '3.8'                    
 
services:
  mongodb1:
	image: mongo:6.0
	container_name: mongodb1
	restart: always
	ports:
  	- "27017:27017"
	volumes:
  	- mongo_data1:/data/db
  	- mongo_config1:/data/configdb
  	- ./mongo-keyfile:/data/keyfile  # Mount keyfile
	command: ["mongod", "--replSet", "rs0", "--bind_ip", "0.0.0.0", "--keyFile", "/data/keyfile"]
	environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: rootpassword
 
  mongodb2:
	image: mongo:6.0
	container_name: mongodb2
	restart: always
	ports:
  	- "27018:27017"
	volumes:
  	- mongo_data2:/data/db
  	- mongo_config2:/data/configdb
  	- ./mongo-keyfile:/data/keyfile  # Mount keyfile
	command: ["mongod", "--replSet", "rs0", "--bind_ip", "0.0.0.0", "--keyFile", "/data/keyfile"]
	environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: rootpassword
 
  mongodb3:
	image: mongo:6.0
	container_name: mongodb3
	restart: always
	ports:
  	- "27019:27017"
	volumes:
  	- mongo_data3:/data/db
  	- mongo_config3:/data/configdb
  	- ./mongo-keyfile:/data/keyfile  # Mount keyfile
	command: ["mongod", "--replSet", "rs0", "--bind_ip", "0.0.0.0", "--keyFile", "/data/keyfile"]
	environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: rootpassword
 
volumes:
  mongo_data1:
  mongo_config1:
  mongo_data2:
  mongo_config2:
  mongo_data3:
  mongo_config3:

===================================================================STEPS==================================================================================

STEP1 :Login to Mongodb check your db and collection need to backup    

docker exec -it  mongodb1 mongosh -u root -p rootpassword --authenticationDatabase admin

docker exec -it mongodb1 mongosh -u root -p rootpassword --authenticationDatabase admin

Current Mongosh Log ID: 684137de6c6c889b1544a6d
Connecting to: mongodb://<credentials>@127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&authSource=admin&appName=mongosh+2.3.8
Using MongoDB: 6.0.20
Using Mongosh: 2.3.8

For mongosh info see: https://www.mongodb.com/docs/mongodb-shell/

------
The server generated these startup warnings when booting
2025-06-05T09:56:30.361+00:00: Using the XFS filesystem is strongly recommended with the WiredTiger storage engine. See http://dochub.mongodb.org/core/prodnotes-filesystem
2025-06-05T09:56:33.375+00:00: vm.max_map_count is too low
------

---------------------------------------------------------------------------------------------------------------------------------------

Step2:  show dbs → ,use <db> → , check collection ,-->db.resources.find().pretty()
rs0 [direct: primary] test> show dbs
ExcelHire    40.00 KiB
Exel         80.00 KiB
admin        40.00 KiB
cloud_resources  40.00 KiB
config       72.00 KiB
local         2.15 MiB

rs0 [direct: primary] test> use Exel
switched to db Exel

rs0 [direct: primary] Exel> show collections
exel
resources

rs0 [direct: primary] Exel> db.resources.find().pretty()
[
  {
    _id: ObjectId("6814abcbad5e0016ee544cb4"),
    cloud_resource_id: 'vol-0527baaa2e047933a',
    employee_id: '89326023-a406-4c19-a9c6-168fa670ca44',
    region: 'us-east-1',
    resource_type: 'Volume',
    service_name: 'AmazonEC2',
    cost: 1.493333318
  },
  {
    _id: ObjectId("6814abcbad5e0016ee544ca7"),
    cloud_resource_id: 'i-00948dc007b76f956',
    employee_id: '89326023-a406-4c19-a9c6-168fa670ca44',
    region: 'us-east-1',
    resource_type: 'Instance',
    service_name: 'AmazonEC2',
    cost: 52.18452293
  },
  {
    _id: ObjectId("6814abcbad5e0016ee544cb8"),
    cloud_resource_id: 'eni-05869d6074cc68306',
    employee_id: '89326023-a406-4c19-a9c6-168fa670ca44',
    region: 'us-east-1',
    resource_type: 'USE1-PublicIPv4:InUseAddress',
    service_name: 'AmazonVPC',
    cost: 0.97010972
  },
  {
    _id: ObjectId("6814abcbad5e0016ee544cae"),
    cloud_resource_id: 'i-0f3de5edfe09aabcb',
    employee_id: '89326023-a406-4c19-a9c6-168fa670ca44',
    region: 'us-east-1',
    resource_type: 'Instance',
    service_name: 'AmazonEC2',
    cost: 31.02917922
  }
]

================================================================================ MONGODB FULL BACKUP & INCREMENTAL BACKUP PYTHON SCRIPT ======================================================================

mongodb_full_backup.py
#!/usr/bin/env python3
"""
mongodb_full_backup.py
Backs up the 'resources' collection from 'Exel' DB using mongodump, uploads to S3, then deletes local archive.
"""

import os
import subprocess
import boto3
from datetime import datetime

# CONFIG
CONTAINER = "mongodb1"
MONGO_USER = "root"
MONGO_PASS = "rootpassword"
MONGO_AUTH_DB = "admin"
DB_NAME = "Exel"
COLLECTION = "resources"

S3_BUCKET = "backupmongdb"
S3_KEY_PREFIX = "s3mongodbbackautomatic/full"

TMP_DIR = "/tmp/mongodb_backups"
os.makedirs(TMP_DIR, exist_ok=True)


def run_full_dump() -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    outfile = os.path.join(TMP_DIR, f"full_{DB_NAME}_{COLLECTION}_{timestamp}.archive.gz")

    cmd = [
        "docker", "exec", CONTAINER,
        "mongodump",
        "--db", DB_NAME,
        "--collection", COLLECTION,
        "--archive", "--gzip",
        "--username", MONGO_USER,
        "--password", MONGO_PASS,
        "--authenticationDatabase", MONGO_AUTH_DB
    ]

    with open(outfile, "wb") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"mongodump failed: {stderr.decode('utf-8')}")

    return outfile


def upload_to_s3(local_path: str) -> None:
    s3 = boto3.client("s3")
    key = os.path.join(S3_KEY_PREFIX, os.path.basename(local_path))
    print(f"Uploading {local_path} to s3://{S3_BUCKET}/{key} ...")
    s3.upload_file(local_path, S3_BUCKET, key)
    print("Upload complete.")


def main():
    try:
        local_file = run_full_dump()
        upload_to_s3(local_file)
        os.remove(local_file)
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()


============================================================================================== mongodb_incremental_backup.py=====================================
cat mongodb_incremental_backup.py
#!/usr/bin/env python3
"""
mongodb_incremental_backup.py
Backs up the oplog.rs collection (incremental) and uploads to S3.
"""

import os
import subprocess
import boto3
from datetime import datetime

# CONFIG
CONTAINER = "mongodb1"
MONGO_USER = "root"
MONGO_PASS = "rootpassword"
MONGO_AUTH_DB = "admin"

S3_BUCKET = "backupmongdb"
S3_KEY_PREFIX = "s3mongodbbackautomatic/incremental"

TMP_DIR = "/tmp/mongodb_backups"
os.makedirs(TMP_DIR, exist_ok=True)


def run_oplog_dump() -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    outfile = os.path.join(TMP_DIR, f"oplog_{timestamp}.archive.gz")

    cmd = [
        "docker", "exec", CONTAINER,
        "mongodump",
        "--db", "local",
        "--collection", "oplog.rs",
        "--archive", "--gzip",
        "--username", MONGO_USER,
        "--password", MONGO_PASS,
        "--authenticationDatabase", MONGO_AUTH_DB
    ]

    with open(outfile, "wb") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"mongodump (oplog) failed: {stderr.decode('utf-8')}")

    return outfile


def upload_to_s3(local_path: str) -> None:
    s3 = boto3.client("s3")
    key = os.path.join(S3_KEY_PREFIX, os.path.basename(local_path))
    print(f"Uploading {local_path} to s3://{S3_BUCKET}/{key} ...")
    s3.upload_file(local_path, S3_BUCKET, key)
    print("Upload complete.")


def main():
    try:
        local_file = run_oplog_dump()
        upload_to_s3(local_file)
        os.remove(local_file)
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()

=========================================================================
1. Manual Execution
To run the scripts manually from terminal:
# Run Full Backup Manually
python3 /root/corn/mongodb_full_backup.py
# Run Incremental Backup Manually
python3 /root/corn/mongodb_incremental_backup.py
                                       
---------------------------------------------------------- Cron Configuration automation ----------------------------------------------------------

# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
# │ │ │ │ │
# * * * * *  command to execute  
*/5 * * * * /usr/bin/python3 /root/corn/mongodb_full_backup.py >> /var/log/mongo_full.log 2>&1
*/5 * * * * /usr/bin/python3 /root/corn/mongodb_incremental_backup.py >> /var/log/mongo_incr.log 2>&1



sudo crontab -e
Here’s the exact text content from your screenshot (crontab -e file):

# Edit this file to introduce tasks to be run by cron.
#
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
#
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').
#
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
#
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
#
# For example, you can run a backup of all your user accounts
# at 5 a.m. every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
#
# For more information see the manual pages of crontab(5) and cron(8)
#
# m h  dom mon dow   command
0 4 * * * /usr/bin/python3 /root/cron/mongodb_full_backup.py >> /var/log/mongo_full.log 2>&1
0 */5 * * * /usr/bin/python3 /root/cron/mongodb_incremental_backup.py >> /var/log/mongo_incr.log 2>&1


👉 This means:

At 04:00 AM daily → runs mongodb_full_backup.py and logs to /var/log/mongo_full.log

Every 5 hours → runs mongodb_incremental_backup.py and logs to /var/log/mongo_incr.log






 

  
