# Day 36 Jenkins-Part-1
<img width="1536" alt="jenkins" src="https://github.com/user-attachments/assets/4519f27d-537b-4593-bde9-0e5756b2965c" />

# Jenkins Setup and Configuration Guide

This guide provides a step-by-step process to set up and configure Jenkins with slave nodes, GitHub integration, SonarQube, and Slack notifications. By following this guide, you will establish a fully functional Jenkins environment capable of managing development and production pipelines.

---

## 1. Deploy Jenkins Master Instance

1. Launch an EC2 instance with the following specifications:
   - **Instance Type:** t2.medium
   - **OS:** Ubuntu
2. Install Jenkins on the instance and start the service.
3. Install VSCode and run the necessary commands to configure Jenkins.

---

## 2. Configure Jenkins Slaves

### Step 1: Add Global Credentials
- Navigate to **Manage Jenkins > Credentials > System > Global Credentials**.
- Add new credentials:
  - **ID:** slave-access
  - **Description:** slave-access
  - **Username:** ubuntu
  - **Password:** Use your `.pem` file.

### Step 2: Deploy Slave Instances
- Launch two t2.medium EC2 instances from the same AMI used for the master instance.
- Name the instances:
  - `Jenkins-Slave-Dev`
  - `Jenkins-Slave-Prod`

### Step 3: Add Nodes to Jenkins
1. Navigate to **Manage Jenkins > Nodes > Add Node**.
2. Configure **Dev-Slave**:
   - **Permanent Agent:** Yes
   - **No. of Executors:** 2
   - **Remote Root Directory:** `/home/ubuntu`
   - **Labels:** DEV
   - **Usage:** Only build jobs with label.
   - **Launch Method:** Launch Agents via SSH
   - **Host:** Dev slave private IP or DNS
   - **Credentials:** ubuntu (slave-access)
   - **Host Key Verification Strategy:** Non-verifying strategy
   - **Port:** 22
3. Repeat the same steps for **Prod-Slave**, copying settings from **Dev-Slave** but updating the names and IP/DNS accordingly.

---

## 3. Configure GitHub Access

1. Switch to the Jenkins user:
   ```bash
   su - jenkins
   ssh-keygen
   ```
2. Add the private key to Jenkins:
   - Navigate to **Manage Jenkins > Credentials > System > Global Credentials**.
   - Add SSH Username with Private Key:
     - **ID:** GitHubAccess
     - **Username:** jenkins
     - **Private Key:** Paste the generated private key.
3. Add the public key to your GitHub repository under **Deploy Keys**.

---

## 4. Configure SonarQube

1. Generate a token from SonarQube:
   - Navigate to **SonarQube > My Account > Security**.
   - Generate a token and copy it.
2. Add the token to Jenkins:
   - Navigate to **Manage Jenkins > Credentials > System > Global Credentials**.
   - Add Secret Text:
     - **ID:** sonarqube-token
     - **Scope:** Global
     - **Secret:** Paste the token.
3. Configure SonarQube in Jenkins:
   - Navigate to **Manage Jenkins > System > Configure System**.
   - Add SonarQube Server:
     - **Name:** As per your script
     - **URL:** Your SonarQube URL (remove trailing slash)
     - **Credentials:** Select the token you just created.
4. Create a webhook in SonarQube:
   - Navigate to **Administrator > Webhooks > Create**.
   - **Name:** Jenkins-Webhook
   - **URL:** `http://<Jenkins-Master-PublicIP>:8080/sonarqube-webhook/`

---

## 5. Configure GitHub Webhooks

1. Push your development code to a private GitHub repository.
2. Navigate to **Repository Settings > Webhooks > Add Webhook**.
   - **Content Type:** `application/json`
   - **URL:** As per your Jenkins pipeline token.
   - Add the webhook and authenticate it.

---

## 6. Create a Multibranch Pipeline

1. Create a new item in Jenkins:
   - **Name:** Your pipeline name
   - **Type:** Multibranch Pipeline
2. Configure the pipeline:
   - **Branch Source:**
     - **Type:** Git
     - **Credentials:** Jenkins (GitHubAccess)
     - **Repository URL:** Your GitHub repository URL
   - **Build Configuration:**
     - **Script Path:** `Jenkinsfile`
     - **Scan by Webhook:** Use the same token as the GitHub webhook.
3. Add the public SSH key generated earlier to **GitHub Deploy Keys**.

---

## 7. Configure Slack Notifications

1. Create a Slack channel and add the Jenkins app:
   - **Channel:** Your desired Slack channel.
   - **Token:** Copy the integration token.
2. Add the Slack token to Jenkins:
   - Navigate to **Manage Jenkins > Credentials > System > Global Credentials**.
   - Add Secret Text:
     - **ID:** slack-token
     - **Secret:** Paste the token.
3. Configure Slack in Jenkins:
   - Navigate to **Manage Jenkins > System**.
   - Add Slack configuration:
     - **Workspace:** Your Slack workspace name
     - **Credentials:** Select slack-token
     - **Channel:** Your Slack channel name

---

## 8. Additional Steps

- Update the `settings.xml` file with the correct JFrog URL.
- Assign an IAM role with admin access to Jenkins for pushing reports.
- Configure labels for nodes:
  - **Manage Jenkins > Nodes and Clouds > Built-in Node**:
    - **Labels:** MASTER

---

## 9. Test the Setup

1. Create a new branch (`development`) in GitHub.
2. Push a commit to the branch.
3. Check if the pipeline triggers and runs successfully in Blue Ocean.
4. Create a `prod` branch and run the job on the **Prod-Slave** node.

---

## 10. Stopping Instances

- Stop all instances when not in use but do not terminate them to preserve configurations.

---


