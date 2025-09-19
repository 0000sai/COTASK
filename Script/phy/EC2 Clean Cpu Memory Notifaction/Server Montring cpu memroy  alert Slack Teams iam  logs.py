ubuntu@ip-172-31-32-78:~/test$ cat IAM.py
#!/usr/bin/env python3
"""
Production Cleanup & Monitoring Script with Boto3, Slack, Teams, Approval
Includes IAM User/Role/Account Tracking
"""

import os
import json
import subprocess
import datetime
import getpass
import grp
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
import requests

# Optional: boto3 for AWS details
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

console = Console()

# Log file setup
DEFAULT_LOG = Path("/var/log/prod_cleanup.log")
FALLBACK_LOG = Path.home() / "logs" / "prod_cleanup.log"
LOG_FILE = DEFAULT_LOG if os.access(DEFAULT_LOG.parent, os.W_OK) else FALLBACK_LOG

# Slack and Teams Webhook URLs (replace with actual)
SLACK_WEBHOOK = "https://hooks.slack.com/services/XXX/XXX/XXX"
TEAMS_WEBHOOK = "https://outlook.office.com/webhook/XXX/XXX/XXX"


def show_description():
    console.print("""
[bold green]1. Auto Mode (1)[/bold green]
   - Runs automatically with predefined actions.
   - Kills processes, deletes files, scans disks, logs everything.
   - No prompts for user input.
   - [red]Use with caution:[/red] safe/staging only.

[bold green]2. Interactive Mode (2) [Default][/bold green]
   - Asks for input before critical actions:
     - Which PIDs to kill
     - Which files to delete
     - Folder paths for disk scan
   - Requires [bold red]approval[/bold red] before killing/deleting.
   - [yellow]Safer for production.[/yellow]

[bold magenta] WARNING:[/bold magenta]
- Interactive recommended for production.
- Auto mode acts without confirmation.
[bold cyan]==========================================================[/bold cyan]
""")


def get_iam_identity():
    """
    Get IAM identity (role/user/account) for logging.
    Falls back gracefully if not available.
    """
    identity = {"role": "none", "user": "none", "account": "none"}

    # Try EC2 Metadata for Role
    try:
        role_name = subprocess.check_output(
            ["curl", "-s", "http://169.254.169.254/latest/meta-data/iam/security-credentials/"],
            text=True, timeout=2
        ).strip()
        if role_name and "Unauthorized" not in role_name:
            identity["role"] = role_name
    except Exception:
        pass

    # Try boto3 STS get_caller_identity
    if BOTO3_AVAILABLE:
        try:
            sts = boto3.client("sts")
            caller = sts.get_caller_identity()
            identity["user"] = caller.get("Arn", "none")
            identity["account"] = caller.get("Account", "none")
        except Exception:
            pass

    return identity


def log_event(event, detail):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    linux_user = getpass.getuser()
    sudo_user = os.environ.get("SUDO_USER", linux_user)
    linux_groups = ",".join(grp.getgrgid(g).gr_name for g in os.getgroups())
    euid = os.geteuid()

    iam_identity = get_iam_identity()

    log_data = {
        "ts": ts,
        "linux_user": linux_user,
        "sudo_user": sudo_user,
        "linux_groups": linux_groups,
        "euid": euid,
        "iam_role": iam_identity["role"],
        "iam_user": iam_identity["user"],
        "iam_account": iam_identity["account"],
        "event": event,
        "detail": detail
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(log_data) + "\n")


def notify_slack(message):
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message}, timeout=5)
    except Exception as e:
        console.print(f"[red]Slack notification failed:[/red] {e}")


def notify_teams(message):
    try:
        requests.post(TEAMS_WEBHOOK, json={"text": message}, timeout=5)
    except Exception as e:
        console.print(f"[red]Teams notification failed:[/red] {e}")


def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except subprocess.CalledProcessError:
        return ""


def system_monitor():
    console.print("\n[bold cyan]======= SYSTEM MONITOR =======[/bold cyan]")
    uptime_output = run_cmd("uptime | awk -F'load average:' '{print $2}'").strip()
    console.print(f"[bold yellow]CPU Load:[/bold yellow] {uptime_output}")
    console.print(run_cmd("free -h"))
    console.print(run_cmd("df -h | grep -E '^/dev|Filesystem'"))

    # Show IAM Identity info live
    iam_identity = get_iam_identity()
    console.print(f"[bold green]IAM Role:[/bold green] {iam_identity['role']}")
    console.print(f"[bold green]IAM User:[/bold green] {iam_identity['user']}")
    console.print(f"[bold green]IAM Account:[/bold green] {iam_identity['account']}")

    log_event("monitor", "System stats displayed")


