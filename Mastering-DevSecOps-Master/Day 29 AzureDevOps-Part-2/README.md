# PLEASE COPY THE POM.XML AND PIPELINE SCRIPT FIRST AND DO THE PRACTICALS. REST ALL SAME. 


# Prod-SpringBoot-Pet-App

This repository contains the production-ready Spring Boot application for the `Prod-ADO` instance. Follow the steps below to set up and run the CI/CD pipeline using Azure DevOps (ADO).

## Prerequisites
- AWS and Azure instances must be up and running.
- Proper IP addresses should be updated in Route 53.

## Steps to Set Up the Pipeline

### Stage 1: Initial Setup
1. **Start the agents** on AWS and Azure.
2. **Update the IPs** in Route 53.
3. **Clone the repository** and check the available branches.
4. **Add the SonarQube stage** and build the pipeline accordingly.
5. **Modify the `pom.xml` file** at lines 13 & 16:
   ```xml
   <artifactId>ado-spring-boot-app-dev</artifactId>
   ```

### Stage 2: Connecting the Pipeline to the EC2 Instance
1. **Connect the pipeline to the EC2 instance** where SonarQube and Maven are installed using service connections:
   - Navigate to **Project Settings > Service Connections**.
   - Create a new service connection for the EC2 instance.
2. **Add the token** in the pipeline and push the code to the development branch.
3. **Run the pipeline** and push it to the development environment.
4. If the Maven build fails, skip tests by adding the following line:
   ```yaml
   options: '-DskipTests'
   ```
   Add it above the `displayName` in your YAML file.
5. Push the changes again.
6. If you encounter issues with `sonar.branch.name`, set the development branch as the default branch.
7. Once the job completes, check the results on SonarQube.

### Stage 3: Building with Java and Copying Artifacts to JFrog
1. **Build the application** using Maven and copy the artifact to JFrog.
2. Ensure `settings.yaml` is securely managed:
   - Go to **Libraries > Add Secure Files**.
   - Browse and add the secure file.
3. **Create the necessary directories** on the Azure agent:
   ```bash
   sudo mkdir /artifacts
   sudo chown adminsai:adminsai /artifacts
   ```
   This folder will store the copied artifact.
4. Save and push the changes.
5. If errors occur during the Maven build, log in to the server and debug using:
   ```bash
   grep -i "failure" *.txt
   ```
   Example failure:
   ```
   org.springframework.samples.petclinic.system.CrashControllerIntegrationTests.txt
   ```
   Review and fix the `CrashControllerIntegrationTests` file accordingly.

### Stage 4: Copying Artifacts to Azure Blob Storage
1. **Create a storage account** in Azure:
   - Name: `artifacts`
   - Redundancy: Locally Redundant Storage (LRS)
2. **Create a container** named `artifacts`.
3. **Set up a service principal**:
   - Navigate to **Microsoft Entra ID > App Registration**.
   - Create a new service principal.
   - In **Project Settings > Service Connections**, create a new Azure Resource Manager connection manually.
   - Provide the following details:
     - Tenant ID
     - Client ID (Service Principal ID)
     - Subscription ID
     - Client Secret (Create a new secret under Certificates & Secrets).
4. **Create a new pipeline variable**:
   - Name: `STORAGE_ACCOUNT_KEY`
   - Secret: Yes
   - Value: Copy the access key from the storage account.
5. Push the changes and run the pipeline.

### Stage 5: Adding an S3 Bucket
1. **Create an S3 bucket** with the name specified in the YAML file.
2. **Grant S3 access**:
   - Navigate to **IAM > Users** and grant S3 full access.
3. **Create a new AWS service connection** in ADO:
   - Use the access key and secret key.
   - Connection name: `saikiransecops-s3`
4. Push the changes and verify the artifacts in the S3 bucket.

### Stage 6: Building a Docker Image and Scanning with Trivy
1. **Create a template folder** in VSCode:
   ```bash
   mkdir template
   cd template
   touch junit.tpl
   ```
   Paste the required content into `junit.tpl`.
2. **Create a Dockerfile** in VSCode and paste the necessary code.
3. Push the changes.
4. Test the pipeline step-by-step to ensure correctness.

## Final Notes
- The pipeline may require multiple iterations to achieve perfection. Ensure that each step is tested and validated before proceeding to the next.
- Use secure methods to manage sensitive information such as credentials and keys.

## Troubleshooting
- For Maven build failures, use the following command:
  ```bash
  grep -i "failure" *.txt
  ```
- If issues are found in `CrashControllerIntegrationTests`, review the file and make the necessary changes without altering unrelated parts.
- **SonarQube Upgrade Steps**:
  1. **Stop SonarQube**:
     ```bash
     sudo systemctl stop sonar
     ```
  2. **Download and install a newer version (10.3)**:
     ```bash
     cd /opt
     sudo wget https://binaries.sonarsource.com/Distribution/sonarqube/sonarqube-10.3.0.82913.zip
     sudo unzip sonarqube-10.3.0.82913.zip
     sudo rm -rf sonarqube
     sudo mv sonarqube-10.3.0.82913 sonarqube
     ```
  3. **Fix permissions**:
     ```bash
     sudo chown -R sonar:sonar /opt/sonarqube
     sudo chmod -R 755 /opt/sonarqube
     ```
  4. **Update `sonar.properties` to configure JDK 17 module path**:
     ```bash
     sudo nano /opt/sonarqube/conf/sonar.properties
     ```
     Add the following line:
     ```properties
     sonar.web.javaAdditionalOpts=--add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-exports=java.base/jdk.internal.ref=ALL-UNNAMED
     ```
  5. **Restart SonarQube**:
     ```bash
     sudo systemctl restart sonar
     ```
  This newer version has better compatibility with Java 17. Let the DevOps team know if further errors occur.

## Acknowledgments
Special thanks to the team for their support in setting up and validating the pipeline.

---
For further assistance, please contact the DevOps team.



---


