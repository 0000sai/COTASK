<img width="1536" alt="Jenkins Pipeline" src="https://github.com/user-attachments/assets/78c38280-4096-4b14-9891-f924ef87e729" />


# Jenkins Pipeline Setup with Multi-Branch Deployment for Infra Hanlding 

This repository details the process of setting up a Jenkins multi-branch pipeline for automated deployments using GitHub webhooks and IAM roles on AWS instances.

## **Steps to Follow**

1. **Instance Setup & DNS Configuration**  
   - Turn on the AWS instances and configure DNS records accordingly.

2. **Code Explanation**  
   - Review and understand the provided codebase for deployment automation.

3. **IAM Role Assignment**  
   - Assign appropriate IAM roles to all three instances to manage permissions.

4. **DNS Update**  
   - Update the DNS names post instance restart, as previous configurations might have changed.

5. **GitHub Repository Setup**  
   - Create a **private GitHub repository**.
   - Push the code to a **development branch** for better version control.

6. **Webhook Configuration**  
   - Go to **Repo Settings > Webhooks**.
   - Copy the webhook URL from the previous Spring Boot repository and apply it here.

7. **Deploy Key Setup**  
   - Remove the deploy key from the Spring Boot app.
   - Create a new deploy key under the **infra-pipeline** section.
   - Run `su - jenkins && cat ~/.ssh/id_rsa.pub` and paste the key under GitHub deploy keys.

8. **Jenkins Pipeline Configuration**  
   - Create a new pipeline in Jenkins:
     - Select **New Item** and choose **Multibranch Pipeline**.
     - Under **Branch Sources > Git**, paste the repository SSH URL (`git@...`).
     - Use **Jenkins GitHub access credentials** for authentication.
     - Enable **Webhook-triggered builds** by entering the token from the webhook settings.
     - Save the configuration.