def show_top_processes():
    # CPU
    console.print("\n[bold cyan]======= TOP 20 CPU PROCESSES =======[/bold cyan]")
    cpu_output = run_cmd("ps -eo pid,ppid,comm,%cpu,%mem --sort=-%cpu | head -n 21").splitlines()
    table_cpu = Table(show_header=True, header_style="bold magenta")
    table_cpu.add_column("PID", justify="right")
    table_cpu.add_column("PPID", justify="right")
    table_cpu.add_column("Command", overflow="fold")
    table_cpu.add_column("%CPU", justify="right")
    table_cpu.add_column("%MEM", justify="right")
    for line in cpu_output[1:]:
        parts = line.split(None, 4)
        if len(parts) == 5:
            table_cpu.add_row(*parts)
    console.print(table_cpu)

    # Memory
    console.print("\n[bold cyan]======= TOP 20 MEMORY PROCESSES =======[/bold cyan]")
    mem_output = run_cmd("ps -eo pid,ppid,comm,%cpu,%mem --sort=-%mem | head -n 21").splitlines()
    table_mem = Table(show_header=True, header_style="bold magenta")
    table_mem.add_column("PID", justify="right")
    table_mem.add_column("PPID", justify="right")
    table_mem.add_column("Command", overflow="fold")
    table_mem.add_column("%CPU", justify="right")
    table_mem.add_column("%MEM", justify="right")
    for line in mem_output[1:]:
        parts = line.split(None, 4)
        if len(parts) == 5:
            table_mem.add_row(*parts)
    console.print(table_mem)

    log_event("monitor", "Top CPU and memory processes displayed")
    return cpu_output, mem_output


def approve_action(prompt_text):
    answer = Prompt.ask(f"[bold red]Approval required:[/bold red] {prompt_text} (yes/no)", default="no")
    return answer.lower() == "yes"


def kill_processes(process_list, label):
    pids = Prompt.ask(f"Enter PIDs to kill from {label} list (space separated, blank to skip)", default="")
    if pids and approve_action(f"Do you approve killing these PIDs: {pids}?"):
        for pid in pids.split():
            try:
                os.kill(int(pid), 9)
                console.print(f"[green]✅ Killed process {pid}[/green]")
                log_event("kill", f"Process {pid} killed from {label}")
            except Exception:
                console.print(f"[red]❌ Failed to kill {pid}[/red]")


def list_ebs_volumes():
    console.print("\n[bold cyan]======= EBS VOLUMES (Top 20) =======[/bold cyan]")
    if BOTO3_AVAILABLE:
        try:
            ec2 = boto3.client("ec2")
            response = ec2.describe_volumes()
            volumes = response.get("Volumes", [])[:20]

            if volumes:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("AZ")
                table.add_column("ID")
                table.add_column("Size (GiB)")
                table.add_column("State")
                for v in volumes:
                    az = v.get("AvailabilityZone", "")
                    vol_id = v.get("VolumeId", "")
                    size = str(v.get("Size", ""))
                    state = v.get("State", "")
                    table.add_row(az, vol_id, size, state)
                console.print(table)
            else:
                console.print("[yellow]No volumes found[/yellow]")
            log_event("ebs", "EBS volumes listed")
        except (NoCredentialsError, ClientError):
            console.print("[red]AWS credentials not found or permission denied[/red]")
            log_event("ebs", "AWS credentials not found")
    else:
        console.print("[yellow]Boto3 not installed. Skipping EBS volume listing.[/yellow]")
        log_event("ebs", "Boto3 not installed")


def disk_usage():
    path = Prompt.ask("Enter folder path to scan", default="/")
    console.print(f"\n[bold cyan]======= DISK USAGE ({path}) =======[/bold cyan]")
    usage = run_cmd(f"du -ah {path} 2>/dev/null | sort -rh | head -n 20")
    console.print(usage)
    log_event("disk", f"Top storage usage scanned in path {path}")


def delete_files():
    files = Prompt.ask("Enter full file paths to delete (space separated, blank to skip)", default="")
    if files and approve_action(f"Do you approve deleting these files: {files}?"):
        for f in files.split():
            try:
                os.remove(f)
                console.print(f"[green]✅ Deleted {f}[/green]")
                log_event("delete", f"File {f} deleted")
            except FileNotFoundError:
                console.print(f"[yellow]⚠️ File {f} not found[/yellow]")


def main():
    show_description()
    mode = Prompt.ask("Choose Mode: 1=Auto, 2=Interactive", default="2")

    system_monitor()
    cpu_list, mem_list = show_top_processes()
    list_ebs_volumes()

    if mode == "2":
        kill_processes(cpu_list, "CPU")
        kill_processes(mem_list, "Memory")
        disk_usage()
        delete_files()

    log_event("finish", "Cleanup completed")

    # Send notifications
    notify_message = f"✅ EC2 Cleanup & Monitoring completed successfully on {getpass.getuser()}!"
    notify_slack(notify_message)
    notify_teams(notify_message)

    console.print("\n[bold green]✅ Cleanup Completed! Notifications sent to Slack & Teams[/bold green]")


