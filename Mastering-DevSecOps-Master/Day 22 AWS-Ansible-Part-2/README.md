![an-eye-catching-image-with-the-glossy-text-ansible-29br2wpbTleCfuUILMcoiA-q17GtADBT7CWaIP5UT9zHQ](https://github.com/user-attachments/assets/a9d0ef13-a6c4-4b52-8666-f177ff397e69)




# Ansible Redis & Vault Setup
#Complete Repo Here: https://github.com/saikiranpi/Ansible-Testing.git

This repository contains Ansible playbooks to configure Redis caching for storing Ansible facts and demonstrates how to use Ansible Vault to securely manage sensitive information. This is a step-by-step guide to setting up Redis as a fast storage for Ansible facts, managing configurations with handlers, and using Ansible Vault to secure sensitive data.

## Prerequisites

- Ansible installed on the controller node
- Python3 and Redis installed on the target servers
- Proper SSH access and configured inventory file (`invfile`)

---

### Step 1: Initial Setup and Verification

1. **Remove Old Playbooks:** Delete any previous playbook versions.
2. **Copy New Playbook:** Paste the latest playbook to the Ansible playbooks location.
3. **Test Connections:** Run a basic ping test to ensure connectivity:
   ```bash
   ansible -i invfile pvt -m ping
   ansible -i invfile pub -m ping
   ```

### Step 2: Collecting Facts with Redis Caching

**Collect Ansible Facts:** Use the following command to gather facts on `tstserver01`:
   ```bash
   ansible -i invfile tstserver01 -m setup
   ```
   
To reduce memory usage, configure Redis as an external caching server for storing these facts.

#### Redis Configuration

1. **Playbooks and Configuration Files:**
   - `redis.config`: Specifies the IP address to bind (use public IP if necessary).
   - `redis.service`: Ensures Redis service starts.
   - `redis.yml`: Runs the Redis setup.

2. **Run Playbook on Controller:**
   ```bash
   ansible-playbook -i invfile playbooks/2/redis.yaml --syntax-check -v
   ```

3. **Verify Installation on Test Server:**
   ```bash
   systemctl status redis
   ```

#### Handlers

Handlers ensure the Redis service restarts only when necessary (if there are changes in `redis.config` or `redis.service`).

### Step 3: Fetch and Store Files

Once Redis is configured:
1. **Backup File Creation:** Backups are created and saved under `/tmp` on the server.
2. **Download Backup File:** Use Ansible to fetch backup files from the test server to your local machine.

```bash
ansible -i invfile all -m setup
```

### Step 4: Secure Sensitive Information with Ansible Vault

Ansible Vault is used to manage sensitive data like AWS credentials securely.

1. **Create Vault File:**
   ```bash
   ansible-vault create aws_creds
   ```
   Insert your AWS credentials (access key and secret key).

2. **Encrypt and Decrypt Files:**
   - Encrypt the file:
     ```bash
     ansible-vault encrypt aws_creds
     ```
   - Decrypt the file:
     ```bash
     ansible-vault decrypt aws_creds
     ```

3. **Run Playbook Using Vault:**
   ```bash
   ansible-playbook -i invfile playbooks/vault/vaulttesting.yml -v
   ```

### Step 5: Handling Failures with Block and Rescue

Define custom error handling with `block` and `rescue` in your playbooks to ensure playbook execution doesn’t halt due to failures.

### Step 6: Secure Configuration with Vault Password File

1. **Set up Vault Password File**:
   - Create a vault password file, `/root/vaultpass`, and set permissions:
     ```bash
     chmod 600 /root/vaultpass
     ```
   - Update `ansible.cfg` to include the vault password file:
     ```ini
     [defaults]
     vault_password_file=/root/vaultpass
     ```

### Next Steps

- Explore the difference between shell, command, and raw modules in Ansible.
- Automate playbook runs with a Cron Job to periodically update facts.

### License

This project is licensed under the MIT License.

---




























PENDING TASK DURING VIDEO 

ON ANSIBLE CONTROLLER 

CD /ETC/ANSIBLE
NANO ANSIBLE.CONF --> PASTE UNDER [defaults] -- > It looks like this

gathering = smart
fact_caching_timeout = 86400
fact_caching = redis
fact_caching_prefix = ansible_DevSecOps_Saikiran
fact_caching_connection = PASTE-YOUR-CLIENT(TESTSERVER01)-PUBLICIP-HERE:6379:0

![image](https://github.com/user-attachments/assets/5a3e46dd-2534-4b97-8fff-0a380c747433)

CTLR+X --> Y > ENTER

apt update
apt install -y python3-pip
pip3 install redis

ON CONTROLLER --> ANSIBLE -I INVFILE PVT -M SETUP

ON CLIENT(TESTSERVER01) --> REDIS-CLI --> KEYS *


