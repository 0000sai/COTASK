# Day 23 AWS-Ansible-Part-3

![a-3d-render-of-a-glowing-ansible-logo-below-the-lo-4QgGoilXQ36n-8iyPqrNXQ-mBzRZGehQfeGRujEXVxpTQ](https://github.com/user-attachments/assets/240ba7fd-de4a-4f64-9e16-f36c61ca5720)

# Complete Code here : https://github.com/saikiranpi/Ansible-Testing

---

# Ansible Jinja2 Templating with MySQL and Nginx Playbooks

This project demonstrates the use of Jinja2 templates in Ansible to deploy and configure services on multiple servers. It includes examples of pre- and post-tasks, as well as how to manage MySQL and Nginx configurations using Ansible playbooks.

## Project Setup

1. **Initialize Ansible Configuration**
   - Navigate to the Ansible directory:
     ```bash
     cd /etc/ansible/
     ```
   - Generate the default Ansible configuration:
     ```bash
     ansible-config init --disabled > ansible.cfg
     ```
   - Modify `ansible.cfg` for common settings:
     ```bash
     nano ansible.cfg
     ```
   - Update the following values:
     ```ini
     host_key_checking = False
     remote_user = ansibleadmin
     private_key_file = /home/ansibleadmin/key.pem
     ```

2. **Initialize and Apply Terraform**
   - Ensure you are in the correct directory and apply the Terraform configuration to set up your infrastructure:
     ```bash
     terraform init
     terraform apply
     ```

## Jinja2 Templating with Nginx

The `nginx-jinja2.yml` playbook uses Jinja2 templates to configure Nginx.

1. Run the Nginx playbook:
   ```bash
   ansible-playbook -i invfile nginx-jinja2.yml -v
   ```
2. Once the playbook is complete, check the public IP of the server to verify that Nginx is running.

## MySQL Setup with Jinja2

This section explains how to install and configure MySQL using Ansible and Jinja2 templates. All variable values are defined within the configuration file.

1. Run the MySQL playbook:
   ```bash
   ansible-playbook -i invfile playbooks/mysql-jinja2.yml
   ```
2. Verify MySQL service status:
   ```bash
   ansible -i invfile pvt -m shell -a "service mysql status"
   ```
3. Once the MySQL service is running, log in to the server and confirm that you can access MySQL databases:
   ```sql
   mysql> SHOW DATABASES;
   ```
4. Add data to the `myflixdb` database:
   ```sql
   USE myflixdb;
   SHOW TABLES;
   SELECT * FROM movies;
   ```

## Pre-Tasks and Post-Tasks

Pre-tasks and post-tasks are used to prepare the system before the main tasks or clean up afterward.

### Example Task: Checking `/tmp` Folder

1. Run the playbook with pre-tasks and post-tasks:
   ```bash
   ansible-playbook -i invfile playbooks/pre_post_tasks.yml
   ```

## Running the Playbooks on Multiple Servers

If you need to run these playbooks across 100 or more servers, Ansible's inventory and parallel execution capabilities make this straightforward. Update your inventory file (`invfile`) with the list of servers, and then run the playbooks with the inventory specified.

## Git Commands for Version Control

1. To push any changes to your playbook repository:
   ```bash
   git push
   ```
2. To pull the latest updates:
   ```bash
   git pull
   ```

## File Structure

```
/etc/ansible/
├── ansible.cfg               # Ansible configuration file
├── invfile                   # Inventory file listing server IPs or hostnames
├── playbooks/
│   ├── nginx-jinja2.yml      # Nginx playbook using Jinja2 template
│   ├── mysql-jinja2.yml      # MySQL playbook using Jinja2 template
│   └── pre_post_tasks.yml    # Playbook with pre-tasks and post-tasks
└── templates/
    ├── nginx.j2              # Nginx configuration template
    └── mysql.j2              # MySQL configuration template
```

## Requirements

- Ansible 2.9+
- Terraform (if using for infrastructure setup)
- SSH access to the target servers

## Usage Notes

This project is suitable for dynamic and scalable server setups. With Jinja2 templating, you can easily customize configurations for different environments or requirements, making it highly adaptable for both development and production needs.

---
