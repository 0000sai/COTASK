# Ansible Dynamic Inventory and Ansible Tower

"Anible Dynamic Inventory" title with Attractive Font for youtube Thumbnail 

This guide explains how to use **Ansible Dynamic Inventory**  for managing dynamic environments, such as those involving auto-scaling groups. Unlike static inventory, dynamic inventory adapts to infrastructure changes, such as scaling up or down during load variations.

---

## Overview

### Static vs Dynamic Use Case

- **Static Use Case**: Targets predefined servers without HA (High Availability) or auto-scaling. Servers remain fixed, without scaling up or down.
- **Dynamic Use Case**: Ideal for environments with auto-scaling groups. Servers scale automatically based on load, requiring a dynamic inventory for effective management.

---

## Prerequisites

1. **Install Required Tools**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip jq -y
   sudo pip3 install boto3
   sudo apt install -y awscli
   aws --version
   ```

2. **Configure Ansible**:
   - Navigate to the Ansible configuration directory:
     ```bash
     cd /etc/ansible
     ```
   - Back up the `ansible.cfg` file:
     ```bash
     cp ansible.cfg ansible.cfg.bak
     ```
   - Edit the `ansible.cfg` file and enable the **inventory plugins**:
     ```bash
     nano ansible.cfg
     ```
     Locate `[inventory]` and update as needed.

3. **Create EC2 Plugin File**:
   - Create a new file for the EC2 plugin:
     ```bash
     nano aws_ec2.yaml
     ```
   - Paste the following configuration:
     ```yaml
     plugin: aws_ec2
     regions:
       - us-east-1
     keyed_groups:
       - key: tags
         prefix: tag
       - prefix: instance_type
         key: instance_type
       - key: placement.region
         prefix: aws_region
     ```

---

## Steps to Use Dynamic Inventory

### Deploy Infrastructure First
1. Validate the dynamic inventory:
   ```bash
   ansible-inventory -i /etc/ansible/aws_ec2.yaml --list
   ansible-inventory -i /etc/ansible/aws_ec2.yaml --list | jq
   ```
2. Test connectivity using tags:
   ```bash
   ansible -i /etc/ansible/aws_ec2.yaml tag_terraform_managed_yes -m ping
   ```

### Target Specific Resources
- Set the dynamic inventory path:
  ```bash
  export dynamic='/etc/ansible/aws_ec2.yaml'
  ```
- Example command to run on specific instance types:
  ```bash
  ansible -i $dynamic instance_type_t2_small -m shell -a "df -h"
  ```

### Run Playbooks
1. Create a playbook targeting specific tags:
   - Edit or create the playbook under the `dynamic_inventory` folder:
     ```bash
     nano dynamic_nginx-jinja2.yaml
     ```
   - Update the `hosts` to:
     ```yaml
     hosts: tag_managedby_terraform
     ```
2. Run the playbook:
   ```bash
   ansible-playbook -i $dynamic playbook/dynamic_inventory/dynamic_nginx.yaml
   ```

3. Replace `nginx` with `mysql` or other playbooks as needed.

---

## Git Workflow for Dynamic Inventory
1. Create and switch to a new branch:
   ```bash
   git checkout -b dynamic_inventory
   ```
2. Push changes to remote:
   ```bash
   git push origin dynamic_inventory
   ```
3. Pull updates to the local repo:
   ```bash
   git pull
   ```

---

## Auto-Scaling Integration
When an auto-scaling group provisions instances, the dynamic inventory automatically updates to target the new resources. Verify using:
```bash
ansible-inventory -i aws_ec2.yaml --list
ansible-inventory -i aws_ec2.yaml --graph
```

---

## Example Playbook Execution
1. Modify the number of instances in your Terraform configuration:
   ```bash
   terraform apply -var-file="vars.tfvars" -auto-approve
   ```
2. Run the playbook:
   ```bash
   ansible-playbook -i /etc/ansible/aws_ec2.yaml playbook/dynamic_inventory/dynamic_nginx.yaml
   ```
3. Validate with the updated inventory.

---

## Notes
- Ensure that the `ansible.cfg` file is correctly configured for plugins.
- Use `jq` to format and verify inventory JSON outputs.
- Replace line endings with `LF` if issues arise during playbook execution.

End of Dynamic Inventory.