if __name__ == "__main__":
    main()
================================================================================== output =========================================================================
ubuntu@ip-172-31-32-78:~/test$ ./IAM.py

1. Auto Mode (1)
   - Runs automatically with predefined actions.
   - Kills processes, deletes files, scans disks, logs everything.
   - No prompts for user input.
   - Use with caution: safe/staging only.

2. Interactive Mode (2) [Default]
   - Asks for input before critical actions:
     - Which PIDs to kill
     - Which files to delete
     - Folder paths for disk scan
   - Requires approval before killing/deleting.
   - Safer for production.

 WARNING:
- Interactive recommended for production.
- Auto mode acts without confirmation.
==========================================================

Choose Mode: 1=Auto, 2=Interactive (2): 2

======= SYSTEM MONITOR =======
CPU Load: 0.04, 0.01, 0.00
               total        used        free      shared  buff/cache   available
Mem:           3.8Gi       837Mi       916Mi       1.0Mi       2.1Gi       2.7Gi
Swap:             0B          0B          0B

Filesystem      Size  Used Avail Use% Mounted on
/dev/root        97G  9.3G   88G  10% /
/dev/xvda15     105M  6.1M   99M   6% /boot/efi

IAM Role: none
IAM User: arn:aws:iam::050943451137:user/vishnu
IAM Account: 050943451137

======= TOP 20 CPU PROCESSES =======
┏━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┓
┃  PID ┃ PPID ┃ Command         ┃ %CPU ┃ %MEM ┃
┡━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━┩
│ 4051 │ 1804 │ python3         │  1.1 │  1.3 │
│  380 │    1 │ amazon-cloudwat │  0.6 │  3.0 │
│  786 │    1 │ mysqld          │  0.4 │  9.8 │
│ 1463 │ 1402 │ promtail        │  0.3 │  1.4 │
│ 1470 │ 1401 │ grafana         │  0.2 │  5.9 │
│ 1475 │ 1410 │ loki            │  0.1 │  1.7 │
│    1 │    0 │ systemd         │  0.0 │  0.2 │
│    2 │    0 │ kthreadd        │  0.0 │  0.0 │
│    3 │    2 │ pool_workqueue_ │  0.0 │  0.0 │
│    4 │    2 │ kworker/R-rcu_g │  0.0 │  0.0 │
│    5 │    2 │ kworker/R-rcu_p │  0.0 │  0.0 │
│    6 │    2 │ kworker/R-slub_ │  0.0 │  0.0 │
│    7 │    2 │ kworker/R-netns │  0.0 │  0.0 │
│    8 │    2 │ kworker/0:0-eve │  0.0 │  0.0 │
│    9 │    2 │ kworker/0:0H-kb │  0.0 │  0.0 │
│   12 │    2 │ kworker/R-mm_pe │  0.0 │  0.0 │
│   13 │    2 │ rcu_tasks_rude_ │  0.0 │  0.0 │
│   14 │    2 │ rcu_tasks_trace │  0.0 │  0.0 │
│   15 │    2 │ ksoftirqd/0     │  0.0 │  0.0 │
│   16 │    2 │ rcu_sched       │  0.0 │  0.0 │
└──────┴──────┴─────────────────┴──────┴──────┘

======= TOP 20 MEMORY PROCESSES =======
┏━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┓
┃  PID ┃ PPID ┃ Command         ┃ %CPU ┃ %MEM ┃
┡━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━┩
│  786 │    1 │ mysqld          │  0.4 │  9.8 │
│ 1470 │ 1401 │ grafana         │  0.2 │  5.9 │
│  380 │    1 │ amazon-cloudwat │  0.6 │  3.0 │
│  740 │    1 │ dockerd         │  0.0 │  2.0 │
│ 1475 │ 1410 │ loki            │  0.1 │  1.7 │
│ 1463 │ 1402 │ promtail        │  0.3 │  1.4 │
│ 4051 │ 1804 │ python3         │  1.1 │  1.3 │
│  446 │    1 │ containerd      │  0.0 │  1.2 │
│  425 │    1 │ snapd           │  0.0 │  0.9 │
│  722 │  381 │ ssm-agent-worke │  0.0 │  0.7 │
│  175 │    1 │ multipathd      │  0.0 │  0.6 │
│  134 │    1 │ systemd-journal │  0.0 │  0.6 │
│  530 │    1 │ unattended-upgr │  0.0 │  0.5 │
│ 2999 │    1 │ packagekitd     │  0.0 │  0.5 │
│  381 │    1 │ amazon-ssm-agen │  0.0 │  0.4 │
│  414 │    1 │ networkd-dispat │  0.0 │  0.4 │
│ 1401 │    1 │ containerd-shim │  0.0 │  0.3 │
│ 1402 │    1 │ containerd-shim │  0.0 │  0.3 │
│ 1410 │    1 │ containerd-shim │  0.0 │  0.3 │
│  345 │    1 │ systemd-resolve │  0.0 │  0.3 │
└──────┴──────┴─────────────────┴──────┴──────┘

