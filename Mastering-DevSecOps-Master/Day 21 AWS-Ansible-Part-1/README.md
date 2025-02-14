# Day 21 AWS-Ansible-Part-1

![image](https://github.com/user-attachments/assets/5cec40df-0b9a-4757-8399-d2fbe42fb064)

# Project Setup with Packer, Ansible, and Terraform

## Overview

In this project, we utilize several DevOps tools to set up, configure, and manage infrastructure and application deployment:
- **Packer**: Used for building machine images.
- **Ansible**: Configuration management tool, enabling automated configuration of our infrastructure post-deployment.
- **Terraform**: Infrastructure as Code (IaC) tool for provisioning resources.

We’ll walk through how to integrate **Ansible** with **Terraform** to manage configurations on an infrastructure that's already deployed, setting up an Ansible Controller and ensuring communication between it and the client servers.

## Architecture and Components

1. **Ansible Controller**: Runs all configuration commands on the clients/nodes.
2. **Ansible Clients**: Servers that Ansible manages remotely.

**Note**: Ansible doesn’t require client software installation, as it connects to clients via SSH and Python.

### Diagram
- [Add a diagram here depicting the VPC peering, Ansible Controller, and Ansible Clients.]

## Task Workflow

### Step 1: Provisioning with Terraform

1. **Modify the Terraform Configuration**:
   - Update `ec2.tf` with the correct AWS account number.
   - Set up **VPC Peering** to allow communication between the Ansible Controller VPC and the client VPC. Update the **Route Tables** accordingly.

2. **Deploy Resources**:
   - Use `terraform init`, `terraform fmt`, `terraform validate`, and finally `terraform apply -var-file=15.terraform.tfvars` to deploy the infrastructure.
   - Verify that the public and private IPs are assigned correctly.

### Step 2: Configure Ansible Inventory

1. **Inventory File (invfile)**:
   - This is a critical file listing all servers or hosts Ansible will manage.
   - It identifies the target machines, making it easy for Ansible to know where to apply configuration changes.

### Step 3: Set Up Ansible Controller

1. **Prepare SSH Access**:
   - Place your SSH key at `/etc/ansible/ansiblekey.pem` on the Ansible controller and set permissions using `chmod 600`.
   
2. **Install Terraform on the Controller**:
   - Clone the Git repository in the root location of the controller.
   - Navigate to `ansiblecore`, and initialize Terraform with `terraform init`.

3. **Validate Connectivity**:
   - Use Ansible to test connectivity with the client servers:
     ```bash
     ansible -i invfile pvt -m ping
     ```

### Step 4: Working with Ad-Hoc Commands in Ansible

1. **Run Ad-Hoc Commands**:
   - To check disk space across servers:
     ```bash
     ansible -i invfile pvt -m shell -a "df -h"
     ```
   - To filter for root volume only:
     ```bash
     ansible -i invfile pvt -m shell -a "df -h | grep '/dev/root'"
     ```
   - Increase verbosity by appending `-v`, `-vv`, or `-vvv` for debugging:
     ```bash
     ansible -i invfile pvt -m shell -a "df -h | grep '/dev/root'" -vv
     ```

2. **Target Specific Servers**:
   - For example, to exclude a specific server:
     ```bash
     ansible -i invfile 'all:!server01' -m shell -a "df -h | grep '/dev/root'" -v
     ```

### Step 5: Using Ansible Playbooks for Complex Tasks

1. **Create Playbooks Folder**:
   - Organize playbooks in the `playbooks` folder.

2. **Sample Nginx Playbook**:
   - The sample playbook installs nginx on the client servers.
   - Run syntax checks with:
     ```bash
     ansible-playbook -i invfile playbooks/1.nginx/o.sample-playbook.yml --syntax-check
     ```

3. **Run Playbooks**:
   - Deploy nginx using:
     ```bash
     ansible-playbook -i invfile playbooks/1.nginx/1.nginx-local.yml -vvv
     ```

4. **Remote Module Usage**:
   - For copying files from a remote location, use the remote module. To remove unnecessary files:
     ```bash
     ansible -i invfile pvt -m shell -a "rm -rf /var/www/html/index.nginx-debian.html" --become
     ```

### Step 6: User Management

- Run the user creation playbook:
  ```bash
  ansible-playbook -i invfile playbooks/1.nginx/5.user_creation.yml -vv
  ```

### Step 7: Redis Caching (Optional)

- Use Redis to cache Ansible facts for environments with a large number of servers:
  ```bash
  ansible -i invfile all -m setup
  ```

### Final Steps

1. **Push Code Changes**:
   - Regularly push updates from your local machine to Git.

2. **Destroying Resources**:
   - Use Terraform to destroy resources if needed:
     ```bash
     terraform destroy -var-file=15.terraform.tfvars
     ```
