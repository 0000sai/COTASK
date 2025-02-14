# Day 37 Jenkins-Part-2

![diagram-export-1-29-2025-8_53_17-PM](https://github.com/user-attachments/assets/123cd71f-a1ff-4263-a77f-13d00818363e)

# Jenkins RBAC and Backup & Restore

## Jenkins Role-Based Access Control (RBAC)

### Overview
Jenkins Role-Based Access Control (RBAC) allows administrators to define specific permissions for users and groups. This ensures proper access management and enhances security within Jenkins.

### Steps to Configure RBAC
1. **Login to Your Jenkins Server**
   - Open Jenkins on port `8443`.
2. **Navigate to Manage Jenkins**
   - You will not see any roles initially since a plugin needs to be installed.
3. **Install the Required Plugin**
   - Go to **Manage Jenkins > Plugins**.
   - Install the **Role-Based Authorization Strategy** plugin.
   - Wait for the installation to complete.
4. **Configure Security Settings**
   - Navigate to **Manage Jenkins > Security**.
   - Set **Security Realm** to: *Jenkins’ own user database*.
   - Set **Authorization** to: *Role-Based Strategy*.
   - Click **Save**.
5. **Assign Roles**
   - Go to **Manage Jenkins > Manage and Assign Roles**.
   - Click on **Assign Roles** and configure project-level roles as needed.
   - Save the changes.
6. **Create User Accounts**
   - Navigate to **Manage Jenkins > Users**.
   - Create a user named `saikiran` with a password and fill in the required details.
   - Similarly, create three additional users.
7. **Assign Users to Roles**
   - Go to **Manage Jenkins > Manage and Assign Roles > Assign Roles**.
   - Add users and assign them appropriate roles.
   - Scroll down to **Item Roles** and configure access levels.
   - Click **Save**.
8. **Create a Project**
   - Create a new project named `java-project`.
   - Scroll down, select **Execute Shell**, enter the necessary script.
   - Click **Save**.
9. **Create Additional Projects**
   - Create three more projects (e.g., Python, Java, etc.).
   - The code remains the same.
10. **Configure the Built-in Node**
    - Navigate to **Manage Jenkins > Nodes > Built-in Node**.
    - Remove existing labels and save.
11. **Test Role-Based Access Control**
    - Open Jenkins in a **private browser window**.
    - Log in with different users and observe the access differences.

---

## Jenkins Backup and Restore

### Overview
Regular backups ensure that Jenkins configurations and jobs can be restored in case of failure. Jenkins provides multiple backup options, including local and cloud storage.

### Steps to Backup Jenkins Data
1. **Navigate to Jenkins Home Directory**
   ```sh
   cd /var/lib/jenkins
   du -h /var/lib/jenkins
   ```
   - You can directly back up these files if required.
2. **Use ThinBackup Plugin for Backup**
   - Navigate to **Manage Jenkins > ThinBackup**.
   - Click on **Backup Now**.
3. **Create a Backup Directory on the Server**
   - Open **Putty** and run:
     ```sh
     mkdir /Jenkins-backup
     chown jenkins:jenkins /Jenkins-backup
     ```
4. **Configure Automatic Backup Schedule**
   - Go to **Manage Jenkins > ThinBackup**.
   - Set the backup schedule to run at 9 PM from Monday to Friday:
     ```
     0 21 * * 1-5
     ```
   - Set the maximum retention period to **30 days**.
   - Restart Jenkins:
     ```sh
     sudo systemctl restart jenkins
     ```
   - Enable backups and click **Save**.
   - Click **Backup Now** and verify the backup in **Putty**.
5. **Store Backups in the Cloud**
   - Since Jenkins could be completely deleted, it is advisable to store backups in **Amazon S3** or **Azure Blob Storage** for added security and redundancy.

---

By following these steps, you can effectively manage user roles in Jenkins and implement a reliable backup strategy to protect your Jenkins environment.

