![escape](https://github.com/user-attachments/assets/63a9188f-edea-4fc4-9f94-c28b46c5bb37)

# Day28 AzureDevOps_Part_1

## CI-CD-CD (Continuous Integration, Continuous Delivery, Continuous Deployment)

This project focuses on setting up a CI/CD pipeline in Azure DevOps to automate the processes of code integration, delivery, and deployment. The pipeline ensures secure, efficient, and seamless transitions from development to production.

---

### **Continuous Integration**
1. **Code Readiness:**
   - Code is committed and merged into the repository.
   - Static Application Security Testing (SAST) is performed to identify vulnerabilities.

2. **Build:**
   - Uses Maven to generate a JAR file.
   - Docker is employed to create an image using a `Dockerfile`.

3. **Artifacts Publishing:**
   - Built artifacts are stored for further stages in the CI/CD pipeline.

**Example Release Strategy:**
- A versioning system is employed:
  - Stable Version: `23.0.0` (Production-ready).
  - Release Candidates: `23.0.0.0-RC1`, `23.0.0.0-RC2`, etc., for testing.
  - Hotfix Versions: `23.0.0.1` for bug fixes post-release.

---

### **Continuous Delivery**
- Automates deployment to development and staging environments after successful integration testing.
- Focuses on delivering artifacts to lower environments for further testing.

---

### **Continuous Deployment**
- Automates deployment to production after passing all previous stages.
- Often skipped for production in many organizations due to additional manual checks.

---

### **Branching Strategy**
1. **Main/Master Branch:**
   - Represents production-ready code.

2. **Development Branch:**
   - Feature branches are created for changes and merged back into development after review.

3. **Staging/Functional Testing:**
   - Tracks and documents manual/automated test results in an organized manner.

---

### **CI/CD Tools**
Common tools for CI/CD pipelines include:
- Azure DevOps (primary focus)
- Jenkins
- GitLab
- GitHub Actions
- GoCD
- TravisCI
- CircleCI

---

## **Setting up Azure DevOps Pipeline**

### Task Overview:
1. **Create a Pipeline Agent:**
   - Use a self-hosted agent by creating a virtual machine (VM) with the necessary tools installed.
   - VM Configuration:
     - OS: Ubuntu 20.04
     - Specs: 2 CPUs, 8GB RAM
     - Disk: Standard SSD

2. **Configure the Agent:**
   - Install required tools (e.g., Terraform, Packer).
   - Generate a Personal Access Token (PAT) for authentication.
   - Create an agent pool and register the agent in Azure DevOps.

3. **Pipeline Creation:**
   - Create a pipeline for the repository in Azure DevOps.
   - Use a `trigger` to specify branches for automatic execution.

4. **Clone Repository Locally:**
   - Use Git commands to clone the repository and manage changes.

---

### Step-by-Step Instructions:

1. **Create VM:**
   - Set up a virtual machine in Azure with the specified configuration.
   - Configure networking to allow necessary inbound and outbound rules.

2. **Install Required Tools:**
   - Access the VM via SSH (e.g., PuTTY).
   - Install dependencies and configure tools as the admin user.

3. **Generate PAT:**
   - Create a Personal Access Token in Azure DevOps with full access and save it securely.

4. **Setup Agent Pool:**
   - Create and configure an agent pool in Azure DevOps.
   - Register the VM as an agent using provided setup scripts.

5. **Pipeline Creation:**
   - Use Azure Pipelines to create a YAML-based pipeline.
   - Example configuration:
     ```yaml
     trigger:
       branches:
         include:
           - master
     pool:
       name: LinuxAgentPool
     steps:
       - script: echo "Hello, Azure DevOps!"
     ```

6. **Test and Modify Pipeline:**
   - Push changes to trigger pipeline execution.
   - Use Visual Studio Code for editing pipeline configurations.

7. **Add Variables:**
   - Add SonarQube credentials or other required variables in the Azure DevOps pipeline UI.

8. **Service Connections:**
   - Connect the Azure DevOps pipeline to external tools like SonarQube for analysis.

---

## **Advanced Features**
- Conditional expressions for environment-specific pipelines.
- Integration with AWS instances or other external environments.
- Dynamic agent capabilities for task-specific pipelines.

---

### **Additional Resources**
- [Azure DevOps Documentation](https://learn.microsoft.com/en-us/azure/devops/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [GitHub for Version Control](https://github.com/)

---

**Contributors:**
- Admin Kiran (Contact: `adminkiran`)

**License:**
- This project is licensed under the MIT License. See the LICENSE file for details.
