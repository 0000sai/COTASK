# Day 20 AWS-Packer

![a-vibrant-and-eye-catching-youtube-thumbnail-with--CWD0OBoeRVO1Jw5QXUd3iw-PZaqUMYdQ0eS9Tv6GFm_VQ](https://github.com/user-attachments/assets/5cc2de07-938e-4197-8e07-c99bdcdd0180)


Here's an outline to help you implement and visualize this process:

### 1. **Introduction to Packer and Ansible**

- **Packer**: A tool to create images for multiple platforms from a single source configuration.
- **Ansible**: A configuration management tool used for automation, specifically post-deployment configuration.

### 2. **Why Ansible?**

After deploying infrastructure with tools like **Terraform**, configuration management is needed for more specific setups on the deployed resources. Here’s where **Ansible** comes in:

- **Controller-Client Model**:
  - **Controller**: The machine where Ansible commands are run.
  - **Clients** (Nodes): Machines receiving configuration commands from the controller.

- **No Client Software Needed**: Ansible only requires SSH and Python on the nodes, simplifying the setup.

### 3. **Diagram of Ansible Setup**
For a visual, imagine:
   - A **controller node** communicating with **client nodes** using SSH.
   - Commands are sent from the controller, received by nodes, and executed without needing any additional software on the client side.

### 4. **Task: AMI Creation and Deployment**
   1. **Create an AMI Image** using Packer for a base instance.
   2. **Deploy an Instance** with this AMI.
   3. Verify functionality, ensuring services like Node Exporter (on port 9100) are working.

### 5. **Steps to Install and Configure Ansible on Deployed Instances**
   - **Install Ansible**:
     - Refer to [Ansible documentation](https://docs.ansible.com/) for the latest installation steps.
   - **Configuration File**:
     - Run `sudo ansible-config init --disabled > ansible.cfg` in `/etc` to generate the config file.
   - **Update Ansible Configurations**:
     - Open the file with `ctrl+w` to search and configure:
       - Set `host_key_checking = false`.
       - Define the `remote_user` as `ansibleadmin`.
       - Define `private_key_file` as `/home/ansibleadmin/key.pem` (ensure key permissions are set to read-only, i.e., `chmod 444 key.pem`).

Following these steps will provide a setup ready for deploying configurations across instances effectively using Ansible.