======= EBS VOLUMES (Top 20) =======
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ AZ         ┃ ID                    ┃ Size (GiB) ┃ State  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ us-east-1c │ vol-0798aa3dc96dbbc80 │ 100        │ in-use │
└────────────┴───────────────────────┴────────────┴────────┘
Enter PIDs to kill from CPU list (space separated, blank to skip) ():
Enter PIDs to kill from Memory list (space separated, blank to skip) ():
Enter folder path to scan (/):

======= DISK USAGE (/) =======
6.4G    /
2.6G    /usr
1.5G    /snap
1.4G    /var
1.1G    /usr/lib
1010M   /var/lib
641M    /usr/bin
618M    /var/lib/snapd
496M    /snap/core22
426M    /opt/aws/amazon-cloudwatch-agent
426M    /opt/aws
426M    /opt
425M    /opt/aws/amazon-cloudwatch-agent/bin
419M    /snap/core20
393M    /home/ubuntu
393M    /home
368M    /usr/share
312M    /var/lib/snapd/snaps
311M    /usr/src
306M    /var/lib/snapd/seed/snaps

Enter full file paths to delete (space separated, blank to skip) ():

Cleanup Completed! Notifications sent to Slack & Teams

==================================================================================LOGS=============================================================================
ubuntu@ip-172-31-32-78:~/logs$ ls -la
total 56
drwxrwxr-x  2 ubuntu ubuntu  4096 Sep 11 13:40 .
drwxr-x--- 20 ubuntu ubuntu  4096 Sep 12 13:46 ..
-rw-rw-r--  1 ubuntu ubuntu 37055 Sep 12 13:59 prod_cleanup.log
-rw-rw-r--  1 ubuntu ubuntu   702 Sep 12 10:42 prod_cleanup_shell.log
u", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/vishnu", "iam_account": "050943451137", "event": "monitor", "detail": "System stats displayed"}
{"ts": "2025-09-12T13:48:45Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "monitor", "detail": "Top CPU and memory processes displayed"}
{"ts": "2025-09-12T13:48:45Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "ebs", "detail": "EBS volumes listed"}
{"ts": "2025-09-12T13:49:07Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "disk", "detail": "Top storage usage scanned in path /"}
{"ts": "2025-09-12T13:49:09Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "finish", "detail": "Cleanup completed"}
{"ts": "2025-09-12T13:58:11Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "monitor", "detail": "System stats displayed"}
{"ts": "2025-09-12T13:58:11Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "monitor", "detail": "Top CPU and memory processes displayed"}
{"ts": "2025-09-12T13:58:12Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "ebs", "detail": "EBS volumes listed"}
{"ts": "2025-09-12T13:59:47Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "disk", "detail": "Top storage usage scanned in path /"}
{"ts": "2025-09-12T13:59:50Z", "linux_user": "ubuntu", "sudo_user": "ubuntu", "linux_groups": "adm,dialout,cdrom,floppy,sudo,audio,dip,video,plugdev,netdev,lxd,docker,ubuntu", "euid": 1000, "iam_role": "none", "iam_user": "arn:aws:iam::050943451137:user/tharunteja", "iam_account": "050943451137", "event": "finish", "detail": "Cleanup completed"}
ubuntu@ip-172-31-32-78:~/logs$ ls
prod_cleanup.log  prod_cleanup_shell.log
ubuntu@ip-172-31-32-78:~/logs$ cat prod_cleanup
cat: prod_cleanup: No such file or directory
ubuntu@ip-172-31-32-78:~/logs$ cat prod_cleanup_shell.log
2025-09-11T13:40:38Z | user:ubuntu | sudo: | event:monitor | detail:System stats displayed
2025-09-11T13:40:38Z | user:ubuntu | sudo: | event:monitor | detail:Top processes displayed
2025-09-11T13:40:50Z | user:ubuntu | sudo: | event:disk | detail:Disk scanned at /
2025-09-11T13:40:59Z | user:ubuntu | sudo: | event:finish | detail:Cleanup completed
2025-09-12T10:42:04Z | user:ubuntu | sudo: | event:monitor | detail:System stats displayed
2025-09-12T10:42:04Z | user:ubuntu | sudo: | event:monitor | detail:Top processes displayed
2025-09-12T10:42:19Z | user:ubuntu | sudo: | event:disk | detail:Disk scanned at /
2025-09-12T10:42:20Z | user:ubuntu | sudo: | event:finish | detail:Cleanup completed


